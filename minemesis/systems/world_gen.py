"""
Deterministic World Generation for Milestone 0.5.

Adheres strictly to agent.md and Milestone 0.5 (Section 4.5):
- 1 seed
- 2D map
- 3 settlements with asymmetric productivity endowments
- ~30 named characters
- Family structures included
"""

from __future__ import annotations
from minemesis.core.rng import keyed_choice, keyed_float, keyed_int
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement

FIRST_NAMES_MALE = [
    "Arthur", "Rowan", "Caleb", "Gideon", "Tobias", "Bram", "Cedric", "Aldous",
    "Gareth", "Eldrin", "Silas", "Corin", "Lucan", "Orson", "Theron", "Vance"
]

FIRST_NAMES_FEMALE = [
    "Lyra", "Eleni", "Maeve", "Freya", "Astrid", "Briony", "Isolde", "Sylvia",
    "Kaelen", "Morwen", "Brenna", "Thalia", "Vesper", "Sari", "Daphne", "Elora"
]

FAMILY_NAMES = [
    "Ironwood", "Rivers", "Stone", "Ashford", "Crowley", "Oakhaven",
    "Vance", "Blackwood", "Falconer", "Winter", "Hawthorne", "Miller"
]


def generate_world(seed: int) -> tuple[dict[str, Settlement], dict[str, Character]]:
    """
    Deterministically generates 3 settlements with asymmetric endowments
    and 30 named characters organized in family structures.
    """
    settlements: dict[str, Settlement] = {}
    characters: dict[str, Character] = {}

    # 1. Asymmetric settlement profiles (Section 4.5)
    settlement_configs = [
        # (id, name, x, y, base_food, base_wood, base_ore, base_wealth, farm, forest, ore, defense)
        ("set_oakhaven", "Oakhaven", 10, 20, 160, 110, 40, 60, 1.45, 1.10, 0.60, 0.85),
        ("set_riverbend", "Riverbend", 60, 25, 120, 150, 75, 70, 1.05, 1.45, 0.95, 1.00),
        ("set_ironpeak", "Ironpeak", 35, 80, 75, 80, 140, 90, 0.55, 0.75, 1.75, 1.50),
    ]

    for s_id, s_name, x, y, food, wood, ore, wealth, farm, forst, o_rich, defn in settlement_configs:
        # Small seed-keyed variance (±10%)
        farm_mod = 0.9 + 0.2 * keyed_float(seed, "gen_farm", s_id, 0)
        ore_mod = 0.9 + 0.2 * keyed_float(seed, "gen_ore", s_id, 0)

        settlements[s_id] = Settlement(
            id=s_id,
            name=s_name,
            x=x,
            y=y,
            food=food,
            wood=wood,
            ore=ore,
            wealth=wealth,
            farmland=round(farm * farm_mod, 2),
            forest=round(forst, 2),
            ore_richness=round(o_rich * ore_mod, 2),
            defensibility=round(defn, 2),
            stability=1.0,
        )

    # 2. Generate 30 characters (10 per settlement)
    char_counter = 0
    family_pairs = [
        ("Ironwood", "Ashford"),
        ("Rivers", "Crowley"),
        ("Stone", "Blackwood"),
    ]

    sorted_s_ids = sorted(settlements.keys())

    for s_idx, s_id in enumerate(sorted_s_ids):
        fam1, fam2 = family_pairs[s_idx]
        settlement = settlements[s_id]

        # Family 1: Father, Mother, 2 Children (4 characters)
        f1_father_id = f"char_{char_counter}"
        char_counter += 1
        f1_mother_id = f"char_{char_counter}"
        char_counter += 1
        f1_child1_id = f"char_{char_counter}"
        char_counter += 1
        f1_child2_id = f"char_{char_counter}"
        char_counter += 1

        f1_father = Character(
            id=f1_father_id,
            first_name=FIRST_NAMES_MALE[s_idx * 4 + 0],
            last_name=fam1,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f1_father_id, 0, 36 * 12, 45 * 12),
            sex="M",
            spouse_id=f1_mother_id,
            children_ids=[f1_child1_id, f1_child2_id],
            suspicion=0.35 + 0.1 * s_idx,
            forgiveness=0.60 - 0.1 * s_idx,
        )
        f1_mother = Character(
            id=f1_mother_id,
            first_name=FIRST_NAMES_FEMALE[s_idx * 4 + 0],
            last_name=fam1,
            settlement_id=s_id,
            age_ticks=f1_father.age_ticks - 24,
            sex="F",
            spouse_id=f1_father_id,
            children_ids=[f1_child1_id, f1_child2_id],
            suspicion=0.40,
            forgiveness=0.60,
        )
        f1_child1 = Character(
            id=f1_child1_id,
            first_name=FIRST_NAMES_MALE[s_idx * 4 + 1],
            last_name=fam1,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f1_child1_id, 0, 16 * 12, 19 * 12),
            sex="M",
            father_id=f1_father_id,
            mother_id=f1_mother_id,
            suspicion=0.55,
            forgiveness=0.45,
        )
        f1_child2 = Character(
            id=f1_child2_id,
            first_name=FIRST_NAMES_FEMALE[s_idx * 4 + 1],
            last_name=fam1,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f1_child2_id, 0, 12 * 12, 15 * 12),
            sex="F",
            father_id=f1_father_id,
            mother_id=f1_mother_id,
            suspicion=0.35,
            forgiveness=0.65,
        )

        # Family 2: Father, Mother, 2 Children (4 characters)
        f2_father_id = f"char_{char_counter}"
        char_counter += 1
        f2_mother_id = f"char_{char_counter}"
        char_counter += 1
        f2_child1_id = f"char_{char_counter}"
        char_counter += 1
        f2_child2_id = f"char_{char_counter}"
        char_counter += 1

        f2_father = Character(
            id=f2_father_id,
            first_name=FIRST_NAMES_MALE[s_idx * 4 + 2],
            last_name=fam2,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f2_father_id, 0, 38 * 12, 48 * 12),
            sex="M",
            spouse_id=f2_mother_id,
            children_ids=[f2_child1_id, f2_child2_id],
            suspicion=0.50,
            forgiveness=0.50,
        )
        f2_mother = Character(
            id=f2_mother_id,
            first_name=FIRST_NAMES_FEMALE[s_idx * 4 + 2],
            last_name=fam2,
            settlement_id=s_id,
            age_ticks=f2_father.age_ticks - 12,
            sex="F",
            spouse_id=f2_father_id,
            children_ids=[f2_child1_id, f2_child2_id],
            suspicion=0.35,
            forgiveness=0.65,
        )
        f2_child1 = Character(
            id=f2_child1_id,
            first_name=FIRST_NAMES_FEMALE[s_idx * 4 + 3],
            last_name=fam2,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f2_child1_id, 0, 17 * 12, 21 * 12),
            sex="F",
            father_id=f2_father_id,
            mother_id=f2_mother_id,
            suspicion=0.40,
            forgiveness=0.60,
        )
        f2_child2 = Character(
            id=f2_child2_id,
            first_name=FIRST_NAMES_MALE[s_idx * 4 + 3],
            last_name=fam2,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", f2_child2_id, 0, 10 * 12, 14 * 12),
            sex="M",
            father_id=f2_father_id,
            mother_id=f2_mother_id,
            suspicion=0.50,
            forgiveness=0.50,
        )

        # 2 Unaffiliated young adults (total 10 per settlement)
        u1_id = f"char_{char_counter}"
        char_counter += 1
        u2_id = f"char_{char_counter}"
        char_counter += 1

        u1 = Character(
            id=u1_id,
            first_name=keyed_choice(seed, "gen_name", u1_id, 0, FIRST_NAMES_MALE, salt="u1"),
            last_name=fam1,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", u1_id, 0, 20 * 12, 26 * 12),
            sex="M",
            suspicion=0.45,
            forgiveness=0.55,
        )
        u2 = Character(
            id=u2_id,
            first_name=keyed_choice(seed, "gen_name", u2_id, 0, FIRST_NAMES_FEMALE, salt="u2"),
            last_name=fam2,
            settlement_id=s_id,
            age_ticks=keyed_int(seed, "gen_age", u2_id, 0, 19 * 12, 25 * 12),
            sex="F",
            suspicion=0.40,
            forgiveness=0.60,
        )

        settlement_chars = [
            f1_father, f1_mother, f1_child1, f1_child2,
            f2_father, f2_mother, f2_child1, f2_child2,
            u1, u2
        ]

        for c in settlement_chars:
            characters[c.id] = c
            settlement.member_ids.append(c.id)

        # Chief is designated as the elder father
        settlement.leader_id = f1_father.id

    return settlements, characters
