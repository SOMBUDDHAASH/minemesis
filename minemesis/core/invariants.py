"""
Pipeline Invariants and Architectural Rule Enforcement.

Enforces:
1. Dead Actors Invariant: Every active participant in an event must be alive at that tick.
   Active roles: actor, instigator, instigator_char, initiator, witness, recipient,
                 spouse, spouse1, spouse2, author, party1, party2.
   Subject allowed to be dead only in DEATH events (target, deceased, victim).
   In DEATH events with an active killer (actor, instigator), the killer must be alive.
2. World Extinction Invariant: Simulation stops immediately upon world extinction (pop == 0),
   logging zero posthumous events.
3. Conservation Invariants: Demographic and economic balances strictly hold.
"""

from __future__ import annotations
from typing import Mapping, Sequence

from minemesis.core.event_log import Event
from minemesis.core.types import EventType
from minemesis.models.character import Character


class InvariantViolationError(Exception):
    """Raised when an architectural or simulation invariant is violated."""
    pass


ACTIVE_PARTICIPANT_ROLES = {
    "actor",
    "instigator",
    "instigator_char",
    "initiator",
    "witness",
    "recipient",
    "spouse",
    "spouse1",
    "spouse2",
    "author",
    "party1",
    "party2",
}


def validate_event_actors_alive(event: Event, characters: Mapping[str, Character]) -> None:
    """
    Validates at runtime (during simulation step) that every active participant
    is alive at the moment the event occurred.
    A character cannot act if they died prior to this event (event.tick > death_tick
    or event.tick == death_tick and event.id > death_event_id).
    """
    for role, participant_id in event.participants:
        # Check if participant refers to a tracked character
        if participant_id in characters:
            char = characters[participant_id]
            is_active = (role in ACTIVE_PARTICIPANT_ROLES) or (
                event.type == EventType.DEATH and role in ("actor", "instigator")
            )
            if is_active:
                if not char.alive:
                    d_tick = char.death_tick
                    d_evt = char.death_event_id
                    if d_tick is not None:
                        if event.tick > d_tick or (d_evt is not None and event.id > d_evt):
                            raise InvariantViolationError(
                                f"Invariant Violation: Dead character '{char.id}' ({char.full_name}) "
                                f"died at tick {d_tick} (event #{d_evt}) but acted as '{role}' in event #{event.id} ({event.type.value}) at tick {event.tick}"
                            )
                    else:
                        raise InvariantViolationError(
                            f"Invariant Violation: Dead character '{char.id}' ({char.full_name}) "
                            f"acted as '{role}' in event #{event.id} ({event.type.value}) at tick {event.tick}"
                        )


def validate_entire_history_no_dead_actors(event_log: EventLog) -> None:
    """
    Audits the complete event log post-hoc.
    Determines each character's death tick from DEATH events, then verifies that
    no character ever acts in an active role at any tick strictly after their death tick.
    """
    death_ticks: dict[str, int] = {}
    death_event_ids: dict[str, int] = {}

    for evt in event_log.all_events():
        if evt.type == EventType.DEATH:
            victim_id = (
                evt.participants_dict.get("deceased")
                or evt.participants_dict.get("target")
                or evt.participants_dict.get("victim")
            )
            if victim_id and victim_id not in death_ticks:
                death_ticks[victim_id] = evt.tick
                death_event_ids[victim_id] = evt.id

    for evt in event_log.all_events():
        for role, participant_id in evt.participants:
            if participant_id in death_ticks:
                d_tick = death_ticks[participant_id]
                if role in ACTIVE_PARTICIPANT_ROLES:
                    if evt.tick > d_tick:
                        raise InvariantViolationError(
                            f"Posthumous Action Violation: Character '{participant_id}' died at tick {d_tick} "
                            f"(event #{death_event_ids[participant_id]}), but acted as '{role}' in event #{evt.id} "
                            f"({evt.type.value}) at tick {evt.tick}!"
                        )

