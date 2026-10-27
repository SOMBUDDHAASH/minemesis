"""
Procedural Sound Synthesis & Audio Engine for Minemesis Standalone Engine.
Generates crisp 16-bit 22050Hz PCM audio completely in-memory with zero external files
and zero dependencies, played asynchronously via Windows Multimedia.
"""

from __future__ import annotations
import math
import random
import struct
import threading
from typing import Dict, Optional

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class SoundEngine:
    """
    Synthesizes and plays tactile procedural sound effects for:
    - Block destruction (crunch / crumble)
    - Block placement (solid thud / clack)
    - UI slot clicks (crisp mechanical click)
    - Fist punch swing (whoosh sweep)
    """

    SAMPLE_RATE = 22050

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and HAS_WINSOUND
        self._sound_cache: Dict[str, bytes] = {}
        if self.enabled:
            self._prebake_sounds()

    def _build_wav_bytes(self, samples: list[int]) -> bytes:
        raw_pcm = struct.pack(f"<{len(samples)}h", *samples)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + len(raw_pcm), b"WAVE",
            b"fmt ", 16, 1, 1, self.SAMPLE_RATE, self.SAMPLE_RATE * 2, 2, 16,
            b"data", len(raw_pcm),
        )
        return header + raw_pcm

    def _prebake_sounds(self) -> None:
        sr = self.SAMPLE_RATE

        # 1. Block Break (Tactile crunch / crumble, 0.13s)
        n_break = int(sr * 0.13)
        s_break = []
        for i in range(n_break):
            t = i / float(sr)
            env = max(0.0, 1.0 - t / 0.13) ** 1.8
            # Low rumble tone + crunchy noise
            tone = math.sin(2.0 * math.pi * 140.0 * (1.0 - t * 4.0) * t) * 0.4
            noise = random.uniform(-0.8, 0.8) * 0.6
            val = int(max(-32767, min(32767, (tone + noise) * env * 24000.0)))
            s_break.append(val)
        self._sound_cache["break"] = self._build_wav_bytes(s_break)

        # 2. Block Place (Crisp solid thud, 0.08s)
        n_place = int(sr * 0.08)
        s_place = []
        for i in range(n_place):
            t = i / float(sr)
            env = max(0.0, 1.0 - t / 0.08) ** 2.2
            tone = math.sin(2.0 * math.pi * 210.0 * (1.0 - t * 6.0) * t) * 0.75
            click = random.uniform(-0.5, 0.5) * 0.25
            val = int(max(-32767, min(32767, (tone + click) * env * 26000.0)))
            s_place.append(val)
        self._sound_cache["place"] = self._build_wav_bytes(s_place)

        # 3. UI Slot Click (Subtle mechanical click, 0.03s)
        n_click = int(sr * 0.03)
        s_click = []
        for i in range(n_click):
            t = i / float(sr)
            env = max(0.0, 1.0 - t / 0.03) ** 3.0
            tone = math.sin(2.0 * math.pi * 920.0 * t) * 0.85
            val = int(max(-32767, min(32767, tone * env * 18000.0)))
            s_click.append(val)
        self._sound_cache["click"] = self._build_wav_bytes(s_click)

        # 4. Fist Punch Swing (Low air whoosh, 0.09s)
        n_punch = int(sr * 0.09)
        s_punch = []
        for i in range(n_punch):
            t = i / float(sr)
            env = math.sin(t / 0.09 * math.pi)
            noise = random.uniform(-0.6, 0.6)
            tone = math.sin(2.0 * math.pi * 90.0 * t) * 0.4
            val = int(max(-32767, min(32767, (tone + noise) * env * 16000.0)))
            s_punch.append(val)
        self._sound_cache["punch"] = self._build_wav_bytes(s_punch)

    def _play_sound_async(self, sound_data: bytes) -> None:
        def _target():
            try:
                winsound.PlaySound(sound_data, winsound.SND_MEMORY)
            except Exception:
                pass
        t = threading.Thread(target=_target, daemon=True)
        t.start()

    def play(self, sound_name: str) -> None:
        """Plays sound effect asynchronously without blocking game loop."""
        if not self.enabled:
            return
        data = self._sound_cache.get(sound_name)
        if data:
            self._play_sound_async(data)

    def play_break(self) -> None:
        self.play("break")

    def play_place(self) -> None:
        self.play("place")

    def play_click(self) -> None:
        self.play("click")

    def play_punch(self) -> None:
        self.play("punch")
