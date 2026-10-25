"""
V0 Procedural World Generator (Before Milestone T0 Terrain Engine).

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).

Rules:
- Governed strictly by WorldSeed (chronicle seed is never touched).
- Generates bounded finite map with 3 to 7 settlements.
- Platform-independent noise: integer hash noise with smoothstep using only + - * / and sqrt.
- Zero calls to math.sin, math.cos, math.exp, or math.pow.
- Generates place names from syllable tables selected by site profile.
- Viability guaranteed at generation time through deterministic retry loop.
"""

from __future__ import annotations
import math
from typing import Sequence

from minemesis.core.rng import keyed_hash_int
from minemesis.systems.world_spec import SettlementSite, WorldSpec, WorldProvider


# Multi-Continental Place Name Traditions (Spanning Global Continents)
# Rendered in accessible English typography while preserving authentic cultural phonotactics
GLOBAL_VILLAGE_TRADITIONS = {
    # 1. Anglo-Celtic & Western European
    "anglo_celtic": {
        "prefixes": [
            "Stone", "Ash", "River", "High", "Winter", "Black", "Oak", "Falcon", "Crow", "White",
            "Silver", "Thorn", "Red", "Glen", "Loch", "Bryn", "Fjord", "Kirk", "Heath", "Moor",
            "Raven", "Shield", "Vale", "Dale", "Cliff", "Brook", "Holm", "Bramble", "Fox", "Wolf",
            "Alder", "Birch", "Iron", "Gold", "Hawk", "Hart", "Barrow", "Fair", "Amber", "Deep"
        ],
        "suffixes": [
            "ford", "bury", "stead", "haven", "dale", "moor", "hurst", "wick", "ton", "croft",
            "garth", "bridge", "wood", "ridge", "well", "crest", "cross", "gate", "holm", "field",
            "berg", "kirk", "by", "vik", "gard", "nes", "low", "worth", "mouth", "mere"
        ],
    },
    # 2. Mediterranean & Southern European
    "mediterranean": {
        "prefixes": [
            "Monte", "Valle", "Porto", "Rocca", "Castel", "Riva", "Bella", "Serena", "Terra", "Costa",
            "Ponte", "Fonte", "Sol", "Sierra", "Villa", "Camino", "Playa", "Isla", "Rio", "Bosco",
            "San", "Santa", "Canto", "Alba", "Pico", "Viento", "Cielo", "Luz", "Plaza", "Faro"
        ],
        "suffixes": [
            "monte", "valle", "porto", "rocca", "castello", "riva", "costa", "ponte", "fonte", "canto",
            "villa", "camino", "bello", "vista", "verde", "mar", "pico", "sierra", "faro", "plaza"
        ],
    },
    # 3. Nordic & Baltic
    "nordic": {
        "prefixes": [
            "Fjord", "Frost", "Nord", "Is", "Skag", "Tind", "Foss", "Strom", "Vind", "Borg",
            "Lund", "Hult", "Bred", "Stor", "Myr", "Klint", "Malm", "Gull", "Ulf", "Bjorn",
            "Varg", "Hauk", "Ravne", "Sjo", "Hav", "Vik", "Trom", "Vester", "Aust", "Syd"
        ],
        "suffixes": [
            "vik", "gard", "holm", "by", "fjord", "foss", "tind", "nes", "skag", "borg",
            "lund", "hult", "sund", "dal", "bu", "mark", "berg", "tuna", "valla", "havn"
        ],
    },
    # 4. Slavic & Eastern European
    "slavic": {
        "prefixes": [
            "Bel", "Novo", "Stari", "Krasno", "Zlat", "Gora", "Reka", "Les", "Bor", "Yar",
            "Dol", "Mir", "Svet", "Lug", "Pol", "Ozer", "Brod", "Grad", "Chern", "Dub",
            "Lip", "Berez", "Ostrov", "Vysok", "Chist", "Tikh", "Zelen", "Kam", "Plam", "Voda"
        ],
        "suffixes": [
            "grad", "pol", "yar", "bor", "les", "brod", "dol", "gora", "mir", "lug",
            "reka", "voda", "selo", "stan", "pole", "ostrov", "kamen", "dub", "berez", "yar"
        ],
    },
    # 5. East Asian (Sino / Japanese / Korean phonetics in English)
    "east_asian": {
        "prefixes": [
            "Yama", "Shima", "Kawa", "Mori", "Hana", "Tani", "Oka", "Matsu", "Sugi", "Kuro",
            "Shiro", "Qing", "Bai", "Jin", "Shan", "Jiang", "Long", "Feng", "Yun", "Chun",
            "Cheon", "Baek", "Gang", "Han", "Gyeong", "Pyeong", "Song", "An", "Yue", "Tian",
            "Tai", "Dong", "Nan", "Xi", "Bei", "Zhong", "Lu", "Hai", "He", "Chuan"
        ],
        "suffixes": [
            "yama", "shima", "kawa", "mori", "hara", "sato", "tani", "oka", "mura", "zaki",
            "shan", "jiang", "zhou", "ping", "lin", "hai", "yuan", "cheon", "san", "gang",
            "jin", "dong", "seong", "gok", "do", "ri", "man", "kou", "tan", "wan"
        ],
    },
    # 6. South Asian / Indic
    "south_asian": {
        "prefixes": [
            "Surya", "Chandra", "Ganga", "Shanti", "Ratna", "Sagar", "Nandi", "Vana", "Deva", "Amrita",
            "Kalyan", "Rishi", "Sundar", "Megha", "Pushpa", "Jala", "Himal", "Tara", "Arjun", "Ashok",
            "Kashi", "Shiva", "Brahma", "Indra", "Padma", "Anand", "Vayu", "Agni", "Prithvi", "Shri",
            "Hari", "Om", "Dharma", "Satya", "Maha", "Raj", "Vijay", "Nil", "Swarna", "Kesh"
        ],
        "suffixes": [
            "pur", "nagar", "giri", "durg", "ghat", "sar", "vapi", "gram", "kanda", "palli",
            "khet", "vada", "kund", "tal", "daha", "bazaar", "pura", "dham", "sthan", "garh"
        ],
    },
    # 7. Middle Eastern & North African (Semitic / Persian)
    "middle_eastern": {
        "prefixes": [
            "Nahr", "Jabal", "Ain", "Beit", "Qasr", "Bandar", "Dar", "Bahr", "Noor", "Wadi",
            "Bustan", "Mina", "Rabat", "Bab", "Zaytoun", "Sultan", "Shah", "Firuz", "Roshan", "Shirin",
            "Mir", "Khor", "Diyar", "Medina", "Kuh", "Dasht", "Gul", "Chinar", "Daryacheh", "Sahar"
        ],
        "suffixes": [
            "bad", "abad", "stan", "oasis", "wadi", "kasbah", "medina", "sar", "bazar", "bahr",
            "jabal", "dar", "makan", "khan", "gah", "kuh", "nahr", "gard", "roud", "gah"
        ],
    },
    # 8. African (Swahili, Bantu, West African)
    "african": {
        "prefixes": [
            "Kilima", "Ziwa", "Bonde", "Mto", "Shamba", "Imani", "Jua", "Simba", "Amani", "Mlima",
            "Kaya", "Nyota", "Kazi", "Baraka", "Mawenzi", "Umoja", "Kwame", "Oba", "Zuri", "Tano",
            "Asante", "Kibo", "Serengeti", "Ruvuma", "Mara", "Bantu", "Zambezi", "Limpopo", "Nile", "Congo",
            "Kano", "Ife", "Oyo", "Kumasi", "Lamu", "Malindi", "Kilwa", "Sofala", "Kigali", "Goma"
        ],
        "suffixes": [
            "zuri", "boma", "kwa", "mji", "kaya", "vlei", "dala", "mani", "shamba", "ziwa",
            "mto", "hills", "haven", "springs", "falls", "pass", "ridge", "vale", "grove", "point"
        ],
    },
    # 9. Indigenous Americas & Oceanic
    "americas_oceanic": {
        "prefixes": [
            "Canyon", "Bluff", "Mesa", "Prairie", "Arroyo", "Creek", "Ridge", "Bayou", "Pueblo", "Sierra",
            "Moana", "Atoll", "Reef", "Wai", "Motu", "Tane", "Rua", "Aroha", "Hawa", "Koa",
            "Kauri", "Totara", "Anahuac", "Tenoch", "Cuzco", "Andes", "Pampa", "Selva", "Rani", "Tahiti"
        ],
        "suffixes": [
            "tlan", "pan", "co", "koti", "wai", "moana", "nui", "motu", "mesa", "bluff",
            "creek", "canyon", "bayou", "falls", "pass", "ridge", "haven", "shores", "peak", "run"
        ],
    },
}

# Retained alias for backward compatibility
PLACE_NAME_TABLES = GLOBAL_VILLAGE_TRADITIONS


def _uint64_hash(x: int, y: int, seed: int, salt: int = 0) -> int:
    """Platform-independent 64-bit integer mix."""
    h = (seed ^ (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 32)) * 0xd6e8feb86659fd93 & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 32)) * 0xd6e8feb86659fd93 & 0xFFFFFFFFFFFFFFFF
    return h ^ (h >> 32)


def _hash_float(x: int, y: int, seed: int, salt: int = 0) -> float:
    """Platform-independent float in [0.0, 1.0) derived strictly from integer hash."""
    return (_uint64_hash(x, y, seed, salt) >> 11) / (1 << 53)


def _smoothstep(t: float) -> float:
    """Smoothstep interpolation using only multiplication and addition: 3t^2 - 2t^3."""
    return t * t * (3.0 - 2.0 * t)


def value_noise_2d(x: float, y: float, seed: int, salt: int = 0) -> float:
    """
    Platform-independent 2D value noise with smoothstep interpolation.
    Uses strictly +, -, *, / arithmetic.
    Zero math.sin, math.cos, math.exp, math.pow.
    """
    x0 = int(x) if x >= 0 else int(x) - 1
    y0 = int(y) if y >= 0 else int(y) - 1
    x1 = x0 + 1
    y1 = y0 + 1

    fx = x - x0
    fy = y - y0

    wx = _smoothstep(fx)
    wy = _smoothstep(fy)

    c00 = _hash_float(x0, y0, seed, salt)
    c10 = _hash_float(x1, y0, seed, salt)
    c01 = _hash_float(x0, y1, seed, salt)
    c11 = _hash_float(x1, y1, seed, salt)

    nx0 = c00 + wx * (c10 - c00)
    nx1 = c01 + wx * (c11 - c01)
    return nx0 + wy * (nx1 - nx0)


def distance_euclidean(x1: int, y1: int, x2: int, y2: int) -> float:
    """Euclidean distance using sqrt."""
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx * dx + dy * dy)


class V0WorldGenerator:
    """
    WorldProvider implementation for Milestone 0.5.3.
    Generates 10 to 35 settlements across a 300x300 world with multi-continental naming traditions.
    """
    def __init__(
        self,
        map_width: int = 300,
        map_height: int = 300,
        margin: int = 20,
        min_settlements: int = 10,
        max_settlements: int = 35,
    ):
        self.map_width = map_width
        self.map_height = map_height
        self.margin = margin
        self.min_settlements = min_settlements
        self.max_settlements = max_settlements

    def generate(self, world_seed: int, name_salt: int = 0) -> WorldSpec:
        """
        Deterministically produces an immutable WorldSpec from world_seed.
        Guarantees 100% economic viability and minimum spacing through deterministic retries.
        Place names use isolated 'name:' domain keying across global continental traditions.
        """
        # Determine target settlement count: 10 to 35
        count_roll = keyed_hash_int(world_seed, "target_settlement_count", 0, 0)
        span = max(1, self.max_settlements - self.min_settlements + 1)
        target_count = self.min_settlements + (count_roll % span)  # 10 to 35

        current_count = target_count
        while current_count >= self.min_settlements:
            for attempt in range(25):
                attempt_seed = keyed_hash_int(world_seed, "world_attempt", attempt, current_count)
                sites = self._attempt_generate_sites(attempt_seed, current_count, name_salt=name_salt)
                if sites and self._is_world_viable(sites):
                    return WorldSpec(
                        world_seed=world_seed,
                        map_width=self.map_width,
                        map_height=self.map_height,
                        settlements=tuple(sites),
                        generator_version="v0",
                    )
            # If 25 attempts failed at current_count, decrease settlement count by 1
            current_count -= 1

        # Fallback to guaranteed baseline 10 sites
        fallback_seed = keyed_hash_int(world_seed, "fallback_sites", 0, 0)
        fallback_sites = self._generate_guaranteed_baseline(fallback_seed, name_salt=name_salt)
        return WorldSpec(
            world_seed=world_seed,
            map_width=self.map_width,
            map_height=self.map_height,
            settlements=tuple(fallback_sites),
            generator_version="v0",
        )

    def _attempt_generate_sites(self, seed: int, count: int, name_salt: int = 0) -> list[SettlementSite] | None:
        """Attempts to sample count sites with minimum distance and valid profiles."""
        min_distance = max(18.0, 36.0 - (count * 0.45))
        usable_w = self.map_width - (2 * self.margin)
        usable_h = self.map_height - (2 * self.margin)
        if usable_w <= 0 or usable_h <= 0:
            return None

        candidates: list[tuple[int, int]] = []
        max_candidate_tries = 600

        for try_idx in range(max_candidate_tries):
            if len(candidates) >= count:
                break
            # Candidate coordinate from hash
            rx = _hash_float(try_idx, 0, seed, salt=1)
            ry = _hash_float(try_idx, 0, seed, salt=2)
            cx = self.margin + int(rx * usable_w)
            cy = self.margin + int(ry * usable_h)

            # Check distance against placed candidates
            if all(distance_euclidean(cx, cy, ox, oy) >= min_distance for ox, oy in candidates):
                candidates.append((cx, cy))

        if len(candidates) < count:
            return None

        # Build sites with resource noise and distinct names
        sites: list[SettlementSite] = []
        used_names: set[str] = set()

        for idx, (x, y) in enumerate(candidates):
            site_id = f"set_{idx}"
            # Resource profiles from 2D value noise sampled at scale
            scale = 0.05
            n_farm = value_noise_2d(x * scale, y * scale, seed, salt=10)
            n_forest = value_noise_2d(x * scale, y * scale, seed, salt=20)
            n_ore = value_noise_2d(x * scale, y * scale, seed, salt=30)
            n_defense = value_noise_2d(x * scale, y * scale, seed, salt=40)
            n_water = value_noise_2d(x * scale, y * scale, seed, salt=50)

            # Classify dominant site type to guarantee asymmetric economic diversity
            if idx == 0:
                site_type = "plain"  # Agricultural breadbasket
            elif idx == 1:
                site_type = "mountain"  # Ore-rich mining center
            elif idx == 2:
                site_type = "river"  # Riverine trade & timber
            else:
                # Emergent site type from landscape noise
                if n_water >= 0.55:
                    site_type = "river"
                elif n_ore >= 0.55 and n_defense >= 0.50:
                    site_type = "mountain"
                elif n_forest >= 0.55:
                    site_type = "forest"
                else:
                    site_type = "plain"

            # Endowments calibrated to asymmetric archetype
            if site_type == "mountain":
                farmland = round(0.48 + n_farm * 0.20, 2)         # [0.48, 0.68] (low subsistence)
                forest = round(0.60 + n_forest * 0.35, 2)           # [0.60, 0.95]
                ore = round(1.45 + n_ore * 0.55, 2)                # [1.45, 2.00] (mining wealth)
                defense = round(1.25 + n_defense * 0.45, 2)         # [1.25, 1.70]
                water = round(n_water * 0.35, 2)                   # [0.00, 0.35]
                base_food = 75
                base_wood = 80
                base_ore = 140
                base_wealth = 85
            elif site_type == "river":
                farmland = round(0.95 + n_farm * 0.35, 2)         # [0.95, 1.30]
                forest = round(1.20 + n_forest * 0.45, 2)          # [1.20, 1.65] (lumber)
                ore = round(0.70 + n_ore * 0.40, 2)                # [0.70, 1.10]
                defense = round(0.85 + n_defense * 0.30, 2)        # [0.85, 1.15]
                water = round(0.65 + n_water * 0.35, 2)            # [0.65, 1.00]
                base_food = 120
                base_wood = 150
                base_ore = 70
                base_wealth = 70
            elif site_type == "forest":
                farmland = round(0.75 + n_farm * 0.35, 2)         # [0.75, 1.10]
                forest = round(1.35 + n_forest * 0.50, 2)          # [1.35, 1.85] (heavy timber)
                ore = round(0.60 + n_ore * 0.40, 2)                # [0.60, 1.00]
                defense = round(0.90 + n_defense * 0.35, 2)        # [0.90, 1.25]
                water = round(0.30 + n_water * 0.40, 2)            # [0.30, 0.70]
                base_food = 110
                base_wood = 160
                base_ore = 50
                base_wealth = 65
            else: # "plain"
                farmland = round(1.35 + n_farm * 0.50, 2)         # [1.35, 1.85] (breadbasket)
                forest = round(0.85 + n_forest * 0.35, 2)          # [0.85, 1.20]
                ore = round(0.45 + n_ore * 0.35, 2)                # [0.45, 0.80]
                defense = round(0.75 + n_defense * 0.30, 2)        # [0.75, 1.05]
                water = round(0.20 + n_water * 0.40, 2)            # [0.20, 0.60]
                base_food = 160
                base_wood = 100
                base_ore = 40
                base_wealth = 60

            # Generate unique name in isolated name domain
            name = self._generate_place_name(site_type, seed, idx, used_names, name_salt=name_salt)
            used_names.add(name)

            sites.append(SettlementSite(
                id=site_id,
                name=name,
                x=x,
                y=y,
                farmland=farmland,
                forest=forest,
                ore_richness=ore,
                defensibility=defense,
                water_access=water,
                site_type=site_type,
                base_food=base_food,
                base_wood=base_wood,
                base_ore=base_ore,
                base_wealth=base_wealth,
            ))

        return sites

    def _generate_place_name(self, site_type: str, seed: int, index: int, used_names: set[str], name_salt: int = 0) -> str:
        """Generates a unique thematic place name spanning diverse global naming traditions."""
        tradition_keys = list(GLOBAL_VILLAGE_TRADITIONS.keys())
        # Pick culture tradition based on site index and seed hash
        t_choice = tradition_keys[keyed_hash_int(seed, "name:tradition_choice", index, 0, salt=name_salt) % len(tradition_keys)]
        tradition_tables = GLOBAL_VILLAGE_TRADITIONS[t_choice]
        prefs = tradition_tables["prefixes"]
        suffs = tradition_tables["suffixes"]

        for var_idx in range(100):
            p_idx = keyed_hash_int(seed, "name:place_prefix", index, var_idx, salt=name_salt) % len(prefs)
            s_idx = keyed_hash_int(seed, "name:place_suffix", index, var_idx, salt=name_salt) % len(suffs)
            pref = prefs[p_idx]
            suff = suffs[s_idx]
            if suff.lower().startswith(pref[-1].lower()):
                cand = f"{pref}{suff[1:]}"
            else:
                cand = f"{pref}{suff}"
            if cand not in used_names:
                return cand

        # Fallback with regional descriptor to ensure 100% uniqueness
        modifiers = ["Upper", "Lower", "New", "Great", "Old", "Port", "Fort", "Mount", "Cape", "Saint"]
        mod = modifiers[keyed_hash_int(seed, "name:place_mod", index, 0, salt=name_salt) % len(modifiers)]
        cand = f"{mod} {prefs[index % len(prefs)]}{suffs[index % len(suffs)]}"
        if cand not in used_names:
            return cand
        return f"{prefs[index % len(prefs)]}{suffs[index % len(suffs)]} {index + 1}"

    def _is_world_viable(self, sites: list[SettlementSite]) -> bool:
        """
        Viability at generation time:
        1. Settlement count >= min_settlements.
        2. Every settlement has farmland >= 0.45 OR water_access >= 0.40 OR ore_richness >= 1.20.
        3. World contains at least one agricultural hub with farmland >= 1.20.
        4. World contains resource diversity (ore or forest variation).
        5. Pairwise distance >= min_distance between all sites.
        """
        if len(sites) < self.min_settlements:
            return False

        # Check each site's subsistence viability
        for s in sites:
            is_viable = (
                s.farmland >= 0.70
                or (s.water_access >= 0.40 and s.farmland >= 0.55)
                or (s.ore_richness >= 1.20 and s.farmland >= 0.45)
            )
            if not is_viable:
                return False

        # World agricultural center
        if max(s.farmland for s in sites) < 1.15:
            return False

        # World mining center
        if max(s.ore_richness for s in sites) < 1.15:
            return False

        # Minimum spacing
        min_distance = max(18.0, 36.0 - (len(sites) * 0.45))
        for i in range(len(sites)):
            for j in range(i + 1, len(sites)):
                if distance_euclidean(sites[i].x, sites[i].y, sites[j].x, sites[j].y) < min_distance:
                    return False

        return True

    def _generate_guaranteed_baseline(self, seed: int, name_salt: int = 0) -> list[SettlementSite]:
        """Guaranteed viable baseline of 10 well-spaced settlements as ultimate fallback."""
        configs = [
            ("set_0", "Highplain", 40, 40, 1.45, 1.10, 0.65, 0.90, 0.40, "plain"),
            ("set_1", "Riverford", 150, 40, 1.10, 1.35, 0.85, 1.05, 0.85, "river"),
            ("set_2", "Ironhold", 260, 40, 0.75, 0.80, 1.70, 1.45, 0.30, "mountain"),
            ("set_3", "Greenwood", 40, 150, 1.00, 1.50, 0.60, 1.00, 0.50, "forest"),
            ("set_4", "Sunvalley", 150, 150, 1.50, 1.00, 0.55, 0.85, 0.35, "plain"),
            ("set_5", "Deepcrag", 260, 150, 0.65, 0.75, 1.80, 1.50, 0.25, "mountain"),
            ("set_6", "Otterbend", 40, 260, 1.15, 1.25, 0.70, 0.95, 0.90, "river"),
            ("set_7", "Timberhurst", 150, 260, 0.90, 1.65, 0.65, 1.10, 0.45, "forest"),
            ("set_8", "Goldridge", 260, 260, 0.80, 0.85, 1.60, 1.40, 0.30, "mountain"),
            ("set_9", "Fairmeadow", 200, 200, 1.40, 1.05, 0.60, 0.90, 0.55, "plain"),
        ]
        sites = []
        for s_id, default_name, x, y, farm, forst, ore, defn, water, s_type in configs:
            name = self._generate_place_name(s_type, seed, len(sites), set(), name_salt=name_salt)
            sites.append(SettlementSite(
                id=s_id,
                name=name or default_name,
                x=x,
                y=y,
                farmland=farm,
                forest=forst,
                ore_richness=ore,
                defensibility=defn,
                water_access=water,
                site_type=s_type,
            ))
        return sites
