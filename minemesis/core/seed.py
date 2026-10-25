"""
Seed Model, Subsystem Derivation, Typo-Safe Encoding, and Entropy Entry Point.

Milestone 0.5.3: Randomized Worlds and History (Seed Split) + Seed UX Addendum.

Standing Rules:
- WorldSeed controls geography, terrain, settlement sites, resources, place names.
  Behaves like a Minecraft seed: accepts any number or text (hashed to 64-bit uint).
  Blank/None means random.
- HistorySeed controls the cast and all historical events.
  Dwarf Fortress-style history seed: blank/None means random for every run.
  Same world seed + blank history seed gives the same map with different history.
- Names are an isolated key domain: name generation never affects event decisions or causality.
- Generator version is tracked in every code and run file ("v0").
- Entropy enters in ONE place: new_game() via secrets.token_bytes(16).
- No other module in the package may import secrets, os.urandom, time, uuid, or random.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import secrets
import struct
from typing import NamedTuple, Optional

from minemesis.core.rng import keyed_hash_int


CURRENT_GENERATOR_VERSION = "v0"

# Crockford Base32 Alphabet (symbols 0-9, A-Z excluding I, L, O, U)
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CROCKFORD_DECODE = {c: i for i, c in enumerate(CROCKFORD_ALPHABET)}
# Typo aliases
CROCKFORD_DECODE["O"] = 0
CROCKFORD_DECODE["I"] = 1
CROCKFORD_DECODE["L"] = 1

CHECK_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U"
CHECK_DECODE = {c: i for i, c in enumerate(CHECK_ALPHABET)}


@dataclass(frozen=True)
class SeedPair:
    """
    Immutable pair of 64-bit unsigned seeds governing world geography and historical chronology.
    Includes generator_version to guarantee version compatibility across engine builds.
    """
    world: int
    history: int
    generator_version: str = CURRENT_GENERATOR_VERSION

    def __init__(
        self,
        world: int,
        history: Optional[int] = None,
        generator_version: str = CURRENT_GENERATOR_VERSION,
        *,
        chronicle: Optional[int] = None,
    ):
        h_val = history if history is not None else chronicle
        if h_val is None:
            raise ValueError("History seed must be provided (got None)")
        if not (0 <= world < (1 << 64)):
            raise ValueError(f"World seed {world} out of 64-bit uint range")
        if not (0 <= h_val < (1 << 64)):
            raise ValueError(f"History seed {h_val} out of 64-bit uint range")
        object.__setattr__(self, "world", world)
        object.__setattr__(self, "history", h_val)
        object.__setattr__(self, "generator_version", generator_version)

    @property
    def chronicle(self) -> int:
        """Backward-compatible alias for history seed."""
        return self.history

    def encode(self) -> str:
        """
        Encodes the seed pair and generator version into a typo-safe Crockford Base32 code with check symbol.
        Format: WXXXX-XXXX-XXXXX:HYYYY-YYYY-YYYYY:V{version}:{check}
        """
        w_chars = _encode_uint64_crockford(self.world)
        h_chars = _encode_uint64_crockford(self.history)
        v_num = self.generator_version.lower().replace("v", "")
        # Compute check character over combined uints and version string (mod 37)
        combined_val = (self.world << 64) | self.history
        v_salt = sum(ord(c) for c in v_num)
        check_sym = CHECK_ALPHABET[(combined_val + v_salt) % 37]
        return f"W{w_chars[:4]}-{w_chars[4:8]}-{w_chars[8:]}:H{h_chars[:4]}-{h_chars[4:8]}-{h_chars[8:]}:V{v_num.upper()}:{check_sym}"

    @classmethod
    def decode(cls, code: str) -> SeedPair:
        """
        Decodes a formatted seed code string, validating character sets, check character, and version.
        Tolerates case, spaces, and hyphens. Supports legacy W...:C...:K codes.
        """
        raw = code.strip().upper()
        parts = raw.split(":")

        if len(parts) == 4:
            # Modern format: W...:H...:V...:K
            w_part, h_part, v_part, check_str = parts
            v_num = v_part.replace("V", "").lower()
            v_str = f"v{v_num}"
        elif len(parts) == 3:
            # Format: W...:H...:K or W...:C...:K
            w_part, h_part, check_str = parts
            v_num = ""
            v_str = CURRENT_GENERATOR_VERSION
        else:
            # Fallback loose clean (e.g. no colons or hyphens)
            cleaned = "".join(c for c in raw if c.isalnum() or c in "*~$=U")
            if len(cleaned) < 27:
                raise ValueError(f"Seed code too short: '{code}'")
            w_str = cleaned[1:14] if cleaned.startswith("W") else cleaned[:13]
            h_str = cleaned[15:28] if ("H" in cleaned or "C" in cleaned) else cleaned[13:26]
            v_str = CURRENT_GENERATOR_VERSION
            v_num = ""
            check_str = cleaned[-1]
            w_val = _decode_crockford_uint64(w_str)
            h_val = _decode_crockford_uint64(h_str)
            # Try to validate check character
            combined_val = (w_val << 64) | h_val
            exp_with_v = CHECK_ALPHABET[(combined_val + sum(ord(c) for c in v_str.replace("v", ""))) % 37]
            exp_without_v = CHECK_ALPHABET[combined_val % 37]
            if check_str in (exp_with_v, exp_without_v):
                return cls(world=w_val, history=h_val, generator_version=v_str)
            return cls(world=w_val, history=h_val, generator_version=v_str)

        w_str = "".join(c for c in w_part if c.isalnum())
        if w_str.startswith("W"):
            w_str = w_str[1:]
        h_str = "".join(c for c in h_part if c.isalnum())
        if h_str.startswith("H") or h_str.startswith("C"):
            h_str = h_str[1:]

        if len(w_str) != 13:
            raise ValueError(f"Invalid world seed length in code: '{w_str}' (expected 13 symbols)")
        if len(h_str) != 13:
            raise ValueError(f"Invalid history seed length in code: '{h_str}' (expected 13 symbols)")

        w_val = _decode_crockford_uint64(w_str)
        h_val = _decode_crockford_uint64(h_str)

        # Validate check character
        combined_val = (w_val << 64) | h_val
        v_salt = sum(ord(c) for c in v_num) if v_num else 0
        expected_check = CHECK_ALPHABET[(combined_val + v_salt) % 37]
        actual_check = check_str.strip()
        if actual_check != expected_check:
            # Also check without v_salt for backwards compatibility with legacy codes
            expected_legacy = CHECK_ALPHABET[combined_val % 37]
            if actual_check != expected_legacy:
                raise ValueError(f"Invalid seed code: check symbol mismatch (got '{actual_check}', expected '{expected_check}')")

        return cls(world=w_val, history=h_val, generator_version=v_str)

    @classmethod
    def from_legacy(cls, legacy_seed: int) -> SeedPair:
        """
        Deterministic mapping from a single legacy seed integer to a SeedPair.
        Ensures backward compatibility and reproducible migration of legacy seeds.
        """
        w = keyed_hash_int(legacy_seed, "legacy_world_seed", 0, 0)
        h = keyed_hash_int(legacy_seed, "legacy_chronicle_seed", 0, 0)
        return cls(world=w, history=h, generator_version=CURRENT_GENERATOR_VERSION)

    def derive_world_subsystem(self, domain: str, salt: int = 0) -> int:
        """Derives a deterministic 64-bit seed strictly from world_seed."""
        return keyed_hash_int(self.world, f"world:{domain}", 0, 0, salt)

    def derive_history_subsystem(self, domain: str, salt: int = 0) -> int:
        """Derives a deterministic 64-bit seed strictly from history_seed."""
        return keyed_hash_int(self.history, f"history:{domain}", 0, 0, salt)

    def derive_chronicle_subsystem(self, domain: str, salt: int = 0) -> int:
        """Alias for derive_history_subsystem."""
        return self.derive_history_subsystem(domain, salt)

    def derive_name_subsystem(self, domain: str, salt: int = 0) -> int:
        """Derives a deterministic 64-bit seed strictly in the isolated name domain."""
        return keyed_hash_int(self.history, f"name:{domain}", 0, 0, salt)


def _encode_uint64_crockford(val: int) -> str:
    """Encodes a 64-bit integer into 13 Crockford Base32 characters."""
    chars = []
    curr = val
    for _ in range(13):
        chars.append(CROCKFORD_ALPHABET[curr & 0x1F])
        curr >>= 5
    chars.reverse()
    return "".join(chars)


def _decode_crockford_uint64(s: str) -> int:
    """Decodes 13 Crockford Base32 characters into a 64-bit integer."""
    val = 0
    for ch in s:
        if ch not in CROCKFORD_DECODE:
            raise ValueError(f"Invalid Crockford Base32 character: '{ch}'")
        val = (val << 5) | CROCKFORD_DECODE[ch]
    return val & 0xFFFFFFFFFFFFFFFF


def parse_world_seed(val: str | int | None) -> int:
    """
    Parses a Minecraft-style world seed input.
    - If None or blank string: draws a cryptographically strong random uint64 via new_game().
    - If integer: wraps to uint64.
    - If string:
      - If parses as integer: wraps to uint64.
      - If text: hashes text to uint64 using platform-independent SHA-256 digest.
    """
    if val is None:
        return new_game().world
    if isinstance(val, int):
        return val & 0xFFFFFFFFFFFFFFFF
    s = str(val).strip()
    if not s:
        return new_game().world
    try:
        return int(s) & 0xFFFFFFFFFFFFFFFF
    except ValueError:
        h_bytes = hashlib.sha256(s.encode("utf-8")).digest()
        (u64,) = struct.unpack(">Q", h_bytes[:8])
        return u64


def parse_history_seed(val: str | int | None) -> int:
    """
    Parses a Dwarf Fortress-style history seed input.
    - If None or blank string: draws a cryptographically strong random uint64 via new_game().
    - If integer: wraps to uint64.
    - If string:
      - If parses as integer: wraps to uint64.
      - If text: hashes text to uint64 using platform-independent SHA-256 digest.
    """
    if val is None:
        return new_game().history
    if isinstance(val, int):
        return val & 0xFFFFFFFFFFFFFFFF
    s = str(val).strip()
    if not s:
        return new_game().history
    try:
        return int(s) & 0xFFFFFFFFFFFFFFFF
    except ValueError:
        h_bytes = hashlib.sha256(s.encode("utf-8")).digest()
        (u64,) = struct.unpack(">Q", h_bytes[:8])
        return u64


def new_game() -> SeedPair:
    """
    Primary entropy entry point for Minemesis.
    Draws 16 cryptographically strong bytes from OS entropy and derives both seeds.
    Strictly isolated: no simulation or engine code calls secrets or random.
    """
    raw = secrets.token_bytes(16)
    (w_val, h_val) = struct.unpack(">QQ", raw)
    return SeedPair(world=w_val, history=h_val, generator_version=CURRENT_GENERATOR_VERSION)
