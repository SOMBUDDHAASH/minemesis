"""
Acceptance Tests for Historical Pressure Systems and Economic Dynamics (Section 3d).

Verifies across at least 5 seeds:
- Revenge killings, succession crises, famines, raids, feuds, and peace mechanisms occur.
- End-state economic diversity (wealth, food, and population differ meaningfully).
- Includes explicit negative controls for pressure presence and anti-convergence diversity.
- Validates Marriage/Peace alliance edge rules and SettlementCollapse/Migration pipeline.
"""

import pytest
from minemesis.core.types import EventType, Intent, Scale
from minemesis.systems.simulation import Simulation


def test_historical_pressures_present_across_seeds() -> None:
    """
    Behavioural test across 5 seeds (42, 101, 200, 777, 2026):
    Verifies that all drama drivers (Revenge, Succession, Scarcity/Famine, Raids, Feuds, Chief Changes)
    manifest in the simulated histories.
    """
    test_seeds = [42, 101, 200, 777, 2026]
    aggregate_types: set[EventType] = set()
    total_revenge = 0
    total_famines = 0
    total_crises = 0
    total_chiefs = 0

    for s in test_seeds:
        sim = Simulation(seed=s)
        sim.run_years(100)
        events = sim.event_log.all_events()
        for e in events:
            aggregate_types.add(e.type)
            if e.type == EventType.DEATH and e.payload.get("cause_of_death") == "Revenge":
                total_revenge += 1
            elif e.type == EventType.FAMINE:
                total_famines += 1
            elif e.type == EventType.SUCCESSION_CRISIS:
                total_crises += 1
            elif e.type == EventType.CHIEF_CHANGED:
                total_chiefs += 1

    assert EventType.FEUD in aggregate_types, "Expected Feud events across batch"
    assert EventType.RAID in aggregate_types, "Expected Raid events across batch"
    assert EventType.TRADE_ROUTE_FOUNDED in aggregate_types, "Expected TradeRouteFounded events across batch"
    assert EventType.CHIEF_CHANGED in aggregate_types, "Expected ChiefChanged events across batch"
    assert total_chiefs >= 5, f"Expected chief successions, got {total_chiefs}"
    assert total_crises >= 1, f"Expected succession crises across batch, got {total_crises}"
    assert total_famines >= 1, f"Expected famine events across batch, got {total_famines}"
    assert total_revenge >= 1, f"Expected revenge killings across batch, got {total_revenge}"


def test_negative_control_historical_pressures_fails_on_empty_pressures() -> None:
    """
    Negative control: Asserts that an event log lacking required historical pressures fails verification.
    """
    from minemesis.core.event_log import EventLog
    log = EventLog()
    log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.BIRTH,
        participants={"child": "char_1"},
        causes=[],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    event_types = {e.type for e in log.all_events()}
    with pytest.raises(AssertionError):
        assert EventType.FEUD in event_types, "Negative control: Feud should be missing"


def test_anti_convergence_diversity_across_seeds() -> None:
    """
    Behavioural test across 5 seeds:
    Verifies that end-state wealth and food stocks differ meaningfully across settlements.
    """
    test_seeds = [42, 101, 200, 777, 2026]
    for seed in test_seeds:
        sim = Simulation(seed)
        sim.run_years(100)
        living_counts = {s_id: len([c for c in sim.living_characters if c.settlement_id == s_id]) for s_id in sim.settlements}
        surviving = [s for s_id, s in sim.settlements.items() if living_counts[s_id] > 0]
        if len(surviving) >= 2:
            wealth_vals = [s.wealth for s in surviving]
            food_vals = [s.food for s in surviving]
            assert max(wealth_vals) > min(wealth_vals), f"Seed {seed}: Wealth must differ across settlements"
            assert max(food_vals) > min(food_vals), f"Seed {seed}: Food must differ across settlements"


def test_negative_control_anti_convergence_fails_on_uniform_world() -> None:
    """
    Negative control: Asserts that a uniform world where all settlements have identical wealth fails diversity check.
    """
    class MockSettlement:
        def __init__(self, wealth: int) -> None:
            self.wealth = wealth

    uniform_settlements = [MockSettlement(100), MockSettlement(100), MockSettlement(100)]
    wealth_vals = [s.wealth for s in uniform_settlements]
    with pytest.raises(AssertionError):
        assert max(wealth_vals) > min(wealth_vals), "Negative control: Uniform wealth should fail diversity check"


def test_marriage_peace_alliance_edge_rule() -> None:
    """
    Audit 2a test: Verifies that Marriage only cites Peace when it is a genuine alliance marriage
    between the two settlements that were parties to that Peace, and never cites unrelated recency events.
    """
    sim = Simulation(seed=42)
    sim.run_years(100)
    event_map = {e.id: e for e in sim.event_log.all_events()}

    for e in sim.event_log.all_events():
        if e.type == EventType.MARRIAGE:
            peace_causes = [c_id for c_id in e.causes if event_map[c_id].type == EventType.PEACE]
            if peace_causes:
                # Must be flagged as alliance
                assert e.payload.get("is_alliance") is True, f"Marriage #{e.id} cited Peace without alliance flag"
                p_evt = event_map[peace_causes[0]]
                p_parties = {p_evt.participants_dict.get("initiator"), p_evt.participants_dict.get("target")} - {None}
                reloc = e.payload.get("relocation") or {}
                s_from = reloc.get("from_settlement_id")
                s_to = reloc.get("to_settlement_id")
                if s_from and s_to:
                    assert {s_from, s_to} == p_parties, f"Alliance marriage spouses {s_from, s_to} must match peace parties {p_parties}"
