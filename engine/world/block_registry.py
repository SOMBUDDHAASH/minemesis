"""
Block Registry and Material Metadata Provider for Minemesis Engine.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional, Set


class BlockDef:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self.id: int = raw["id"]
        self.name: str = raw["name"]
        self.category: str = raw.get("category", "rock")
        self.hardness: float = float(raw.get("hardness", 1.0))
        self.transparent: bool = bool(raw.get("transparent", False))
        self.texture: str = raw.get("texture", "stone")
        self.tags: Set[str] = set(raw.get("tags", []))
        self.drops: str = raw.get("drops", self.name)


class BlockRegistry:
    """Singleton registry holding all original block definitions."""

    def __init__(self, json_path: Optional[str | Path] = None) -> None:
        if json_path is None:
            # Look in data/blocks.json relative to project root or sys._MEIPASS
            import sys
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
            json_path = base / "data" / "blocks.json"

        p = Path(json_path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.blocks_by_id: Dict[int, BlockDef] = {}
        self.blocks_by_name: Dict[str, BlockDef] = {}
        self.solid_ids: Set[int] = set()
        self.transparent_ids: Set[int] = set()

        for raw in data.get("blocks", []):
            b = BlockDef(raw)
            self.blocks_by_id[b.id] = b
            self.blocks_by_name[b.name] = b
            if not b.transparent and b.id != 0:
                self.solid_ids.add(b.id)
            if b.transparent and b.id != 0:
                self.transparent_ids.add(b.id)

    def get_by_id(self, block_id: int) -> Optional[BlockDef]:
        return self.blocks_by_id.get(block_id)

    def get_by_name(self, name: str) -> Optional[BlockDef]:
        return self.blocks_by_name.get(name)

    def is_solid(self, block_id: int) -> bool:
        return block_id in self.solid_ids

    def is_transparent(self, block_id: int) -> bool:
        return block_id == 0 or block_id in self.transparent_ids


# Global singleton instance
registry = BlockRegistry()
