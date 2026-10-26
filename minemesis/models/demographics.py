"""
Demographic Cohort & Population Layering System (Milestone 4).

Allows settlements to simulate realistic populations of thousands of villagers
at near-zero RAM overhead by maintaining aggregate demographic cohorts
(settlement, age_bracket, sex, profession) and deterministically materializing
and promoting individuals only when they become historically notable.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.rng import keyed_choice, keyed_float, keyed_hash_int, keyed_int
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.systems.cast_gen import (
    GIVEN_NAMES_FEMALE,
    GIVEN_NAMES_MALE,
    SURNAME_PREFIXES,
    SURNAME_SUFFIXES,
)


AGE_BRACKETS = ("child", "young_adult", "adult", "elder")


@dataclass
class DemographicCohort:
    settlement_id: str
    age_bracket: str  # "child", "young_adult", "adult", "elder"
    sex: str          # "M" or "F"
    profession: str   # "Farmer", "Laborer", "Craftsman", "Hunter", "Herder"
    count: int = 0


class DemographicRegistry:
    """
    Manages background population cohorts for all settlements.
    Supports deterministic promotion of ordinary citizens into full Character instances.
    """

    def __init__(self, world_seed: int = 42, history_seed: int = 1337) -> None:
        self.world_seed = world_seed
        self.history_seed = history_seed
        # Key: (settlement_id, age_bracket, sex, profession) -> DemographicCohort
        self.cohorts: dict[tuple[str, str, str, str], DemographicCohort] = {}
        self._promoted_counter = 0

    def add_population(
        self,
        settlement_id: str,
        age_bracket: str,
        sex: str,
        count: int = 1,
        profession: str = "Laborer",
    ) -> None:
        if count <= 0:
            return
        key = (settlement_id, age_bracket, sex, profession)
        if key not in self.cohorts:
            self.cohorts[key] = DemographicCohort(
                settlement_id=settlement_id,
                age_bracket=age_bracket,
                sex=sex,
                profession=profession,
                count=0,
            )
        self.cohorts[key].count += count

    def remove_population(
        self,
        settlement_id: str,
        age_bracket: str,
        sex: str,
        count: int = 1,
        profession: Optional[str] = None,
    ) -> int:
        """Removes up to count from matching cohorts. Returns actual number removed."""
        if count <= 0:
            return 0
        removed = 0
        for (s_id, b, sx, prof), cohort in list(self.cohorts.items()):
            if s_id == settlement_id and b == age_bracket and sx == sex:
                if profession is None or prof == profession:
                    avail = cohort.count
                    take = min(count - removed, avail)
                    cohort.count -= take
                    removed += take
                    if removed >= count:
                        break
        return removed

    def get_settlement_population(self, settlement_id: str) -> int:
        """Returns total background cohort population residing in a settlement."""
        return sum(
            c.count for (s_id, _, _, _), c in self.cohorts.items()
            if s_id == settlement_id
        )

    def get_total_population(self) -> int:
        """Returns total background cohort population across the entire world."""
        return sum(c.count for c in self.cohorts.values())

    def get_cohort_count(
        self,
        settlement_id: str,
        age_bracket: Optional[str] = None,
        sex: Optional[str] = None,
    ) -> int:
        total = 0
        for (s_id, b, sx, _), cohort in self.cohorts.items():
            if s_id == settlement_id:
                if age_bracket is not None and b != age_bracket:
                    continue
                if sex is not None and sx != sex:
                    continue
                total += cohort.count
        return total

    def promote_citizen(
        self,
        settlement_id: str,
        age_bracket: str = "adult",
        sex: Optional[str] = None,
        profession: Optional[str] = None,
        reason: str = "notable_action",
        tick: int = 0,
        char_counter: Optional[list[int]] = None,
        existing_surnames: Sequence[str] = (),
        name_salt: int = 0,
    ) -> Optional[Character]:
        """
        Promotes an ordinary background citizen to a full Character entity.
        Decrements the background cohort tally and deterministically generates identity.
        """
        # Choose sex if not provided
        if sex is None:
            m_count = self.get_cohort_count(settlement_id, age_bracket, "M")
            f_count = self.get_cohort_count(settlement_id, age_bracket, "F")
            if m_count >= f_count and m_count > 0:
                sex = "M"
            elif f_count > 0:
                sex = "F"
            else:
                sex = "M"

        # Check if cohort has members to promote
        removed = self.remove_population(settlement_id, age_bracket, sex, count=1, profession=profession)
        if removed == 0:
            # Fallback to any age bracket if requested bracket is empty
            for fallback_b in ("young_adult", "adult", "child", "elder"):
                removed = self.remove_population(settlement_id, fallback_b, sex, count=1)
                if removed > 0:
                    age_bracket = fallback_b
                    break

        self._promoted_counter += 1
        if char_counter is not None:
            cid = f"char_{char_counter[0]}"
            char_counter[0] += 1
        else:
            cid = f"prom_{settlement_id}_{self._promoted_counter}"

        # Deterministic identity generation
        salt_key = f"{self.history_seed}_{settlement_id}_{self._promoted_counter}_{name_salt}"
        if sex == "M":
            first_name = keyed_choice(self.history_seed, "prom_fn", salt_key, tick, GIVEN_NAMES_MALE)
        else:
            first_name = keyed_choice(self.history_seed, "prom_fn", salt_key, tick, GIVEN_NAMES_FEMALE)

        if existing_surnames:
            last_name = keyed_choice(self.history_seed, "prom_ln", salt_key, tick, list(existing_surnames))
        else:
            pfx = keyed_choice(self.history_seed, "prom_pfx", salt_key, tick, SURNAME_PREFIXES)
            sfx = keyed_choice(self.history_seed, "prom_sfx", salt_key, tick, SURNAME_SUFFIXES)
            last_name = f"{pfx}{sfx}"

        # Age in ticks according to bracket
        if age_bracket == "child":
            age_years = 5 + (keyed_hash_int(self.history_seed, "p_age", salt_key) % 11)
        elif age_bracket == "young_adult":
            age_years = 16 + (keyed_hash_int(self.history_seed, "p_age", salt_key) % 15)
        elif age_bracket == "adult":
            age_years = 31 + (keyed_hash_int(self.history_seed, "p_age", salt_key) % 20)
        else:  # elder
            age_years = 51 + (keyed_hash_int(self.history_seed, "p_age", salt_key) % 25)

        age_ticks = age_years * 12 + (keyed_hash_int(self.history_seed, "p_m", salt_key) % 12)

        susp = 0.20 + 0.60 * keyed_float(self.history_seed, "p_susp", salt_key, tick)
        forg = 0.20 + 0.60 * keyed_float(self.history_seed, "p_forg", salt_key, tick)
        prof = profession or keyed_choice(
            self.history_seed,
            "p_prof",
            salt_key,
            tick,
            ["Farmer", "Laborer", "Craftsman", "Hunter", "Herder"],
        )

        char = Character(
            id=cid,
            first_name=first_name,
            last_name=last_name,
            settlement_id=settlement_id,
            age_ticks=age_ticks,
            sex=sex,
            alive=True,
            suspicion=round(susp, 2),
            forgiveness=round(forg, 2),
            profession=prof,
            family_id=last_name,
            name_ordinal=1,
            display_name=f"{first_name} {last_name}",
        )
        return char

    def step_demographics(
        self,
        settlements: Mapping[str, Settlement],
        living_promoted_by_settlement: Mapping[str, int],
        tick: int,
        seed: int,
    ) -> None:
        """
        Simulates background demographic flows per settlement:
        - Monthly aging transitions
        - Background births
        - Background mortality
        - Famine starvation when food is deficit
        """
        month = tick % 12

        for s_id, s in settlements.items():
            prom_count = living_promoted_by_settlement.get(s_id, 0)
            bg_pop = self.get_settlement_population(s_id)
            total_pop = prom_count + bg_pop
            if total_pop <= 0:
                continue

            # Carrying capacity & Food check
            k_settlement = max(50, int(130 * s.farmland * (s.water_access + 0.5)))
            is_famine = (s.food < 10)
            overcrowded = (total_pop > k_settlement)

            # 1. Background Mortality
            # Elders face monthly natural mortality (~0.8%)
            elders = self.get_cohort_count(s_id, "elder")
            if elders > 0:
                elder_deaths = int(elders * 0.008)
                if elder_deaths > 0:
                    self.remove_population(s_id, "elder", "M", elder_deaths // 2)
                    self.remove_population(s_id, "elder", "F", (elder_deaths + 1) // 2)

            # Famine mortality
            if is_famine and bg_pop > 10:
                famine_deaths = max(1, int(bg_pop * 0.02))
                self.remove_population(s_id, "child", "M", famine_deaths // 4)
                self.remove_population(s_id, "child", "F", famine_deaths // 4)
                self.remove_population(s_id, "elder", "M", famine_deaths // 4)
                self.remove_population(s_id, "elder", "F", famine_deaths // 4)

            # 2. Background Births (Spring/Summer boost, suppressed in famine or overcrowding)
            adults_f = self.get_cohort_count(s_id, "adult", "F") + self.get_cohort_count(s_id, "young_adult", "F")
            if adults_f > 0 and not is_famine:
                birth_rate = 0.012 if not overcrowded else 0.004
                if month in (3, 4, 5, 6):
                    birth_rate *= 1.3
                expected_births = int(adults_f * birth_rate)
                if expected_births > 0:
                    m_births = expected_births // 2
                    f_births = expected_births - m_births
                    self.add_population(s_id, "child", "M", m_births, profession="Child")
                    self.add_population(s_id, "child", "F", f_births, profession="Child")

            # 3. Yearly Aging Transitions (once a year in month 0)
            if month == 0:
                # 1/15th of children become young adults
                c_m = self.get_cohort_count(s_id, "child", "M")
                c_f = self.get_cohort_count(s_id, "child", "F")
                trans_c_m = max(1, c_m // 15) if c_m >= 15 else (1 if c_m > 0 and keyed_float(seed, "age_cm", s_id, tick) < 0.2 else 0)
                trans_c_f = max(1, c_f // 15) if c_f >= 15 else (1 if c_f > 0 and keyed_float(seed, "age_cf", s_id, tick) < 0.2 else 0)
                if trans_c_m > 0:
                    self.remove_population(s_id, "child", "M", trans_c_m)
                    self.add_population(s_id, "young_adult", "M", trans_c_m, profession="Laborer")
                if trans_c_f > 0:
                    self.remove_population(s_id, "child", "F", trans_c_f)
                    self.add_population(s_id, "young_adult", "F", trans_c_f, profession="Laborer")

                # 1/15th of young adults become adults
                ya_m = self.get_cohort_count(s_id, "young_adult", "M")
                ya_f = self.get_cohort_count(s_id, "young_adult", "F")
                trans_ya_m = max(1, ya_m // 15) if ya_m >= 15 else 0
                trans_ya_f = max(1, ya_f // 15) if ya_f >= 15 else 0
                if trans_ya_m > 0:
                    self.remove_population(s_id, "young_adult", "M", trans_ya_m)
                    self.add_population(s_id, "adult", "M", trans_ya_m, profession="Farmer")
                if trans_ya_f > 0:
                    self.remove_population(s_id, "young_adult", "F", trans_ya_f)
                    self.add_population(s_id, "adult", "F", trans_ya_f, profession="Farmer")

                # 1/20th of adults become elders
                ad_m = self.get_cohort_count(s_id, "adult", "M")
                ad_f = self.get_cohort_count(s_id, "adult", "F")
                trans_ad_m = max(1, ad_m // 20) if ad_m >= 20 else 0
                trans_ad_f = max(1, ad_f // 20) if ad_f >= 20 else 0
                if trans_ad_m > 0:
                    self.remove_population(s_id, "adult", "M", trans_ad_m)
                    self.add_population(s_id, "elder", "M", trans_ad_m, profession="Elder")
                if trans_ad_f > 0:
                    self.remove_population(s_id, "adult", "F", trans_ad_f)
                    self.add_population(s_id, "elder", "F", trans_ad_f, profession="Elder")
