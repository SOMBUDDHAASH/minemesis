"""
Great Religious Figures System (Milestone R1.4).

Models prominent religious archetypes beyond merely canonized saints:
- Prophets: Charismatic figures receiving divine revelation, sparking mass devotion or sects.
- Saints: Posthumously canonized champions of faith, piety, and virtue.
- Mystics: Hermits and seers who perceive sacred geometry and discover holy sites.
- Martyrs: Faithful slain during raids or persecutions; their memory ignites holy vengeance.
- Reformers: Internal critics striving to purge corruption and purify doctrine.
- Heretics: Dissident thinkers whose heterodoxy threatens the orthodox fold.
"""

from __future__ import annotations
import random
from typing import Mapping, Optional, Sequence
from minemesis.core.types import EventType, Intent
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    CharacterFaith,
    HeroArchetype,
    Religion,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousRole,
    Saint,
)


def determine_hero_archetype(
    religion: Optional[Religion],
    character: Character,
    figure_type: ReligiousFigureType,
) -> HeroArchetype:
    """
    R2.6: Maps historical veneration according to tradition:
    - Ancestor traditions -> Ancestor / Protective Spirit
    - Animist traditions -> Protective Spirit
    - Martial / Warrior traditions -> Hero / Cultural Icon
    - Priesthood / Institutional -> Saint
    """
    if religion:
        traits = set(religion.traits.keys())
        if "ancestor_worship" in traits or "ancestral_veneration" in traits:
            return HeroArchetype.ANCESTOR
        if "animism_cosmology" in traits:
            return HeroArchetype.PROTECTIVE_SPIRIT
        if "warrior_tradition" in traits or "warrior_honor" in traits:
            return HeroArchetype.HERO
        if "hierarchical_priesthood" in traits:
            return HeroArchetype.SAINT

    if character.age_ticks > 600:
        return HeroArchetype.CULTURAL_ICON
    return HeroArchetype.HERO


def create_religious_figure(
    figure_id: str,
    character: Character,
    faith: CharacterFaith,
    religion: Religion,
    figure_type: ReligiousFigureType,
    title: str,
    deed: str,
    tick: int,
    associated_event_id: Optional[int] = None,
) -> ReligiousFigure:
    """Instantiates and registers a new Great Religious Figure within a religion."""
    archetype = determine_hero_archetype(religion, character, figure_type)
    fig = ReligiousFigure(
        id=figure_id,
        character_id=character.id,
        character_name=character.name,
        figure_type=figure_type,
        religion_id=religion.id,
        title=title,
        deeds=[deed],
        tick_recognized=tick,
        is_alive=character.alive,
        associated_event_id=associated_event_id,
        archetype=archetype,
    )
    religion.figures.append(fig)

    # If the figure is a prophet or reformer, elevate their religious role
    if figure_type == ReligiousFigureType.PROPHET:
        faith.role = ReligiousRole.PROPHET
        faith.is_zealot = True
        faith.devotion = min(1.0, faith.devotion + 0.2)
    elif figure_type == ReligiousFigureType.MYSTIC:
        faith.role = ReligiousRole.ORACLE
        faith.devotion = min(1.0, faith.devotion + 0.15)
    elif figure_type == ReligiousFigureType.REFORMER:
        faith.role = ReligiousRole.ELDER
        faith.devotion = min(1.0, faith.devotion + 0.15)

    return fig


def evaluate_martyrdom(
    deceased_char: Character,
    deceased_faith: CharacterFaith,
    religion: Religion,
    cause_type: EventType,
    death_event_id: int,
    tick: int,
    figure_counter: list[int],
) -> Optional[ReligiousFigure]:
    """
    Checks if a deceased character qualifies as a Martyr.
    Requires death via Raid or Feud and high devotion / clerical standing.
    """
    if cause_type not in (EventType.RAID, EventType.FEUD, EventType.DEATH):
        return None

    # Martyrdom criteria: high devotion or defender of the faith
    if deceased_faith.devotion >= 0.75 or deceased_faith.role in (ReligiousRole.PRIEST, ReligiousRole.SHAMAN, ReligiousRole.ZEALOT):
        f_num = figure_counter[0]
        figure_counter[0] += 1
        fig_id = f"fig_{f_num}"
        title = f"Martyr of {religion.name}"
        deed = f"Slain while holding fast to the sacred tenets during the {cause_type.value} at tick {tick}."

        archetype = determine_hero_archetype(religion, deceased_char, ReligiousFigureType.MARTYR)
        fig = ReligiousFigure(
            id=fig_id,
            character_id=deceased_char.id,
            character_name=deceased_char.name,
            figure_type=ReligiousFigureType.MARTYR,
            religion_id=religion.id,
            title=title,
            deeds=[deed],
            tick_recognized=tick,
            is_alive=False,
            associated_event_id=death_event_id,
            archetype=archetype,
        )
        religion.figures.append(fig)

        # Also register as a posthumous Saint
        saint = Saint(
            character_id=deceased_char.id,
            character_name=deceased_char.name,
            title=title,
            canonized_tick=tick,
            deed=deed,
            archetype=archetype,
        )
        religion.saints.append(saint)
        return fig

    return None


def evaluate_prophet_or_mystic_emergence(
    candidates: Sequence[Character],
    faiths: Mapping[str, CharacterFaith],
    religion: Religion,
    trigger_event_id: Optional[int],
    tick: int,
    rng: random.Random,
    figure_counter: list[int],
) -> Optional[ReligiousFigure]:
    """
    Evaluates whether a devout adherent experiences prophetic revelation or mystical awakening.
    Often triggered after the death of a founder/chief or severe trial.
    """
    living_devout = [
        c for c in candidates
        if c.alive and c.id in faiths and faiths[c.id].religion_id == religion.id and faiths[c.id].devotion >= 0.80
    ]
    if not living_devout:
        return None

    # Sort deterministically
    living_devout.sort(key=lambda c: (-faiths[c.id].devotion, c.id))
    chosen_char = living_devout[0]
    c_faith = faiths[chosen_char.id]

    roll = rng.random()
    f_num = figure_counter[0]
    figure_counter[0] += 1
    fig_id = f"fig_{f_num}"

    if roll < 0.60:
        # Prophet Emergence
        title = f"The Voice of {religion.name}"
        deed = f"Proclaimed divine revelation and gathered the faithful in renewal at tick {tick}."
        fig = create_religious_figure(
            figure_id=fig_id,
            character=chosen_char,
            faith=c_faith,
            religion=religion,
            figure_type=ReligiousFigureType.PROPHET,
            title=title,
            deed=deed,
            tick=tick,
            associated_event_id=trigger_event_id,
        )
        return fig
    else:
        # Mystic Emergence
        title = f"The Seer of Sacred Visions"
        deed = f"Entered deep communion with the unseen spiritual realm at tick {tick}."
        fig = create_religious_figure(
            figure_id=fig_id,
            character=chosen_char,
            faith=c_faith,
            religion=religion,
            figure_type=ReligiousFigureType.MYSTIC,
            title=title,
            deed=deed,
            tick=tick,
            associated_event_id=trigger_event_id,
        )
        return fig
