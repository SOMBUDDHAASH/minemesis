"""
Conflict Storyline & Thread Detection Engine for Minemesis Story Viewer.

Discovers connected causal components of conflict events (Feuds, Raids, Murders,
Revenge, Peace, Succession Crises) with >= 3 events and builds deterministic titles.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from minemesis.core.history_printer import get_causal_depth, get_longest_conflict_path
from minemesis.core.types import EventType
from viewer.formatter import format_character_name, format_settlement_name


CONFLICT_EVENT_TYPES = {
    EventType.DEATH.value,
    EventType.FEUD.value,
    EventType.RAID.value,
    EventType.FAMINE.value,
    EventType.SUCCESSION_CRISIS.value,
    EventType.PEACE.value,
    EventType.REVELATION.value,
}


@dataclass
class StoryThread:
    thread_id: str
    title: str
    start_year: int
    end_year: int
    event_ids: list[int]
    longest_chain_depth: int
    root_event_id: int
    summary: str

    @property
    def year_span(self) -> str:
        if self.start_year == self.end_year:
            return f"Year {self.start_year}"
        return f"Year {self.start_year} to Year {self.end_year}"

    @property
    def event_count(self) -> int:
        return len(self.event_ids)


def extract_story_threads(
    event_log: Any,
    characters: Mapping[str, Any],
    settlements: Mapping[str, Any],
    min_events: int = 3,
) -> list[StoryThread]:
    """
    Groups connected conflict events into coherent historical storylines.
    """
    events = event_log.all_events() if hasattr(event_log, "all_events") else event_log
    
    # 1. Filter conflict events
    conflict_events = []
    conflict_ids = set()
    for e in events:
        e_type_val = e.type.value if hasattr(e.type, "value") else str(e.type)
        if e_type_val in CONFLICT_EVENT_TYPES:
            conflict_events.append(e)
            conflict_ids.add(e.id)

    if not conflict_events:
        return []

    # 2. Build graph adjacency among conflict events (both causes and reverse causes)
    adj: dict[int, set[int]] = {e.id: set() for e in conflict_events}
    for e in conflict_events:
        for c_id in getattr(e, "causes", ()):
            if c_id in conflict_ids:
                adj[e.id].add(c_id)
                adj[c_id].add(e.id)

    # 3. Find connected components
    visited = set()
    components: list[list[int]] = []
    for e in conflict_events:
        if e.id not in visited:
            comp: list[int] = []
            queue = [e.id]
            visited.add(e.id)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj.get(curr, ()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(comp) >= min_events:
                components.append(sorted(comp))

    # 4. Synthesize StoryThread objects
    threads: list[StoryThread] = []
    for idx, comp in enumerate(components):
        comp_events = [event_log.get(e_id) for e_id in comp]
        comp_events.sort(key=lambda e: e.tick)

        first_evt = comp_events[0]
        last_evt = comp_events[-1]

        start_year = (first_evt.tick // 12) + 1
        end_year = (last_evt.tick // 12) + 1

        # Calculate longest causal chain in this component
        max_chain = 1
        for e in comp_events:
            path = get_longest_conflict_path(event_log, e.id)
            if len(path) > max_chain:
                max_chain = len(path)

        # Build deterministic title
        p_dict = dict(getattr(first_evt, "participants", ()))
        f_type_val = first_evt.type.value if hasattr(first_evt.type, "value") else str(first_evt.type)

        if f_type_val == "Feud":
            inst = format_character_name(p_dict.get("instigator", ""), characters)
            target = format_character_name(p_dict.get("target", ""), characters)
            title = f"The Feud between {inst} and {target}"
        elif f_type_val == "Raid":
            att = format_settlement_name(p_dict.get("attacker", ""), settlements)
            deff = format_settlement_name(p_dict.get("defender", ""), settlements)
            title = f"The Border Warfare of {att} and {deff}"
        elif f_type_val == "SuccessionCrisis":
            loc = format_settlement_name(first_evt.location, settlements)
            title = f"The Crisis of Succession in {loc}"
        elif f_type_val == "Famine":
            loc = format_settlement_name(first_evt.location, settlements)
            title = f"The Great Famine of {loc}"
        elif f_type_val == "Death":
            victim = format_character_name(p_dict.get("target") or p_dict.get("deceased", ""), characters)
            actor = format_character_name(p_dict.get("actor", ""), characters)
            if actor and actor != "Unknown Person":
                title = f"The Slaying of {victim} and its Aftermath"
            else:
                title = f"The Tragic Death of {victim} and its Escalation"
        else:
            loc = format_settlement_name(first_evt.location, settlements)
            title = f"The Strife of {loc}"

        full_title = f"{title} ({start_year == end_year and f'Year {start_year}' or f'Year {start_year} to Year {end_year}'})"

        summary = (
            f"{len(comp)} connected historical events spanning {end_year - start_year + 1} years. "
            f"Deepest conflict chain reaches depth {max_chain}."
        )

        threads.append(StoryThread(
            thread_id=f"thread_{idx+1}",
            title=full_title,
            start_year=start_year,
            end_year=end_year,
            event_ids=comp,
            longest_chain_depth=max_chain,
            root_event_id=first_evt.id,
            summary=summary,
        ))

    # Sort threads by event count and duration descending
    threads.sort(key=lambda t: (t.event_count, t.longest_chain_depth), reverse=True)
    return threads
