"""
Minecraft Java Anvil (.mca) World Exporter for Milestone T1.

Target Version: Minecraft Java Edition 1.20 / 1.21 (DataVersion: 3465).
Exports:
1. Cropped Settlement Region: 400x400 block region around Settlement A.
2. Full Continental World: 2400x2400 block continent with region files and level.dat.

Self-contained pure-Python implementation using standard library struct and zlib.
Generates fully compliant Minecraft Anvil region files and NBT headers.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import struct
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import zlib

from minemesis.systems.world_spec import WorldSpec
from translators.voxel.chunk_generator import ChunkData, generate_chunk
from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_NAMES,
    VoxelWorldSpec,
)


MINECRAFT_DATA_VERSION = 3465  # Java 1.20.2 - 1.20.4
SECTOR_SIZE = 4096


# -----------------------------------------------------------------------------
# Pure-Python Lightweight NBT Serializer
# -----------------------------------------------------------------------------
class NBT:
    END = 0
    BYTE = 1
    SHORT = 2
    INT = 3
    LONG = 4
    FLOAT = 5
    DOUBLE = 6
    BYTE_ARRAY = 7
    STRING = 8
    LIST = 9
    COMPOUND = 10
    INT_ARRAY = 11
    LONG_ARRAY = 12


def write_nbt_tag(tag_type: int, name: Optional[str], value: Any) -> bytearray:
    buf = bytearray()
    if name is not None:
        buf.append(tag_type)
        name_bytes = name.encode("utf-8")
        buf.extend(struct.pack(">H", len(name_bytes)))
        buf.extend(name_bytes)

    if tag_type == NBT.BYTE:
        buf.append(int(value) & 0xFF)
    elif tag_type == NBT.SHORT:
        buf.extend(struct.pack(">h", int(value)))
    elif tag_type == NBT.INT:
        buf.extend(struct.pack(">i", int(value)))
    elif tag_type == NBT.LONG:
        buf.extend(struct.pack(">q", int(value)))
    elif tag_type == NBT.FLOAT:
        buf.extend(struct.pack(">f", float(value)))
    elif tag_type == NBT.DOUBLE:
        buf.extend(struct.pack(">d", float(value)))
    elif tag_type == NBT.BYTE_ARRAY:
        buf.extend(struct.pack(">i", len(value)))
        buf.extend(value)
    elif tag_type == NBT.STRING:
        s_bytes = str(value).encode("utf-8")
        buf.extend(struct.pack(">H", len(s_bytes)))
        buf.extend(s_bytes)
    elif tag_type == NBT.LIST:
        item_type, items = value
        buf.append(item_type)
        buf.extend(struct.pack(">i", len(items)))
        for it in items:
            buf.extend(write_nbt_tag(item_type, None, it))
    elif tag_type == NBT.COMPOUND:
        for k, (sub_t, sub_v) in value.items():
            buf.extend(write_nbt_tag(sub_t, k, sub_v))
        buf.append(NBT.END)
    elif tag_type == NBT.LONG_ARRAY:
        buf.extend(struct.pack(">i", len(value)))
        for l_val in value:
            buf.extend(struct.pack(">q", int(l_val)))

    return buf


def serialize_chunk_to_nbt(cx: int, cz: int, chunk: ChunkData) -> bytes:
    """
    Serializes ChunkData to Minecraft Java 1.20/1.21 NBT chunk structure.
    Optimized with fast C-level memory slices and uniform section compression.
    """
    sections_list = []

    # 16 vertical sections (16x16x16 blocks each) for Y = 0..255
    for sec_idx in range(16):
        sec_y = sec_idx
        start_idx = sec_idx * 4096
        end_idx = start_idx + 4096
        sec_bytes = chunk.voxels[start_idx:end_idx]

        min_b = min(sec_bytes)
        max_b = max(sec_bytes)

        if min_b == max_b:
            # Entire 16x16x16 section is uniform (single block type, e.g. AIR or STONE)
            res_name = BLOCK_NAMES.get(min_b, "minecraft:air")
            sec_compound = {
                "Y": (NBT.BYTE, sec_y),
                "block_states": (NBT.COMPOUND, {
                    "palette": (NBT.LIST, (NBT.COMPOUND, [{"Name": (NBT.STRING, res_name)}]))
                })
            }
            sections_list.append(sec_compound)
            continue

        # Section contains mixed blocks
        palette_ids = sorted(set(sec_bytes))
        palette_compounds = [
            {"Name": (NBT.STRING, BLOCK_NAMES.get(pid, "minecraft:stone"))}
            for pid in palette_ids
        ]

        sec_compound = {
            "Y": (NBT.BYTE, sec_y),
            "block_states": (NBT.COMPOUND, {
                "palette": (NBT.LIST, (NBT.COMPOUND, palette_compounds))
            })
        }

        # Pack indices into 64-bit Long Array
        bits_per_entry = max(4, math.ceil(math.log2(len(palette_ids))))
        entries_per_long = 64 // bits_per_entry
        long_count = math.ceil(4096 / entries_per_long)

        id_to_idx = {pid: i for i, pid in enumerate(palette_ids)}
        packed_longs = [0] * long_count

        for i in range(4096):
            b_val = sec_bytes[i]
            p_idx = id_to_idx[b_val]
            long_idx = i // entries_per_long
            sub_offset = (i % entries_per_long) * bits_per_entry
            packed_longs[long_idx] |= (p_idx << sub_offset)

        signed_longs = [
            struct.unpack(">q", struct.pack(">Q", pl & 0xFFFFFFFFFFFFFFFF))[0]
            for pl in packed_longs
        ]
        sec_compound["block_states"][1]["data"] = (NBT.LONG_ARRAY, signed_longs)
        sections_list.append(sec_compound)

    root_compound = {
        "DataVersion": (NBT.INT, MINECRAFT_DATA_VERSION),
        "xPos": (NBT.INT, cx),
        "yPos": (NBT.INT, 0),
        "zPos": (NBT.INT, cz),
        "Status": (NBT.STRING, "minecraft:full"),
        "sections": (NBT.LIST, (NBT.COMPOUND, sections_list)),
    }

    nbt_data = write_nbt_tag(NBT.COMPOUND, "", root_compound)
    return zlib.compress(bytes(nbt_data), level=6)


# -----------------------------------------------------------------------------
# Anvil Region File Writer (.mca)
# -----------------------------------------------------------------------------
class AnvilRegionWriter:
    """
    Constructs a standard Minecraft Java Anvil (.mca) region file containing up to 1024 chunks.
    """

    def __init__(self, region_file: Path) -> None:
        self.file_path = Path(region_file)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # 1024 chunks: (offset, sector_count)
        self.locations: List[Tuple[int, int]] = [(0, 0)] * 1024
        self.timestamps: List[int] = [int(time.time())] * 1024
        self.chunk_payloads: Dict[int, bytes] = {}

    def add_chunk(self, rx: int, rz: int, compressed_chunk_data: bytes) -> None:
        """Adds a chunk at region-local coordinates (rx: 0..31, rz: 0..31)."""
        idx = (rz % 32) * 32 + (rx % 32)
        self.chunk_payloads[idx] = compressed_chunk_data

    def write(self) -> None:
        """Packs headers and chunk sectors into the .mca binary format."""
        sector_offset = 2  # Sectors 0 and 1 are reserved for header tables

        payload_bytes = bytearray()
        for idx in range(1024):
            if idx in self.chunk_payloads:
                c_data = self.chunk_payloads[idx]
                total_len = len(c_data) + 1  # 1 byte for compression scheme (2 = zlib)

                # Length header (4 bytes) + version byte (1 byte) + zlib bytes
                chunk_header = struct.pack(">IB", total_len, 2)
                chunk_full = chunk_header + c_data

                # Pad to multiple of 4096 bytes
                sectors = math.ceil(len(chunk_full) / SECTOR_SIZE)
                pad_len = (sectors * SECTOR_SIZE) - len(chunk_full)
                padded_chunk = chunk_full + (b"\x00" * pad_len)

                self.locations[idx] = (sector_offset, sectors)
                payload_bytes.extend(padded_chunk)
                sector_offset += sectors
            else:
                self.locations[idx] = (0, 0)

        # Build Header
        header = bytearray(8192)
        for i in range(1024):
            offset, count = self.locations[i]
            # 3 bytes offset, 1 byte sector count
            header[i * 4 : i * 4 + 3] = offset.to_bytes(3, byteorder="big")
            header[i * 4 + 3] = count & 0xFF
            # Timestamp table
            struct.pack_into(">I", header, 4096 + i * 4, self.timestamps[i])

        with open(self.file_path, "wb") as f:
            f.write(header)
            f.write(payload_bytes)


def export_settlement_region_to_anvil(
    world_spec: WorldSpec,
    settlement_id: str,
    output_dir: Path,
) -> Path:
    """
    Exports a 400x400 block region centered on settlement_id to Minecraft Java Anvil (.mca) format.
    """
    voxel_spec = VoxelWorldSpec(world_spec=world_spec)
    s = world_spec.get_site(settlement_id)
    if not s:
        s = world_spec.settlements[0]

    scx, scz = voxel_spec.tile_to_block_center(s.x, s.y)

    # 400x400 block region = 25x25 chunks
    center_cx = scx // 16
    center_cz = scz // 16
    radius_chunks = 12  # 25 chunks wide (-12 to +12)

    region_path = output_dir / "region" / "r.0.0.mca"
    writer = AnvilRegionWriter(region_path)

    for dz in range(-radius_chunks, radius_chunks + 1):
        cz = center_cz + dz
        for dx in range(-radius_chunks, radius_chunks + 1):
            cx = center_cx + dx

            # Map to 0..31 region local indices
            rx = (dx + radius_chunks) % 32
            rz = (dz + radius_chunks) % 32

            chunk = generate_chunk(cx, cz, voxel_spec)
            compressed_nbt = serialize_chunk_to_nbt(cx, cz, chunk)
            writer.add_chunk(rx, rz, compressed_nbt)

    writer.write()

    # Generate minimal level.dat
    _write_level_dat(output_dir, level_name=f"Minemesis_{s.name}", spawn_x=scx, spawn_z=scz, spawn_y=voxel_spec.get_interpolated_height(scx, scz) + 2)

    return region_path


def export_full_world_to_anvil(
    world_spec: WorldSpec,
    output_dir: Path,
) -> List[Path]:
    """
    Exports full 2400x2400 block continent (150x150 chunks) into Minecraft Java region files.
    """
    voxel_spec = VoxelWorldSpec(world_spec=world_spec)
    region_dir = output_dir / "region"
    region_dir.mkdir(parents=True, exist_ok=True)

    # 150 chunks / 32 chunks per region = 5x5 regions (r.0.0.mca to r.4.4.mca)
    exported_files = []

    for reg_z in range(5):
        for reg_x in range(5):
            r_file = region_dir / f"r.{reg_x}.{reg_z}.mca"
            writer = AnvilRegionWriter(r_file)

            min_cx = reg_x * 32
            max_cx = min(150, min_cx + 32)
            min_cz = reg_z * 32
            max_cz = min(150, min_cz + 32)

            for cz in range(min_cz, max_cz):
                rz = cz - (reg_z * 32)
                for cx in range(min_cx, max_cx):
                    rx = cx - (reg_x * 32)

                    chunk = generate_chunk(cx, cz, voxel_spec)
                    comp_nbt = serialize_chunk_to_nbt(cx, cz, chunk)
                    writer.add_chunk(rx, rz, comp_nbt)

            writer.write()
            exported_files.append(r_file)

    s0 = world_spec.settlements[0]
    sp_x, sp_z = voxel_spec.tile_to_block_center(s0.x, s0.y)
    sp_y = voxel_spec.get_interpolated_height(sp_x, sp_z) + 2
    _write_level_dat(output_dir, level_name=f"Minemesis_Seed_{world_spec.world_seed}", spawn_x=sp_x, spawn_z=sp_z, spawn_y=sp_y)

    return exported_files


def _write_level_dat(world_dir: Path, level_name: str, spawn_x: int, spawn_z: int, spawn_y: int) -> None:
    """Generates standard Minecraft Java level.dat file."""
    level_compound = {
        "Data": (NBT.COMPOUND, {
            "LevelName": (NBT.STRING, level_name),
            "SpawnX": (NBT.INT, spawn_x),
            "SpawnY": (NBT.INT, spawn_y),
            "SpawnZ": (NBT.INT, spawn_z),
            "GameType": (NBT.INT, 0),  # Survival
            "Difficulty": (NBT.BYTE, 1),  # Easy
            "hardcore": (NBT.BYTE, 0),
            "DayTime": (NBT.LONG, 1000),
            "Time": (NBT.LONG, 1000),
            "version": (NBT.INT, 19133),
            "DataVersion": (NBT.INT, MINECRAFT_DATA_VERSION),
            "allowCommands": (NBT.BYTE, 1),
        })
    }
    raw_nbt = write_nbt_tag(NBT.COMPOUND, "", level_compound)
    # Standard GZIP compression for level.dat
    import gzip
    dat_path = world_dir / "level.dat"
    dat_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dat_path, "wb") as f:
        f.write(bytes(raw_nbt))
