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


class KeyedRNG:
    """
    Deterministic pseudo-random number generator backed by keyed SHA-256 hashing.
    Process-independent, platform-independent, and immune to Python's hash randomization.
    Provides standard PRNG methods: random, uniform, randint, randrange, choice, sample, shuffle.
    """

    def __init__(self, seed: int | str, stream: str = "default", step: int = 0) -> None:
        self.seed = str(seed)
        self.stream = stream
        self.step = step

    def _next_uint64(self, salt: str | int = 0) -> int:
        self.step += 1
        key = f"{self.seed}:{self.stream}:{self.step}:{salt}".encode("utf-8")
        digest = hashlib.sha256(key).digest()
        (val,) = struct.unpack(">Q", digest[:8])
        return val

    def random(self) -> float:
        """Returns a deterministic float in [0.0, 1.0) with 53 bits of precision."""
        val = self._next_uint64()
        return (val >> 11) / (1 << 53)

    def uniform(self, a: float, b: float) -> float:
        """Returns a deterministic float in [a, b]."""
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        """Returns a deterministic integer in [a, b] inclusive."""
        if a > b:
            raise ValueError(f"a ({a}) cannot be greater than b ({b})")
        if a == b:
            return a
        span = (b - a) + 1
        return a + (self._next_uint64() % span)

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        """Returns a chosen element from range(start, stop, step)."""
        if stop is None:
            stop = start
            start = 0
        if step == 1:
            if start >= stop:
                raise ValueError(f"empty range for randrange({start}, {stop})")
            return self.randint(start, stop - 1)
        width = stop - start
        n = (width + step - 1) // step if step > 0 else (width + step + 1) // step
        if n <= 0:
            raise ValueError(f"empty range for randrange({start}, {stop}, {step})")
        return start + step * self.randint(0, n - 1)

    def choice(self, sequence: Sequence[T]) -> T:
        """Returns a deterministic random element from non-empty sequence."""
        if not sequence:
            raise IndexError("Cannot choose from an empty sequence")
        idx = self.randint(0, len(sequence) - 1)
        return sequence[idx]

    def sample(self, sequence: Sequence[T], k: int) -> list[T]:
        """Returns k unique deterministic elements sampled from sequence."""
        n = len(sequence)
        if k > n:
            raise ValueError(f"Sample larger than population: {k} > {n}")
        if k == 0:
            return []
        pool = list(sequence)
        result: list[T] = []
        for _ in range(k):
            idx = self.randint(0, len(pool) - 1)
            result.append(pool.pop(idx))
        return result

    def shuffle(self, seq: list[T]) -> None:
        """In-place Fisher-Yates shuffle."""
        for i in range(len(seq) - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

