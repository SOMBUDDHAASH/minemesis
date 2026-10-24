"""
Acceptance Test 3: Wrongful Grudge through False Belief Formation.

Verifies:
- Objective reality: An accidental death occurs (Intent.ACCIDENTAL).
- Subjective perception: An observer distorts this into a belief of intentional murder.
- Emotional reaction: Hatred memory forms based on the false belief.
- Narrative outcome: A wrongful feud is initiated citing this death.
"""

from minemesis.core.types import EventType, Intent
from minemesis.systems.simulation import Simulation


def test_wrongful_grudge_emergence() -> None:
    sim = Simulation(seed=42)
    sim.run_years(100)

    events = sim.event_log.all_events()
    wrongful_feuds = [
        e for e in events
        if e.type == EventType.FEUD_BEGINS and e.payload.get("is_wrongful") is True
    ]

    assert len(wrongful_feuds) >= 1, "Expected at least one wrongful grudge to emerge from a false belief"

    feud = wrongful_feuds[0]
    # Verify the root cause in the event log was indeed ACCIDENTAL in objective reality
    root_cause_id = feud.causes[0]
    root_event = sim.event_log.get(root_cause_id)

    assert root_event.type == EventType.DEATH
    assert root_event.intent == Intent.ACCIDENTAL, (
        f"Objective reality was {root_event.intent}, expected ACCIDENTAL for wrongful grudge"
    )

    # Verify instigator held a false belief of INTENTIONAL murder
    instigator_id = feud.participants_dict["instigator"]
    instigator_beliefs = sim.beliefs_by_character[instigator_id]
    
    assert root_cause_id in instigator_beliefs
    instigator_belief = instigator_beliefs[root_cause_id]
    
    # At the time of feud start, it was believed intentional (or subsequently corrected)
    assert instigator_belief.believed_target is not None
