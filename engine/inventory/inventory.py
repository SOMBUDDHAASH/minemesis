"""
Player Inventory Model: 9-slot Hotbar, 27-slot Main Grid (3x9), 4 Equipment slots, and Cursor Stack.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from engine.inventory.item_stack import ItemStack


class Inventory:
    HOTBAR_SIZE = 9
    MAIN_GRID_SIZE = 27  # 3 rows x 9 columns
    EQUIPMENT_SLOTS = ("head", "chest", "legs", "offhand")

    def __init__(self) -> None:
        self.hotbar: List[Optional[ItemStack]] = [None] * self.HOTBAR_SIZE
        self.main_grid: List[Optional[ItemStack]] = [None] * self.MAIN_GRID_SIZE
        self.equipment: Dict[str, Optional[ItemStack]] = {k: None for k in self.EQUIPMENT_SLOTS}
        self.selected_slot: int = 0
        self.cursor_stack: Optional[ItemStack] = None
        self.gui_open: bool = False
        self._initialize_starter_kit()

    def _initialize_starter_kit(self) -> None:
        # Starter hotbar blocks (building, terrain, exploration)
        starter_blocks = [
            (1, 64),   # Limestone
            (52, 64),  # Oak Planks
            (18, 64),  # Loam Dirt
            (19, 64),  # Grass Turf
            (3, 64),   # Granite
            (51, 64),  # Oak Log
            (89, 64),  # Cut Stone Bricks
            (21, 64),  # Fine Sand
            (97, 64),  # Glass Pane
        ]
        for i, (bid, count) in enumerate(starter_blocks):
            self.hotbar[i] = ItemStack(block_id=bid, count=count)

        # Starter supplies in main storage
        self.main_grid[0] = ItemStack(block_id=100, count=4)   # Bookshelf
        self.main_grid[1] = ItemStack(block_id=101, count=2)   # Lectern
        self.main_grid[2] = ItemStack(block_id=136, count=16)  # Water bucket / flask
        self.main_grid[3] = ItemStack(block_id=45, count=32)   # Iron Ingot/Ore
        self.main_grid[4] = ItemStack(block_id=46, count=16)   # Gold Ingot/Ore

    def get_active_item(self) -> Optional[ItemStack]:
        if 0 <= self.selected_slot < self.HOTBAR_SIZE:
            return self.hotbar[self.selected_slot]
        return None

    def add_item(self, block_id: int, count: int = 1, metadata: Optional[dict] = None) -> int:
        """
        Attempts to add item into existing stacks, then empty hotbar slots, then main grid.
        Returns any remaining count that could not fit.
        """
        rem = count
        meta = metadata or {}

        # 1. Fill existing matching stacks in hotbar
        for stack in self.hotbar:
            if stack and stack.block_id == block_id and stack.metadata == meta:
                rem = stack.add(rem)
                if rem <= 0:
                    return 0

        # 2. Fill existing matching stacks in main grid
        for stack in self.main_grid:
            if stack and stack.block_id == block_id and stack.metadata == meta:
                rem = stack.add(rem)
                if rem <= 0:
                    return 0

        # 3. Place into empty hotbar slot
        for i in range(self.HOTBAR_SIZE):
            if self.hotbar[i] is None:
                to_place = min(64, rem)
                self.hotbar[i] = ItemStack(block_id=block_id, count=to_place, metadata=meta)
                rem -= to_place
                if rem <= 0:
                    return 0

        # 4. Place into empty main grid slot
        for i in range(self.MAIN_GRID_SIZE):
            if self.main_grid[i] is None:
                to_place = min(64, rem)
                self.main_grid[i] = ItemStack(block_id=block_id, count=to_place, metadata=meta)
                rem -= to_place
                if rem <= 0:
                    return 0

        return rem

    def consume_active_item(self) -> Optional[int]:
        """Consumes 1 item from active hotbar slot. Returns block_id or None."""
        active = self.get_active_item()
        if not active or active.count <= 0:
            return None
        bid = active.block_id
        active.count -= 1
        if active.count <= 0:
            self.hotbar[self.selected_slot] = None
        return bid

    def swap_slots(self, is_hotbar_a: bool, slot_a: int, is_hotbar_b: bool, slot_b: int) -> None:
        """Swaps or transfers items between two slots."""
        list_a = self.hotbar if is_hotbar_a else self.main_grid
        list_b = self.hotbar if is_hotbar_b else self.main_grid

        if not (0 <= slot_a < len(list_a)) or not (0 <= slot_b < len(list_b)):
            return

        item_a = list_a[slot_a]
        item_b = list_b[slot_b]

        # If same item type and can stack, combine them
        if item_a and item_b and item_a.can_stack_with(item_b):
            rem = item_b.add(item_a.count)
            if rem == 0:
                list_a[slot_a] = None
            else:
                item_a.count = rem
            return

        list_a[slot_a] = item_b
        list_b[slot_b] = item_a

    def get_slot_item(self, slot_type: str, slot_id: any) -> Optional[ItemStack]:
        if slot_type == "hotbar" and 0 <= int(slot_id) < self.HOTBAR_SIZE:
            return self.hotbar[int(slot_id)]
        elif slot_type == "main" and 0 <= int(slot_id) < self.MAIN_GRID_SIZE:
            return self.main_grid[int(slot_id)]
        elif slot_type == "equipment" and str(slot_id) in self.equipment:
            return self.equipment[str(slot_id)]
        return None

    def set_slot_item(self, slot_type: str, slot_id: any, item: Optional[ItemStack]) -> None:
        if slot_type == "hotbar" and 0 <= int(slot_id) < self.HOTBAR_SIZE:
            self.hotbar[int(slot_id)] = item
        elif slot_type == "main" and 0 <= int(slot_id) < self.MAIN_GRID_SIZE:
            self.main_grid[int(slot_id)] = item
        elif slot_type == "equipment" and str(slot_id) in self.equipment:
            self.equipment[str(slot_id)] = item

    def handle_slot_click(self, slot_type: str, slot_id: any, button: int = 1, shift: bool = False) -> None:
        """
        Interactive Mouse Drag & Drop handler (Blatantly copied from Luanti / Minecraft):
        - button 1 (Left click): Pick up / Drop entire stack
        - button 2 (Right click): Split half stack (if empty cursor) or drop 1 item (if holding cursor stack)
        - shift + click: Quick transfer between hotbar and main storage
        """
        current_item = self.get_slot_item(slot_type, slot_id)

        # 1. Shift-Click Quick Move between hotbar and main storage
        if shift and current_item:
            if slot_type == "hotbar":
                rem = self.add_to_list(self.main_grid, current_item)
                if rem == 0:
                    self.set_slot_item(slot_type, slot_id, None)
            elif slot_type == "main":
                rem = self.add_to_list(self.hotbar, current_item)
                if rem == 0:
                    self.set_slot_item(slot_type, slot_id, None)
            return

        # 2. Left Click (Button 1): Full stack pickup / deposit / swap
        if button == 1:
            if self.cursor_stack is None:
                if current_item is not None:
                    self.cursor_stack = current_item
                    self.set_slot_item(slot_type, slot_id, None)
            else:
                if current_item is None:
                    self.set_slot_item(slot_type, slot_id, self.cursor_stack)
                    self.cursor_stack = None
                elif self.cursor_stack.can_stack_with(current_item):
                    rem = current_item.add(self.cursor_stack.count)
                    if rem == 0:
                        self.cursor_stack = None
                    else:
                        self.cursor_stack.count = rem
                else:
                    self.set_slot_item(slot_type, slot_id, self.cursor_stack)
                    self.cursor_stack = current_item

        # 3. Right Click (Button 2): Split or single item drop
        elif button == 2:
            if self.cursor_stack is None:
                if current_item and current_item.count > 1:
                    half = current_item.count // 2
                    self.cursor_stack = current_item.split(half)
                elif current_item:
                    self.cursor_stack = current_item
                    self.set_slot_item(slot_type, slot_id, None)
            else:
                if current_item is None:
                    single = self.cursor_stack.split(1)
                    self.set_slot_item(slot_type, slot_id, single)
                    if self.cursor_stack.count <= 0:
                        self.cursor_stack = None
                elif self.cursor_stack.can_stack_with(current_item):
                    rem = current_item.add(1)
                    if rem == 0:
                        self.cursor_stack.count -= 1
                        if self.cursor_stack.count <= 0:
                            self.cursor_stack = None

    def add_to_list(self, target_list: List[Optional[ItemStack]], item: ItemStack) -> int:
        rem = item.count
        for s in target_list:
            if s and s.can_stack_with(item):
                rem = s.add(rem)
                if rem <= 0:
                    return 0
        for i in range(len(target_list)):
            if target_list[i] is None:
                to_place = min(64, rem)
                target_list[i] = ItemStack(block_id=item.block_id, count=to_place, metadata=dict(item.metadata))
                rem -= to_place
                if rem <= 0:
                    return 0
        item.count = rem
        return rem

    def to_dict(self) -> dict:
        return {
            "selected_slot": self.selected_slot,
            "hotbar": [s.to_dict() if s else None for s in self.hotbar],
            "main_grid": [s.to_dict() if s else None for s in self.main_grid],
            "equipment": {k: (s.to_dict() if s else None) for k, s in self.equipment.items()},
        }

    def from_dict(self, data: dict) -> None:
        self.selected_slot = data.get("selected_slot", 0)
        raw_hotbar = data.get("hotbar", [])
        self.hotbar = [ItemStack.from_dict(d) if d else None for d in raw_hotbar]
        while len(self.hotbar) < self.HOTBAR_SIZE:
            self.hotbar.append(None)

        raw_main = data.get("main_grid", [])
        self.main_grid = [ItemStack.from_dict(d) if d else None for d in raw_main]
        while len(self.main_grid) < self.MAIN_GRID_SIZE:
            self.main_grid.append(None)

        for k, d in data.get("equipment", {}).items():
            if k in self.equipment:
                self.equipment[k] = ItemStack.from_dict(d) if d else None
