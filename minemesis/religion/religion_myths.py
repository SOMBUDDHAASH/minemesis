"""
Myth Creation, Trade Exchange & Cultural Memory System (Milestone R1.7, R1.5.7 & R2.5).

Operationalizes:
1. Generational Memory Distortion: Event -> Story -> Legend -> Myth -> Tradition -> Culture.
2. R1.5.7 Myth Exchange: Trade routes and pilgrimages carry stories into foreign settlements.
3. R2.5 Stories Create Culture: Ancient myths become foundational cultural traditions.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.core.event_log import Event
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    LoreStage,
    Religion,
    ReligiousMyth,
)


LEGEND_EMBELLISHMENTS = [
    "struck down three assailants with bare hands",
    "a blinding white light descended from the heavens upon the fallen hero",
    "the earth groaned and the forest trees bowed in solemn reverence",
    "spoke words of sacred prophecy with their dying breath",
    "the waters of the river parted as the brave stood ground",
]

MYTH_SUPERNATURAL_TRANSFORMATIONS = [
    "crossed the river of living fire unharmed to deliver the faithful",
    "transformed into the guiding star that watches eternally over the settlement",
    "commanded the thunder to strike down a legion of shadow beasts",
    "ascended upon pillars of celestial smoke into the council of the eternal gods",
    "split the sacred mountain in twain to shield the village from eternal ruin",
]

TRADITION_CELEBRATION_FORMS = [
    "honored each winter with solemn torches and song",
    "commemorated by pouring spring river libations upon the ancestral stones",
    "recited as the foundation story before every village council",
    "woven into sacred tapestries displayed during harvest festivals",
]


def create_initial_story_from_event(
    religion: Religion,
    event: Event,
    hero: Character,
    objective_summary: str,
    tick: int,
    myth_counter: list[int],
) -> tuple[ReligiousMyth, dict[str, Any]]:
    """
    Seeds a new historical story in religious memory from an objective Event.
    Initial stage: STORY.
    """
    m_idx = myth_counter[0]
    myth_counter[0] += 1
    myth_id = f"myth_{m_idx}"

    initial_narrative = (
        f"In the days of old at tick {tick}, {hero.name} stood as a champion of {religion.name}. "
        f"{objective_summary}"
    )

    myth = ReligiousMyth(
        myth_id=myth_id,
        religion_id=religion.id,
        root_event_id=event.id,
        hero_id=hero.id,
        hero_name=hero.name,
        stage=LoreStage.STORY,
        objective_truth=objective_summary,
        mythic_narrative=initial_narrative,
        embellishments=["Heroic stand witnessed by the faithful"],
        retellings=1,
        origin_tick=tick,
        last_retold_tick=tick,
        origin_settlement_id=hero.settlement_id,
        known_by_settlements={hero.settlement_id},
    )
    religion.myths.append(myth)

    event_payload = {
        "myth_id": myth.myth_id,
        "religion_id": religion.id,
        "religion_name": religion.name,
        "root_event_id": event.id,
        "hero_id": hero.id,
        "hero_name": hero.name,
        "stage": myth.stage.value,
        "narrative": myth.mythic_narrative,
        "objective_truth": myth.objective_truth,
        "origin_settlement_id": hero.settlement_id,
    }

    return myth, event_payload


def retell_and_evolve_myths(
    religion: Religion,
    current_tick: int,
    rng: KeyedRNG,
) -> list[dict[str, Any]]:
    """
    Simulates the generational evolution of stories across deep time:
    Event -> Story -> Legend -> Myth -> Tradition -> Culture.
    """
    emitted_records: list[dict[str, Any]] = []

    for myth in religion.myths:
        elapsed_ticks = current_tick - myth.origin_tick
        myth.retellings += 1
        myth.last_retold_tick = current_tick

        stage_changed = False

        if myth.stage == LoreStage.STORY and elapsed_ticks >= 120:  # ~10 years
            myth.stage = LoreStage.LEGEND
            new_embellishment = rng.choice(LEGEND_EMBELLISHMENTS)
            myth.embellishments.append(new_embellishment)
            myth.mythic_narrative = (
                f"The Legend of {myth.hero_name}: It is recounted in {religion.name} that during the Great Ordeal, "
                f"{myth.hero_name} {new_embellishment}, forever etching their deed in glory."
            )
            stage_changed = True

        elif myth.stage == LoreStage.LEGEND and elapsed_ticks >= 480:  # ~40 years
            myth.stage = LoreStage.MYTH
            new_embellishment = rng.choice(MYTH_SUPERNATURAL_TRANSFORMATIONS)
            myth.embellishments.append(new_embellishment)
            myth.mythic_narrative = (
                f"The Sacred Myth of {myth.hero_name}: Before the dawn of the current age, {myth.hero_name} "
                f"{new_embellishment}. Truly, the heavens revealed their omnipotence through the sacred vessel."
            )
            stage_changed = True

        elif myth.stage == LoreStage.MYTH and elapsed_ticks >= 720:  # ~60 years -> TRADITION
            myth.stage = LoreStage.TRADITION
            trad_desc = rng.choice(TRADITION_CELEBRATION_FORMS)
            tradition_entry = f"Tradition of {myth.hero_name}: {trad_desc}"
            if tradition_entry not in religion.cultural_traditions:
                religion.cultural_traditions.append(tradition_entry)
            myth.embellishments.append(trad_desc)
            myth.mythic_narrative = (
                f"The Living Tradition of {myth.hero_name}: The sacred deeds of {myth.hero_name} are now {trad_desc}."
            )
            stage_changed = True

        elif myth.stage == LoreStage.TRADITION and elapsed_ticks >= 1080:  # ~90 years -> CULTURE
            myth.stage = LoreStage.CULTURE
            myth.mythic_narrative = (
                f"Foundational Culture of {myth.hero_name}: The tale has transcended doctrine to become "
                f"inseparable from the spirit and identity of the civilization itself."
            )
            stage_changed = True

        if stage_changed:
            emitted_records.append({
                "myth_id": myth.myth_id,
                "religion_id": religion.id,
                "religion_name": religion.name,
                "root_event_id": myth.root_event_id,
                "hero_name": myth.hero_name,
                "new_stage": myth.stage.value,
                "narrative": myth.mythic_narrative,
                "objective_truth": myth.objective_truth,
                "retellings": myth.retellings,
            })

    return emitted_records


def exchange_myths_across_trade_routes(
    active_trade_routes: Any,
    religions: Mapping[str, Religion],
    dominant_by_settlement: Mapping[str, str],
    current_tick: int,
    rng: KeyedRNG,
    myth_counter: list[int],
) -> list[dict[str, Any]]:
    """
    R1.5.7: Trade routes and travellers spread sacred stories and foreign legends.
    """
    exchanges: list[dict[str, Any]] = []
    if not active_trade_routes:
        return exchanges

    for (s_a, s_b), route in active_trade_routes.items():
        is_route_active = getattr(route, "active", getattr(route, "is_active", True))
        if is_route_active:
            rel_a_id = dominant_by_settlement.get(s_a)
            rel_b_id = dominant_by_settlement.get(s_b)
            if rel_a_id and rel_b_id and rel_a_id in religions and rel_b_id in religions:
                rel_a = religions[rel_a_id]
                rel_b = religions[rel_b_id]

                # Find a myth in rel_a not yet known in s_b
                foreign_myths = [
                    m for m in rel_a.myths
                    if s_b not in m.known_by_settlements
                ]
                if foreign_myths and rng.random() < 0.20:
                    chosen_myth = rng.choice(foreign_myths)
                    chosen_myth.known_by_settlements.add(s_b)

                    # Adapt a syncretic version for rel_b if not already present
                    adapted_myth_id = f"myth_{myth_counter[0]}"
                    myth_counter[0] += 1
                    adapted_narrative = (
                        f"A tale brought by caravans from {s_a}: It is told that {chosen_myth.hero_name} "
                        f"performed great deeds under foreign skies, acknowledged by {rel_b.name}."
                    )
                    adapted_myth = ReligiousMyth(
                        myth_id=adapted_myth_id,
                        religion_id=rel_b.id,
                        root_event_id=chosen_myth.root_event_id,
                        hero_id=chosen_myth.hero_id,
                        hero_name=chosen_myth.hero_name,
                        stage=LoreStage.STORY,
                        objective_truth=chosen_myth.objective_truth,
                        mythic_narrative=adapted_narrative,
                        embellishments=["Brought by trade caravans"],
                        retellings=1,
                        origin_tick=current_tick,
                        last_retold_tick=current_tick,
                        origin_settlement_id=s_a,
                        known_by_settlements={s_a, s_b},
                    )
                    rel_b.myths.append(adapted_myth)

                    exchanges.append({
                        "origin_settlement": s_a,
                        "destination_settlement": s_b,
                        "origin_religion": rel_a.name,
                        "adopting_religion": rel_b.name,
                        "hero_name": chosen_myth.hero_name,
                        "root_event_id": chosen_myth.root_event_id,
                        "tick": current_tick,
                    })

    return exchanges
