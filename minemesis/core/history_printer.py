"""
History Printer: traces causal chains backward from any event.

Adheres to agent.md and Milestone 0.5 requirements (Section 4.1):
- Given any event, print causal chain back through history.
- Calculates longest causal path and counts distinct event types along deepest chain.
- Efficient DAG rendering (avoids exponential subtree re-printing).
"""

from __future__ import annotations
from typing import Sequence, Set
from minemesis.core.event_log import Event, EventLog
from minemesis.core.types import EventType, Intent


def get_causal_depth(event_log: EventLog, event_id: int, memo: dict[int, int] | None = None) -> int:
    """
    Returns the maximum depth of backwards causal chain from this event.
    Depth 0 means no causes (root event).
    """
    if memo is not None and event_id in memo:
        return memo[event_id]
    evt = event_log.get(event_id)
    if not evt.causes:
        res = 0
    else:
        res = 1 + max(get_causal_depth(event_log, c_id, memo=memo) for c_id in evt.causes)
    if memo is not None:
        memo[event_id] = res
    return res


def get_longest_causal_path(
    event_log: EventLog, event_id: int, memo: dict[int, list[int]] | None = None
) -> list[int]:
    """
    Returns the list of Event IDs along the longest causal path ending at event_id.
    """
    if memo is not None and event_id in memo:
        return memo[event_id]
    evt = event_log.get(event_id)
    if not evt.causes:
        res = [event_id]
        if memo is not None:
            memo[event_id] = res
        return res

    longest_ancestor_path: list[int] = []
    for c_id in evt.causes:
        ancestor_path = get_longest_causal_path(event_log, c_id, memo=memo)
        if len(ancestor_path) > len(longest_ancestor_path):
            longest_ancestor_path = ancestor_path

    res = longest_ancestor_path + [event_id]
    if memo is not None:
        memo[event_id] = res
    return res


def get_distinct_event_types_on_path(event_log: EventLog, path: Sequence[int]) -> set[EventType]:
    """
    Returns the set of distinct EventTypes on a causal path.
    """
    return {event_log.get(e_id).type for e_id in path}


CONFLICT_EVENT_TYPES = frozenset({
    EventType.DEATH,
    EventType.FEUD,
    EventType.RAID,
    EventType.FAMINE,
    EventType.SUCCESSION_CRISIS,
    EventType.PEACE,
    EventType.REVELATION,
})


def get_longest_conflict_path(
    event_log: EventLog, event_id: int, memo: dict[int, list[int]] | None = None
) -> list[int]:
    """
    Returns the list of Event IDs along the longest conflict causal path ending at event_id.
    Edges and nodes are strictly restricted to CONFLICT_EVENT_TYPES:
    Death, Feud, Raid, Famine, SuccessionCrisis, Peace, Revelation.
    """
    if memo is not None and event_id in memo:
        return memo[event_id]

    evt = event_log.get(event_id)
    if evt.type not in CONFLICT_EVENT_TYPES:
        res = []
        if memo is not None:
            memo[event_id] = res
        return res

    valid_causes = [c_id for c_id in evt.causes if event_log.get(c_id).type in CONFLICT_EVENT_TYPES]
    if not valid_causes:
        res = [event_id]
        if memo is not None:
            memo[event_id] = res
        return res

    longest_ancestor: list[int] = []
    for c_id in valid_causes:
        ancestor_path = get_longest_conflict_path(event_log, c_id, memo=memo)
        if len(ancestor_path) > len(longest_ancestor):
            longest_ancestor = ancestor_path

    res = longest_ancestor + [event_id]
    if memo is not None:
        memo[event_id] = res
    return res


def get_deepest_conflict_chain_metrics(event_log: EventLog) -> tuple[int, int, int]:
    """
    Scans the entire event log and returns:
    (event_id_with_deepest_conflict_path, conflict_path_depth, distinct_conflict_types_count)
    Depth is defined as the number of conflict edges (len(path) - 1).
    """
    best_id = -1
    best_depth = -1
    best_types_count = 0
    memo: dict[int, list[int]] = {}

    for evt in event_log.all_events():
        if evt.type not in CONFLICT_EVENT_TYPES:
            continue
        path = get_longest_conflict_path(event_log, evt.id, memo=memo)
        if not path:
            continue
        depth = len(path) - 1
        distinct_types = len(get_distinct_event_types_on_path(event_log, path))
        if depth > best_depth or (depth == best_depth and distinct_types > best_types_count):
            best_id = evt.id
            best_depth = depth
            best_types_count = distinct_types

    return best_id, max(0, best_depth), best_types_count


def get_deepest_causal_chain_metrics(event_log: EventLog) -> tuple[int, int, int]:
    """
    Scans the entire event log and returns:
    (event_id_with_deepest_path, path_depth, distinct_event_types_count)
    """
    best_id = -1
    best_depth = -1
    best_types_count = 0
    memo: dict[int, list[int]] = {}

    for evt in event_log.all_events():
        path = get_longest_causal_path(event_log, evt.id, memo=memo)
        depth = len(path) - 1
        distinct_types = len(get_distinct_event_types_on_path(event_log, path))
        if depth > best_depth or (depth == best_depth and distinct_types > best_types_count):
            best_id = evt.id
            best_depth = depth
            best_types_count = distinct_types

    return best_id, best_depth, best_types_count


def format_causal_chain(
    event_log: EventLog,
    event_id: int,
    indent_level: int = 0,
    already_printed: Set[int] | None = None,
    characters: Mapping[str, Any] | None = None,
) -> str:
    """
    Renders a formatted text causal DAG for an event without exponential re-printing.
    Displays event causes and resolves character IDs to 'Full Name (id)'.
    """
    if already_printed is None:
        already_printed = set()

    evt = event_log.get(event_id)
    indent = "  " * indent_level
    bullet = "|-> " if indent_level > 0 else "* "

    # Resolve character names if available
    part_strs = []
    for role, name in evt.participants:
        if characters and name in characters:
            c_obj = characters[name]
            full_name = getattr(c_obj, "full_name", str(name))
            part_strs.append(f"{role}={full_name} ({name})")
        else:
            part_strs.append(f"{role}={name}")
    participants_str = ", ".join(part_strs)

    causes_str = f"Causes: [{', '.join(f'#{c}' for c in evt.causes)}]" if evt.causes else "Causes: none (root)"
    desc = f"[Event #{evt.id} | Year {evt.tick // 12 + 1} Month {evt.tick % 12 + 1}] {evt.type.value} ({evt.intent.value}) @ {evt.location} | {causes_str}"
    details = f"{desc} | {participants_str}"
    
    if "description" in evt.payload:
        details += f" -- \"{evt.payload['description']}\""

    if event_id in already_printed:
        return f"{indent}{bullet}{details} (causal history detailed above)"

    already_printed.add(event_id)
    lines = [f"{indent}{bullet}{details}"]

    for cause_id in evt.causes:
        lines.append(format_causal_chain(event_log, cause_id, indent_level + 1, already_printed, characters))

    return "\n".join(lines)


def format_notable_deaths(
    event_log: EventLog,
    characters: Mapping[str, Any] | None = None,
) -> list[str]:
    """
    Extracts and formats all notable deaths with their antecedent causes:
    - Chiefs and leaders
    - Revenge victims
    - Accident victims (forestry mishaps)
    - Starvation deaths during famine
    - Raid casualties
    - Religious martyrs/saints
    """
    notable: list[str] = []
    for evt in event_log.all_events():
        if evt.type == EventType.DEATH:
            victim_id = (
                evt.participants_dict.get("deceased")
                or evt.participants_dict.get("target")
                or evt.participants_dict.get("victim")
            )
            victim_name = str(victim_id)
            if characters and victim_id in characters:
                c_obj = characters[victim_id]
                victim_name = f"{getattr(c_obj, 'full_name', victim_id)} ({victim_id})"
            elif "victim_name" in evt.payload:
                victim_name = f"{evt.payload['victim_name']} ({victim_id})"

            causes_str = f"Causes: [{', '.join(f'#{c}' for c in evt.causes)}]" if evt.causes else "Causes: none (natural/root)"
            
            is_revenge = evt.payload.get("revenge") or ("Revenge" in str(evt.payload))
            is_accidental = evt.intent == Intent.ACCIDENTAL
            is_raid = any(event_log.get(c).type == EventType.RAID for c in evt.causes)
            is_famine = any(event_log.get(c).type == EventType.FAMINE for c in evt.causes)
            
            category = "Natural"
            if is_revenge:
                category = "Revenge"
            elif is_raid:
                category = "Raid Casualty"
            elif is_famine:
                category = "Starvation"
            elif is_accidental:
                category = "Accident"

            line = (
                f"[Year {evt.tick // 12 + 1:2d} Month {evt.tick % 12 + 1:2d} | Event #{evt.id:3d}] "
                f"Death of {victim_name} @ {evt.location} | Category: {category} | {causes_str}"
            )
            if "description" in evt.payload:
                line += f" -- \"{evt.payload['description']}\""
            notable.append(line)

    return notable


def format_linear_history(event_log: EventLog, event_id: int) -> list[str]:
    """
    Returns a top-down list of events leading up to this event along its longest causal path.
    """
    path = get_longest_causal_path(event_log, event_id)
    result = []
    for e_id in path:
        e = event_log.get(e_id)
        result.append(
            f"[Year {e.tick // 12 + 1:2d} M{e.tick % 12 + 1:2d} (Tick {e.tick:4d})] "
            f"Event #{e.id:3d}: {e.type.value:17s} | {e.intent.value:14s} | "
            f"Loc: {e.location:12s} | "
            f"{e.payload.get('description', '')}"
        )
    return result


def export_causal_graph_dot(event_log: EventLog, event_id: int) -> str:
    """
    Exports the complete backwards causal DAG for event_id in Graphviz DOT format.
    """
    visited: set[int] = set()
    edges: list[tuple[int, int]] = []

    def collect(e_id: int) -> None:
        if e_id in visited:
            return
        visited.add(e_id)
        evt = event_log.get(e_id)
        for c in evt.causes:
            edges.append((c, e_id))
            collect(c)

    collect(event_id)

    lines = ["digraph CausalStory {", "  rankdir=LR;", "  node [shape=box, style=rounded, fontname=\"Arial\"];"]
    for e_id in sorted(visited):
        evt = event_log.get(e_id)
        label = f"#{evt.id}: {evt.type.value}\\nYear {evt.tick // 12 + 1} M{evt.tick % 12 + 1}"
        lines.append(f'  node_{e_id} [label="{label}"];')

    for src, dst in edges:
        lines.append(f"  node_{src} -> node_{dst};")

    lines.append("}")
    return "\n".join(lines)


def export_causal_graph_mermaid(event_log: EventLog, event_id: int) -> str:
    """
    Exports the complete backwards causal DAG for event_id in Mermaid format.
    """
    visited: set[int] = set()
    edges: list[tuple[int, int]] = []

    def collect(e_id: int) -> None:
        if e_id in visited:
            return
        visited.add(e_id)
        evt = event_log.get(e_id)
        for c in evt.causes:
            edges.append((c, e_id))
            collect(c)

    collect(event_id)

    lines = ["graph LR"]
    for e_id in sorted(visited):
        evt = event_log.get(e_id)
        clean_desc = evt.type.value
        lines.append(f'  E{e_id}["#{evt.id}: {clean_desc} (Y{evt.tick // 12 + 1})"]')

    for src, dst in edges:
        lines.append(f"  E{src} --> E{dst}")

    return "\n".join(lines)
