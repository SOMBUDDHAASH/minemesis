"""
JSON Serialization and Deserialization for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Preserves full round-trip state fidelity for all religions, character faiths, holy sites, and saints.
- Enables complete saving, loading, and inspection without loss of lineage or modifiers.
"""

from __future__ import annotations
import json
from typing import Any, Mapping
from minemesis.religion.religion_models import (
    CharacterFaith,
    CulturalProfile,
    Religion,
)


def serialize_religion_state(
    religions: Mapping[str, Religion],
    faiths: Mapping[str, CharacterFaith],
    rel_counter: int,
    site_counter: int,
    seed: int,
    figure_counter: int = 1,
    myth_counter: int = 1,
    cultural_profiles: Optional[Mapping[str, CulturalProfile]] = None,
    folk_counter: int = 1,
    custom_counter: int = 1,
) -> dict[str, Any]:
    """Serializes the entire religion engine state into a plain JSON-compatible dictionary."""
    data: dict[str, Any] = {
        "seed": seed,
        "rel_counter": rel_counter,
        "site_counter": site_counter,
        "figure_counter": figure_counter,
        "myth_counter": myth_counter,
        "folk_counter": folk_counter,
        "custom_counter": custom_counter,
        "religions": {r_id: r.to_dict() for r_id, r in sorted(religions.items())},
        "faiths": {c_id: f.to_dict() for c_id, f in sorted(faiths.items())},
    }
    if cultural_profiles is not None:
        data["cultural_profiles"] = {s_id: cp.to_dict() for s_id, cp in sorted(cultural_profiles.items())}
    return data


def deserialize_religion_state(
    data: dict[str, Any]
) -> tuple[dict[str, Religion], dict[str, CharacterFaith], int, int, int, int, int, dict[str, CulturalProfile], int, int]:
    """
    Reconstitutes live Religion, CharacterFaith, and CulturalProfile objects from serialized dictionary.
    Returns (religions, faiths, rel_counter, site_counter, seed, figure_counter, myth_counter, cultural_profiles, folk_counter, custom_counter).
    """
    seed = int(data.get("seed", 42))
    rel_counter = int(data.get("rel_counter", 1))
    site_counter = int(data.get("site_counter", 1))
    figure_counter = int(data.get("figure_counter", 1))
    myth_counter = int(data.get("myth_counter", 1))
    folk_counter = int(data.get("folk_counter", 1))
    custom_counter = int(data.get("custom_counter", 1))

    religions: dict[str, Religion] = {}
    for r_id, r_dict in data.get("religions", {}).items():
        religions[r_id] = Religion.from_dict(r_dict)

    faiths: dict[str, CharacterFaith] = {}
    for c_id, f_dict in data.get("faiths", {}).items():
        faiths[c_id] = CharacterFaith.from_dict(f_dict)

    cultural_profiles: dict[str, CulturalProfile] = {}
    for s_id, cp_dict in data.get("cultural_profiles", {}).items():
        cultural_profiles[s_id] = CulturalProfile.from_dict(cp_dict)

    return (
        religions,
        faiths,
        rel_counter,
        site_counter,
        seed,
        figure_counter,
        myth_counter,
        cultural_profiles,
        folk_counter,
        custom_counter,
    )


def to_json(state_dict: dict[str, Any], indent: int = 2) -> str:
    """Exports state dictionary to formatted JSON string."""
    return json.dumps(state_dict, indent=indent, sort_keys=True)


def from_json(json_str: str) -> dict[str, Any]:
    """Loads state dictionary from JSON string."""
    return json.loads(json_str)
