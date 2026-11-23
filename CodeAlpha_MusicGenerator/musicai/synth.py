"""Synthétiseur simple : notes -> fichier audio WAV (sons de type piano, calculés avec NumPy)."""

import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 22050
HARMONICS = [(1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.06)]


def render_wav(notes, path, sample_rate: int = SAMPLE_RATE):
    """notes : [(début_s, fin_s, hauteur, vélocité)] -> écrit un WAV mono 16 bits dans `path`."""
    release = 0.35
    total = max((end for _, end, _, _ in notes), default=1.0) + release + 1.0
    buffer = np.zeros(int(total * sample_rate), dtype=np.float64)

    for start, end, pitch, velocity in notes:
        duration = max(end - start, 0.05)
        n = int((duration + release) * sample_rate)
        t = np.arange(n) / sample_rate
        freq = 440.0 * 2 ** ((pitch - 69) / 12)

        tone = np.zeros(n)
        for k, amp in HARMONICS:
            if freq * k < sample_rate / 2:
                tone += amp * np.sin(2 * np.pi * freq * k * t)

        decay = 1.4 + max(pitch - 48, 0) / 18                       # les notes aiguës s'éteignent plus vite
        envelope = np.minimum(1.0, t / 0.008) * np.exp(-decay * t)  # attaque brève puis extinction
        envelope *= np.where(t > duration, np.exp(-(t - duration) * 14), 1.0)

        i0 = int(start * sample_rate)
        i1 = min(i0 + n, len(buffer))
        buffer[i0:i1] += (velocity / 127) * 0.2 * (tone * envelope)[:i1 - i0]

    fade = int(0.5 * sample_rate)                                   # fondu de fin
    if len(buffer) > fade:
        buffer[-fade:] *= np.linspace(1, 0, fade)
    peak = np.abs(buffer).max()
    if peak > 0:
        buffer *= 0.9 / peak

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((buffer * 32767).astype("<i2").tobytes())
