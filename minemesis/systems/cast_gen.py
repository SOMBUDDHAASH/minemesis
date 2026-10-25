"""
Procedural Cast Generator for Minemesis.

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).

Rules:
- Governed by ChronicleSeed + WorldSpec (never draws from world seed).
- Generates 18 to 40 characters per settlement scaled by farmland endowment.
- Surnames generated from syllable tables with >= 6 distinct families per settlement.
- Generation-time guarantees:
  * At least 4 fertile couples per settlement.
  * No kin couples (spouses do not share parents or surname).
  * Unique IDs and unique full names within each settlement.
  * Documented stable sorted order for character IDs.
- Zero hard-coded rosters in code.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

from minemesis.core.rng import keyed_hash_int, keyed_int, keyed_float, keyed_choice
from minemesis.models.character import Character
from minemesis.systems.world_spec import WorldSpec, SettlementSite


GIVEN_NAMES_MALE = [
    "Arthur", "Rowan", "Caleb", "Gideon", "Tobias", "Bram", "Cedric", "Aldous",
    "Gareth", "Eldrin", "Silas", "Corin", "Lucan", "Orson", "Theron", "Vance",
    "Benedict", "Casper", "Dorian", "Evander", "Finnian", "Gregor", "Halden", "Isaac",
    "Jonas", "Kellan", "Leander", "Merrick", "Niall", "Osric", "Perrin", "Quinn",
    "Roderick", "Soren", "Tristan", "Ulric", "Valen", "Wilhelm", "Yorick", "Zane",
    "Ansel", "Bastian", "Colm", "Declan", "Eamon", "Fenton", "Galen", "Hollis",
    "Idris", "Kael", "Lorcan", "Magnus", "Ned", "Oskar", "Pierce", "Ronan",
]

GIVEN_NAMES_FEMALE = [
    "Lyra", "Eleni", "Maeve", "Freya", "Astrid", "Briony", "Isolde", "Sylvia",
    "Kaelen", "Morwen", "Brenna", "Thalia", "Vesper", "Sari", "Daphne", "Elora",
    "Aislinn", "Beatrix", "Calla", "Danica", "Elowen", "Fiora", "Gisela", "Helena",
    "Ingrid", "Jocelyn", "Kira", "Linnea", "Maren", "Nadia", "Opal", "Petra",
    "Rhiannon", "Selene", "Tamsin", "Una", "Valeria", "Willa", "Yvaine", "Zara",
    "Althea", "Blythe", "Cora", "Dahlia", "Elspeth", "Faye", "Greta", "Hazel",
    "Iona", "Junia", "Kendra", "Livia", "Mira", "Nessa", "Oriana", "Priscilla",
]

SURNAME_PREFIXES = [
    "Iron", "Ash", "Black", "River", "Stone", "Crow", "Oak", "Thorn", "Winter",
    "Frost", "Falcon", "Hawk", "Wolf", "Vale", "Dale", "Wood", "Brook", "Hill",
    "Gold", "Silver", "Red", "Bright", "Swift", "Strong", "Long", "Hart", "Fox",
    "Bramble", "Alder", "Birch", "Raven", "Shield", "Spear", "Bow", "Heath", "Moor",
]

SURNAME_SUFFIXES = [
    "wood", "ford", "well", "man", "field", "croft", "ley", "ton", "berg",
    "smith", "son", "wick", "thorne", "ridge", "stone", "water", "brook", "hurst",
    "worth", "gate", "bridge", "hall", "stead", "land", "dale", "beck", "low",
]


class CastGenerator:
    """
    Generates realistic, varied, biologically sound starting populations for all settlements.
    Names are drawn strictly from an isolated 'name:' domain so name variations never disrupt
    event rolls, character traits, or historical causality.
    """
    def __init__(
        self,
        history_seed: Optional[int] = None,
        world_spec: Optional[WorldSpec] = None,
        *,
        chronicle_seed: Optional[int] = None,
        name_salt: int = 0,
    ):
        h = history_seed if history_seed is not None else chronicle_seed
        if h is None:
            raise ValueError("History seed must be provided to CastGenerator")
        if world_spec is None:
            raise ValueError("WorldSpec must be provided to CastGenerator")
        self.history_seed = h
        self.chronicle_seed = h  # backward-compatible alias
        self.world_spec = world_spec
        self.name_salt = name_salt

    def generate_cast(self) -> dict[str, Character]:
        """
        Generates characters for all settlements in the WorldSpec.
        Returns dictionary of Character objects keyed by stable sorted ID (char_0, char_1, ...).
        """
        all_unindexed_chars: list[dict] = []

        # Iterate over settlements in sorted ID order
        sorted_sites = sorted(self.world_spec.settlements, key=lambda s: s.id)

        for s_idx, site in enumerate(sorted_sites):
            site_chars = self._generate_settlement_cast(site, s_idx)
            all_unindexed_chars.extend(site_chars)

        # Assign final sequential IDs in deterministic order
        characters: dict[str, Character] = {}
        id_mapping: dict[str, str] = {}  # temp_id -> final char_N id

        for idx, c_dict in enumerate(all_unindexed_chars):
            final_id = f"char_{idx}"
            temp_id = c_dict["temp_id"]
            id_mapping[temp_id] = final_id

        # Second pass: construct immutable Character objects with remapped IDs
        for c_dict in all_unindexed_chars:
            final_id = id_mapping[c_dict["temp_id"]]
            spouse_id = id_mapping.get(c_dict["spouse_temp_id"]) if c_dict.get("spouse_temp_id") else None
            father_id = id_mapping.get(c_dict["father_temp_id"]) if c_dict.get("father_temp_id") else None
            mother_id = id_mapping.get(c_dict["mother_temp_id"]) if c_dict.get("mother_temp_id") else None
            children_ids = list(id_mapping[kid_t] for kid_t in c_dict.get("children_temp_ids", ()))

            char = Character(
                id=final_id,
                first_name=c_dict["first_name"],
                last_name=c_dict["last_name"],
                settlement_id=c_dict["settlement_id"],
                age_ticks=c_dict["age_ticks"],
                sex=c_dict["sex"],
                alive=True,
                spouse_id=spouse_id,
                father_id=father_id,
                mother_id=mother_id,
                children_ids=children_ids,
                suspicion=c_dict["suspicion"],
                forgiveness=c_dict["forgiveness"],
                profession=c_dict["profession"],
                family_id=c_dict.get("family_id", ""),
            )
            characters[final_id] = char

        return characters

    def _generate_settlement_cast(self, site: SettlementSite, site_index: int) -> list[dict]:
        """Generates realistic starting families for a single settlement site."""
        site_seed = keyed_hash_int(self.history_seed, "settlement_cast", site.id, site_index)

        # Scale population with farmland: 20 to 36 citizens
        pop_target = 20 + int(round((site.farmland - 0.60) * 11))
        pop_target = max(20, min(36, pop_target))

        # Generate exactly 8 distinct family surnames using isolated name domain
        NUM_FAMILIES = 8
        family_names: list[str] = []
        for slot in range(NUM_FAMILIES):
            sub = 0
            while True:
                pref = keyed_choice(site_seed, "name:fam_pref", slot, sub, SURNAME_PREFIXES, salt=self.name_salt)
                suff = keyed_choice(site_seed, "name:fam_suff", slot, sub, SURNAME_SUFFIXES, salt=self.name_salt)
                cand = f"{pref}{suff}"
                if cand not in family_names:
                    family_names.append(cand)
                    break
                sub += 1

        used_full_names: set[str] = set()
        male_names_used: set[str] = set()
        female_names_used: set[str] = set()

        def pick_first_name(sex: str, seed_tag: str) -> str:
            bank = GIVEN_NAMES_MALE if sex == "M" else GIVEN_NAMES_FEMALE
            used_pool = male_names_used if sex == "M" else female_names_used
            for k in range(len(bank)):
                name = keyed_choice(site_seed, f"name:first:{seed_tag}", k, 0, bank, salt=self.name_salt)
                if name not in used_pool:
                    used_pool.add(name)
                    return name
            # Reuse with numeral if bank exhausted
            name = bank[keyed_int(site_seed, f"name:first_reuse:{seed_tag}", 999, 0, 0, len(bank) - 1, salt=self.name_salt)]
            return name

        unindexed_chars: list[dict] = []
        temp_id_counter = 0

        # Guarantee at least 4 fertile couples (aged 22 to 42)
        # Surnames rotate among families to ensure non-kin marriages
        num_couples = 4 + (keyed_hash_int(site_seed, "num_couples", 0, 0) % 3)  # 4, 5, or 6
        num_couples = min(num_couples, len(family_names) - 1)

        for c_idx in range(num_couples):
            fam_id = f"fam_{site.id}_{c_idx}"
            fam_husband = family_names[c_idx]
            fam_wife = family_names[(c_idx + 1) % len(family_names)]

            # Husband
            h_temp = f"t_{site.id}_h_{c_idx}"
            h_name = pick_first_name("M", f"h_name_{c_idx}")
            h_age_years = keyed_int(site_seed, "h_age", c_idx, 0, 24, 40)
            used_full_names.add(f"{h_name} {fam_husband}")

            # Wife
            w_temp = f"t_{site.id}_w_{c_idx}"
            w_name = pick_first_name("F", f"w_name_{c_idx}")
            w_age_years = keyed_int(site_seed, "w_age", c_idx, 0, 22, 38)
            # Wife takes husband's surname upon marriage
            used_full_names.add(f"{w_name} {fam_husband}")

            # Generate 1 to 3 children
            kids_count = 1 + (keyed_hash_int(site_seed, "kids_count", c_idx, 0) % 3)
            kid_temps = []
            kid_dicts = []

            for k_idx in range(kids_count):
                k_temp = f"t_{site.id}_k_{c_idx}_{k_idx}"
                k_sex = "M" if (keyed_hash_int(site_seed, "k_sex", c_idx, k_idx) % 2 == 0) else "F"
                k_name = pick_first_name(k_sex, f"k_name_{c_idx}_{k_idx}")
                k_age_years = keyed_int(site_seed, "k_age", c_idx, k_idx, 1, 14)
                used_full_names.add(f"{k_name} {fam_husband}")

                kid_temps.append(k_temp)
                kid_dicts.append({
                    "temp_id": k_temp,
                    "first_name": k_name,
                    "last_name": fam_husband,
                    "family_id": fam_id,
                    "settlement_id": site.id,
                    "age_ticks": k_age_years * 12,
                    "sex": k_sex,
                    "spouse_temp_id": None,
                    "father_temp_id": h_temp,
                    "mother_temp_id": w_temp,
                    "children_temp_ids": (),
                    "suspicion": round(keyed_float(site_seed, "k_susp", c_idx, k_idx) * 0.4 + 0.1, 2),
                    "forgiveness": round(keyed_float(site_seed, "k_forg", c_idx, k_idx) * 0.6 + 0.2, 2),
                    "profession": "Child",
                    "generation_order": 2,
                })

            # Husband dict
            unindexed_chars.append({
                "temp_id": h_temp,
                "first_name": h_name,
                "last_name": fam_husband,
                "family_id": fam_id,
                "settlement_id": site.id,
                "age_ticks": h_age_years * 12,
                "sex": "M",
                "spouse_temp_id": w_temp,
                "father_temp_id": None,
                "mother_temp_id": None,
                "children_temp_ids": tuple(kid_temps),
                "suspicion": round(keyed_float(site_seed, "h_susp", c_idx, 0) * 0.5 + 0.1, 2),
                "forgiveness": round(keyed_float(site_seed, "h_forg", c_idx, 0) * 0.6 + 0.2, 2),
                "profession": self._assign_profession(site, "M", c_idx),
                "generation_order": 1,
            })

            # Wife dict
            unindexed_chars.append({
                "temp_id": w_temp,
                "first_name": w_name,
                "last_name": fam_husband,
                "family_id": fam_id,
                "settlement_id": site.id,
                "age_ticks": w_age_years * 12,
                "sex": "F",
                "spouse_temp_id": h_temp,
                "father_temp_id": None,
                "mother_temp_id": None,
                "children_temp_ids": tuple(kid_temps),
                "suspicion": round(keyed_float(site_seed, "w_susp", c_idx, 0) * 0.5 + 0.1, 2),
                "forgiveness": round(keyed_float(site_seed, "w_forg", c_idx, 0) * 0.6 + 0.2, 2),
                "profession": self._assign_profession(site, "F", c_idx),
                "generation_order": 1,
            })

            unindexed_chars.extend(kid_dicts)

        # Add 2 to 4 Elders (Aged 50 to 65)
        num_elders = 2 + (keyed_hash_int(site_seed, "num_elders", 0, 0) % 3)
        for e_idx in range(num_elders):
            e_temp = f"t_{site.id}_e_{e_idx}"
            e_sex = "M" if (e_idx % 2 == 0) else "F"
            e_name = pick_first_name(e_sex, f"e_name_{e_idx}")
            e_fam = family_names[e_idx % len(family_names)]
            e_fam_id = f"fam_{site.id}_{e_idx % NUM_FAMILIES}"
            e_age = keyed_int(site_seed, "e_age", e_idx, 0, 50, 65)
            used_full_names.add(f"{e_name} {e_fam}")

            unindexed_chars.append({
                "temp_id": e_temp,
                "first_name": e_name,
                "last_name": e_fam,
                "family_id": e_fam_id,
                "settlement_id": site.id,
                "age_ticks": e_age * 12,
                "sex": e_sex,
                "spouse_temp_id": None,
                "father_temp_id": None,
                "mother_temp_id": None,
                "children_temp_ids": (),
                "suspicion": round(keyed_float(site_seed, "e_susp", e_idx, 0) * 0.4 + 0.1, 2),
                "forgiveness": round(keyed_float(site_seed, "e_forg", e_idx, 0) * 0.6 + 0.2, 2),
                "profession": "Elder",
                "generation_order": 0,  # oldest generation
            })

        # Add young single adults (Aged 16 to 25) until pop_target is reached
        s_idx = 0
        while len(unindexed_chars) < pop_target:
            s_temp = f"t_{site.id}_s_{s_idx}"
            s_sex = "M" if (s_idx % 2 == 0) else "F"
            s_name = pick_first_name(s_sex, f"s_name_{s_idx}")
            s_fam = family_names[(s_idx + 2) % len(family_names)]
            s_fam_id = f"fam_{site.id}_{(s_idx + 2) % NUM_FAMILIES}"
            s_age = keyed_int(site_seed, "s_age", s_idx, 0, 16, 25)
            used_full_names.add(f"{s_name} {s_fam}")

            unindexed_chars.append({
                "temp_id": s_temp,
                "first_name": s_name,
                "last_name": s_fam,
                "family_id": s_fam_id,
                "settlement_id": site.id,
                "age_ticks": s_age * 12,
                "sex": s_sex,
                "spouse_temp_id": None,
                "father_temp_id": None,
                "mother_temp_id": None,
                "children_temp_ids": (),
                "suspicion": round(keyed_float(site_seed, "s_susp", s_idx, 0) * 0.5 + 0.1, 2),
                "forgiveness": round(keyed_float(site_seed, "s_forg", s_idx, 0) * 0.6 + 0.2, 2),
                "profession": self._assign_profession(site, s_sex, s_idx + 20),
                "generation_order": 1,
            })
            s_idx += 1

        # Sort within settlement by structural order (generation_order, temp_id)
        # NEVER sort by character names, which must remain isolated in the 'name:' domain
        unindexed_chars.sort(key=lambda d: (d["generation_order"], d["temp_id"]))
        return unindexed_chars

    def _assign_profession(self, site: SettlementSite, sex: str, index: int) -> str:
        """Assigns a profession weighted by site resource profile."""
        roll = keyed_hash_int(self.chronicle_seed, "prof_roll", site.id, index) % 100

        if site.ore_richness >= 1.25 and roll < 40:
            return "Miner" if sex == "M" else "Smith"
        elif site.forest >= 1.25 and roll < 40:
            return "Woodcutter" if sex == "M" else "Herbalist"
        elif site.water_access >= 0.60 and roll < 40:
            return "Fisher" if sex == "M" else "Weaver"
        elif site.farmland >= 1.20 and roll < 45:
            return "Farmer"
        elif roll < 20:
            return "Priest"
        elif roll < 35:
            return "Builder"
        else:
            return "Laborer"
