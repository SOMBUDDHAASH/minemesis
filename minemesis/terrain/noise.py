"""
Platform-Independent Deterministic Noise for Milestone T0.

Rules:
- Governed exclusively by integer hash functions and polynomial interpolation (smoothstep).
- Zero calls to math.sin, math.cos, math.exp, or math.pow.
- Guaranteed identical output across all OS architectures and Python versions.
"""

from __future__ import annotations


def int_hash_2d(seed: int, x: int, y: int, salt: int = 0) -> int:
    """Deterministic 32-bit unsigned integer hash of a 2D coordinate."""
    h = (seed ^ (x * 374761393) ^ (y * 668265263) ^ (salt * 1442695040888963407)) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) * 2654435761) & 0xFFFFFFFF


def int_hash_3d(seed: int, x: int, y: int, z: int, salt: int = 0) -> int:
    """Deterministic 32-bit unsigned integer hash of a 3D coordinate."""
    h = (seed ^ (x * 374761393) ^ (y * 668265263) ^ (z * 1103515245) ^ (salt * 1442695040888963407)) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) * 2654435761) & 0xFFFFFFFF


def smoothstep(t: float) -> float:
    """3t^2 - 2t^3 cubic Hermite polynomial using only elementary arithmetic."""
    return t * t * (3.0 - 2.0 * t)


def value_noise_2d(seed: int, x: float, y: float, salt: int = 0) -> float:
    """Deterministic 2D value noise returning a float in [0.0, 1.0]."""
    x0 = int(x) if x >= 0 else int(x) - 1
    y0 = int(y) if y >= 0 else int(y) - 1
    x1 = x0 + 1
    y1 = y0 + 1

    fx = x - x0
    fy = y - y0

    sx = smoothstep(fx)
    sy = smoothstep(fy)

    v00 = (int_hash_2d(seed, x0, y0, salt) & 0xFFFF) / 65535.0
    v10 = (int_hash_2d(seed, x1, y0, salt) & 0xFFFF) / 65535.0
    v01 = (int_hash_2d(seed, x0, y1, salt) & 0xFFFF) / 65535.0
    v11 = (int_hash_2d(seed, x1, y1, salt) & 0xFFFF) / 65535.0

    top = v00 + sx * (v10 - v00)
    bot = v01 + sx * (v11 - v01)
    return top + sy * (bot - top)


def fbm_noise_2d(
    seed: int,
    x: float,
    y: float,
    octaves: int = 4,
    persistence: float = 0.5,
    salt: int = 0,
) -> float:
    """
    Fractal Brownian Motion (multi-octave value noise).
    Returns normalized float in [0.0, 1.0].
    """
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_amp = 0.0

    for i in range(octaves):
        total += value_noise_2d(seed, x * frequency, y * frequency, salt=salt + i * 137) * amplitude
        max_amp += amplitude
        amplitude *= persistence
        frequency *= 2.0

    return total / max_amp if max_amp > 0 else 0.0
