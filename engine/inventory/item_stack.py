"""
ItemStack Data Structure for Minemesis Voxel Inventory System.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from engine.world.block_registry import registry


@dataclass
class ItemStack:
    """Represents a quantity of a specific block or item with optional lore metadata."""
    block_id: int
    count: int = 1
    max_stack: int = 64
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        if "name" in self.metadata:
            return str(self.metadata["name"])
        b_def = registry.get_by_id(self.block_id)
        return b_def.name if b_def else f"Block #{self.block_id}"

    @property
    def category(self) -> str:
        b_def = registry.get_by_id(self.block_id)
        return b_def.category if b_def else "item"

    def can_stack_with(self, other: Optional[ItemStack]) -> bool:
        if other is None:
            return False
        return (
            self.block_id == other.block_id
            and self.metadata == other.metadata
            and self.count < self.max_stack
        )

    def add(self, amount: int) -> int:
        """Adds up to max_stack. Returns remainder that could not fit."""
        if amount <= 0:
            return 0
        space = self.max_stack - self.count
        to_add = min(space, amount)
        self.count += to_add
        return amount - to_add

    def split(self, amount: int) -> Optional[ItemStack]:
        """Splits off up to amount items into a new stack."""
        if amount <= 0 or self.count <= 0:
            return None
        split_count = min(self.count, amount)
        self.count -= split_count
        return ItemStack(
            block_id=self.block_id,
            count=split_count,
            max_stack=self.max_stack,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "count": self.count,
            "max_stack": self.max_stack,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ItemStack:
        return cls(
            block_id=data["block_id"],
            count=data.get("count", 1),
            max_stack=data.get("max_stack", 64),
            metadata=data.get("metadata", {}),
        )
