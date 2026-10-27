"""
Voxel Chunk Data Structure (16 x 16 x 256).
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Optional, Tuple


CHUNK_WIDTH = 16
CHUNK_DEPTH = 16
CHUNK_HEIGHT = 256
VOXELS_PER_CHUNK = CHUNK_WIDTH * CHUNK_DEPTH * CHUNK_HEIGHT  # 65,536


class Chunk:
    """16x16x256 voxel column container with chunk deltas and dirty tracking."""

    def __init__(self, cx: int, cz: int) -> None:
        self.cx = cx
        self.cz = cz
        # Fast 1D uint16 array for block indices (Index: y * 256 + z * 16 + x)
        self.blocks = np.zeros(VOXELS_PER_CHUNK, dtype=np.uint16)
        self.deltas: Dict[Tuple[int, int, int], int] = {}
        self.is_dirty: bool = True
        self.opaque_mesh = None
        self.transparent_mesh = None

    @staticmethod
    def get_index(x: int, y: int, z: int) -> int:
        return (y << 8) | (z << 4) | x

    def get_block(self, lx: int, y: int, lz: int) -> int:
        if 0 <= lx < 16 and 0 <= y < 256 and 0 <= lz < 16:
            return int(self.blocks[(y << 8) | (lz << 4) | lx])
        return 0

    def set_block(self, lx: int, y: int, lz: int, block_id: int, record_delta: bool = True) -> bool:
        if 0 <= lx < 16 and 0 <= y < 256 and 0 <= lz < 16:
            idx = (y << 8) | (lz << 4) | lx
            old = self.blocks[idx]
            if old != block_id:
                self.blocks[idx] = block_id
                self.is_dirty = True
                if record_delta:
                    self.deltas[(lx, y, lz)] = block_id
                return True
        return False
