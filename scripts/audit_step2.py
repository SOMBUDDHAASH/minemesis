"""
Audit script for Step 2 of Milestone 0.5.1:
2a. Marriage/Peace causality audit
2c. Revenge funnel audit
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from minemesis.core.rng import keyed_float
from minemesis.core.types import EventType, Intent
from minemesis.systems.simulation import Simulation


def main() -> None:
    seeds = [42 + i * 17 for i in range(50)]

    print(f"Auditing Step 2 across 50 training seeds...")

    # -------------------------------------------------------------
    # Audit 2a: Marriage/Peace Causality
    # -------------------------------------------------------------
    total_marriages = 0
    marriages_citing_peace = 0
    genuine_peace_marriages = 0
    birth_tails_from_peace_marriages = 0

    # -------------------------------------------------------------
    # Audit 2c: Revenge Funnel
    # -------------------------------------------------------------
    # We will track every feud-month evaluated in Section 5 of conflict.py
    funnel = {
        "feud_months_evaluated": 0,
        "instigator_or_target_dead": 0,
        "blocked_by_per_feud_cap": 0,
        "blocked_by_cooldown": 0,
        "blocked_by_target_crit_pop": 0,
        "blocked_by_hatred_threshold": 0,
        "blocked_by_forgiveness_trait": 0,
        "blocked_by_opportunity_roll": 0,
        "executed_revenge": 0,
    }

    for seed in seeds:
        sim = Simulation(seed)
        # We step month by month to instrument revenge funnel accurately
        for tick in range(1200):
            # Check revenge state before step
            for feud in sim.active_feuds:
                if not feud.active:
                    continue
                funnel["feud_months_evaluated"] += 1

                if feud.revenge_count >= 1:
                    funnel["blocked_by_per_feud_cap"] += 1
                    continue

                elapsed = tick - feud.start_tick
                if elapsed < 18 or (tick - feud.last_revenge_tick) < 36:
                    funnel["blocked_by_cooldown"] += 1
                    continue

                instigator = sim.characters.get(feud.instigator_char_id)
                target = sim.characters.get(feud.target_char_id)

                if not instigator or not instigator.alive or not target or not target.alive:
                    funnel["instigator_or_target_dead"] += 1
                    continue

                target_set_living = [c for c in sim.living_characters if c.settlement_id == target.settlement_id]
                if len(target_set_living) <= 3:
                    funnel["blocked_by_target_crit_pop"] += 1
                    continue

                rel = sim.get_relationship(instigator.id, target.id)
                if rel.hatred < 70.0:
                    funnel["blocked_by_hatred_threshold"] += 1
                    continue

                if instigator.forgiveness >= 0.50:
                    funnel["blocked_by_forgiveness_trait"] += 1
                    continue

                revenge_chance = 0.04 * (1.1 - instigator.forgiveness)
                roll = keyed_float(seed, "revenge_kill", str(feud.id), tick)
                if roll >= revenge_chance:
                    funnel["blocked_by_opportunity_roll"] += 1
                    continue

                funnel["executed_revenge"] += 1

            sim.step_month()

        # Audit 2a on the completed simulation log
        events = sim.event_log.all_events()
        event_map = {e.id: e for e in events}

        # Find all marriages citing Peace
        peace_marriage_ids = set()
        for e in events:
            if e.type == EventType.MARRIAGE:
                total_marriages += 1
                peace_causes = [c_id for c_id in e.causes if event_map[c_id].type == EventType.PEACE]
                if peace_causes:
                    marriages_citing_peace += 1
                    peace_evt = event_map[peace_causes[0]]
                    p_initiator = peace_evt.participants_dict.get("initiator")
                    p_target = peace_evt.participants_dict.get("target")
                    p_parties = {p_initiator, p_target} - {None}

                    # Spouses original settlements
                    s1 = sim.characters[e.participants_dict["spouse1"]].settlement_id
                    s2 = sim.characters[e.participants_dict["spouse2"]].settlement_id
                    spouse_sets = {s1, s2}

                    is_alliance = e.payload.get("is_alliance") is True
                    # Check if spouses come from the two settlements that were parties to that peace
                    is_genuine_settlement_pair = (len(p_parties) == 2 and p_parties == spouse_sets)

                    if is_alliance or is_genuine_settlement_pair:
                        genuine_peace_marriages += 1
                    else:
                        peace_marriage_ids.add(e.id)

        # Count Birth tails that trace back to these recency-based peace marriages
        for e in events:
            if e.type == EventType.BIRTH:
                # trace causes back
                queue = list(e.causes)
                visited = set(queue)
                traced_to_peace_marriage = False
                while queue:
                    curr = queue.pop(0)
                    if curr in peace_marriage_ids:
                        traced_to_peace_marriage = True
                        break
                    if curr in event_map:
                        for parent_cause in event_map[curr].causes:
                            if parent_cause not in visited:
                                visited.add(parent_cause)
                                queue.append(parent_cause)
                if traced_to_peace_marriage:
                    birth_tails_from_peace_marriages += 1

    print("\n=== AUDIT 2a: Marriage/Peace Causality ===")
    print(f"Total Marriages: {total_marriages}")
    print(f"Marriages Citing Peace: {marriages_citing_peace} ({marriages_citing_peace / total_marriages:.1%})")
    print(f"Genuine Peace/Alliance Marriages: {genuine_peace_marriages} ({genuine_peace_marriages / max(1, marriages_citing_peace):.1%})")
    print(f"Spurious / Recency-based Peace Marriages: {marriages_citing_peace - genuine_peace_marriages}")
    print(f"Birth Tails Descended from Spurious Peace Marriages: {birth_tails_from_peace_marriages}")

    print("\n=== AUDIT 2c: Revenge Funnel ===")
    for k, v in funnel.items():
        print(f"  {k:30s}: {v}")


if __name__ == "__main__":
    main()
