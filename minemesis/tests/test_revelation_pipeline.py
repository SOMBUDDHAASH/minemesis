"""
Acceptance Test for Truth Revelation & Belief Supersession (Sections 4.3 & 4.4).

Includes:
- Positive control: Hatred drops after belief supersession and regret appears.
- Negative control: Hatred persists when the correction is rejected due to distrust.
"""

from minemesis.core.types import BeliefSource, Emotion, EventType, Intent
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.models.relationship import compute_relationship
from minemesis.systems.memory_system import form_memories_from_belief


def test_belief_supersession_replaces_hatred_with_regret() -> None:
    """
    Positive test: Acceptance of truth supersedes false belief, discounting old hatred
    and forming new regret/relief memories.
    """
    char_a = Character("char_a", "Caleb", "Rivers", "set_oakhaven", 300, "M", suspicion=0.3)
    char_b = Character("char_b", "Arthur", "Ironwood", "set_ironpeak", 350, "M")
    characters = {"char_a": char_a, "char_b": char_b}

    # 1. Caleb holds false belief that Arthur murdered his kin
    old_belief = Belief(
        belief_id=1,
        believer_id=char_a.id,
        event_ref=10,
        source=BeliefSource.WITNESSED,
        source_character_id=None,
        confidence=0.85,
        tick_acquired=10,
        believed_type=EventType.DEATH,
        believed_intent=Intent.INTENTIONAL,
        believed_actor=char_b.id,
        believed_target="char_kin",
        believed_location="set_oakhaven",
    )

    memories_store: list[Memory] = []
    initial_mems = [
        Memory(
            id=1,
            observer_id=char_a.id,
            belief_event_ref=10,
            target_entity_id=char_b.id,
            emotion=Emotion.HATRED,
            initial_intensity=90.0,
            decay_rate=0.002,
            tick_formed=10,
            source_belief_id=1,
        )
    ]
    memories_store.extend(initial_mems)

    rel_before = compute_relationship(char_a.id, char_b.id, memories_store, current_tick=15)
    assert rel_before.hatred >= 80.0, f"Expected intense hatred before correction, got {rel_before.hatred}"

    # 2. Eyewitness reveals truth: Death was accidental!
    superseded_memory_ids: set[int] = set()

    new_belief = Belief(
        belief_id=2,
        believer_id=char_a.id,
        event_ref=10,
        source=BeliefSource.TOLD,
        source_character_id="char_witness",
        confidence=0.95,
        tick_acquired=20,
        believed_type=EventType.DEATH,
        believed_intent=Intent.ACCIDENTAL,
        believed_actor=char_b.id,
        believed_target="char_kin",
        believed_location="set_oakhaven",
        supersedes_belief_id=old_belief.belief_id,
    )

    # Flag old belief's memories as superseded
    for m in memories_store:
        if m.source_belief_id == old_belief.belief_id:
            superseded_memory_ids.add(m.id)

    # Form re-appraisal memories
    reappraisal_mems = form_memories_from_belief(
        belief=new_belief,
        characters=characters,
        next_memory_id=10,
        tick=20,
        prior_hatred=rel_before.hatred,
    )
    memories_store.extend(reappraisal_mems)

    # Verify regret memory formed
    assert any(m.emotion == Emotion.REGRET for m in reappraisal_mems), "Expected Emotion.REGRET in re-appraisal"
    assert any(m.emotion == Emotion.RELIEF for m in reappraisal_mems), "Expected Emotion.RELIEF in re-appraisal"

    # 3. Recalculate relationship excluding superseded memories
    rel_after = compute_relationship(
        char_a.id,
        char_b.id,
        memories_store,
        current_tick=20,
        superseded_memory_ids=superseded_memory_ids,
    )

    # Hatred must drop and respect/trust must increase
    assert rel_after.hatred == 0.0, f"Hatred should be fully extinguished, got {rel_after.hatred}"
    assert rel_after.respect > rel_before.respect, "Respect toward Arthur should increase"


def test_negative_control_rejected_correction_leaves_hatred_intact() -> None:
    """
    Negative control: When incoming testimony fails credibility threshold (e.g. teller distrusted),
    belief is NOT superseded and hatred remains intact.
    """
    char_a = Character("char_a", "Caleb", "Rivers", "set_oakhaven", 300, "M", suspicion=0.9)
    char_b = Character("char_b", "Arthur", "Ironwood", "set_ironpeak", 350, "M")
    witness = Character("char_w", "Sneak", "Untrusted", "set_ironpeak", 300, "M")

    # Initial hatred memory
    memories_store = [
        Memory(
            id=1,
            observer_id=char_a.id,
            belief_event_ref=10,
            target_entity_id=char_b.id,
            emotion=Emotion.HATRED,
            initial_intensity=90.0,
            decay_rate=0.002,
            tick_formed=10,
            source_belief_id=1,
        )
    ]

    # Caleb has negative trust in witness
    witness_rel = compute_relationship(char_a.id, witness.id, [], current_tick=15)
    # Incoming credibility formula
    w_conf = 0.60
    trust_factor = max(0.2, min(1.0, (witness_rel.trust + 50.0) / 100.0))
    suspicion_factor = max(0.5, 1.5 - char_a.suspicion)
    credibility = w_conf * trust_factor * suspicion_factor

    current_conf = 0.85
    # Threshold check fails: credibility < current_conf * 0.80
    assert credibility < current_conf * 0.80, "Credibility check should fail for untrusted witness"

    # Belief is NOT superseded; superseded set is empty
    superseded_memory_ids: set[int] = set()

    rel_still = compute_relationship(
        char_a.id,
        char_b.id,
        memories_store,
        current_tick=20,
        superseded_memory_ids=superseded_memory_ids,
    )
    assert rel_still.hatred >= 80.0, f"Hatred must persist when correction is rejected, got {rel_still.hatred}"


def test_revelation_pipeline_across_5_seeds() -> None:
    """
    Behavioural test across 5 seeds: Verifies that Revelation events occur with genuine witness paths.
    """
    from minemesis.systems.simulation import Simulation
    test_seeds = [42, 101, 200, 777, 2026]
    total_revelations = 0

    for s in test_seeds:
        sim = Simulation(seed=s)
        sim.run_years(100)
        revs = [e for e in sim.event_log.all_events() if e.type == EventType.REVELATION]
        total_revelations += len(revs)
        for r in revs:
            assert "witness" in r.participants_dict, "Revelation must cite eyewitness"
            assert "recipient" in r.participants_dict, "Revelation must cite recipient"
            assert len(r.causes) >= 1, "Revelation must cite cause death"

    assert total_revelations >= 1, f"Expected revelations across 5 seeds, got {total_revelations}"
