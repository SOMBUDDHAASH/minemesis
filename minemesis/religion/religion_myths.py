"""
Myth Creation and Distorted Historical Memory Engine (Milestone R1.7).

Operationalizes religious myth-making:
Event -> Story -> Legend -> Myth

The Event Log remains the bedrock of objective reality.
The Religion Engine maintains the subjective, aggrandized theological memory:
- Reality: "Warrior died defending a bridge from a raider."
- Story (0-10 years): "Fell bravely holding the crossing for the village."
- Legend (10-40 years): "Held the bridge against a horde of twenty raiders, illuminated by divine aura."
- Myth (40+ years): "Crossed the river of fire on a chariot of thunder, shattering the mountains to seal the abyss forever."
"""

from __future__ import annotations
import random
from typing import Any, Mapping, Optional, Sequence
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
    }

    return myth, event_payload


def retell_and_evolve_myths(
    religion: Religion,
    current_tick: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """
    Simulates the generational retelling and mythic distortion of sacred tales:
    Story -> Legend -> Myth.
    """
    emitted_records: list[dict[str, Any]] = []

    for myth in religion.myths:
        elapsed_ticks = current_tick - myth.origin_tick
        myth.retellings += 1
        myth.last_retold_tick = current_tick

        stage_changed = False
        new_embellishment = None

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
