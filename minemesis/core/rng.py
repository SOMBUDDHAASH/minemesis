"""
Keyed Deterministic Random Number Generator.

Follows agent.md determinism specifications:
- Hash(WorldSeed, System, Entity, Tick, Salt)
- Keyed randomness ensures zero shared RNG state
- Fixed evaluation output regardless of execution order
"""

from __future__ import annotations
import hashlib
import struct
from typing import Sequence, TypeVar

T = TypeVar("T")


def keyed_hash_int(seed: int, system: str, entity: str | int, tick: int, salt: str | int = 0) -> int:
    """
    Returns a deterministic 64-bit unsigned integer derived from the keyed parameters.
    """
    key = f"{seed}:{system}:{entity}:{tick}:{salt}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    # Read first 8 bytes as big-endian uint64
    (val,) = struct.unpack(">Q", digest[:8])
    return val


def keyed_float(seed: int, system: str, entity: str | int, tick: int, salt: str | int = 0) -> float:
    """
    Returns a deterministic float in [0.0, 1.0) with 53 bits of precision.
    """
    val = keyed_hash_int(seed, system, entity, tick, salt)
    # Use 53 bits to match IEEE double precision
    return (val >> 11) / (1 << 53)


def keyed_int(
    seed: int,
    system: str,
    entity: str | int,
    tick: int,
    min_val: int,
    max_val: int,
    salt: str | int = 0,
) -> int:
    """
    Returns a deterministic integer in [min_val, max_val] inclusive.
    """
    if min_val > max_val:
        raise ValueError(f"min_val ({min_val}) cannot be greater than max_val ({max_val})")
    if min_val == max_val:
        return min_val
    range_span = (max_val - min_val) + 1
    val = keyed_hash_int(seed, system, entity, tick, salt)
    return min_val + (val % range_span)


def keyed_choice(
    seed: int,
    system: str,
    entity: str | int,
    tick: int,
    sequence: Sequence[T],
    salt: str | int = 0,
) -> T:
    """
    Returns a deterministic choice from a non-empty sequence.
    """
    if not sequence:
        raise IndexError("Cannot choose from an empty sequence")
    idx = keyed_int(seed, system, entity, tick, 0, len(sequence) - 1, salt=salt)
    return sequence[idx]


def keyed_sample(
    seed: int,
    system: str,
    entity: str | int,
    tick: int,
    sequence: Sequence[T],
    k: int,
    salt: str | int = 0,
) -> list[T]:
    """
    Returns k unique deterministic elements sampled from sequence.
    """
    n = len(sequence)
    if k > n:
        raise ValueError(f"Sample larger than population: {k} > {n}")
    if k == 0:
        return []

    pool = list(sequence)
    result: list[T] = []
    for i in range(k):
        pick_idx = keyed_int(seed, system, entity, tick, 0, len(pool) - 1, salt=f"{salt}:{i}")
        result.append(pool.pop(pick_idx))
    return result
