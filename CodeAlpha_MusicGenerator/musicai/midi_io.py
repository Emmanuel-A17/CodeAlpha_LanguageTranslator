"""
Lecture et écriture de fichiers MIDI, sans aucune bibliothèque externe.

Un fichier MIDI est une suite d'événements « note on » / « note off » horodatés.
read_midi  : fichier .mid  -> liste de notes (début, fin, hauteur, vélocité)
write_midi : liste de notes -> fichier .mid
"""

import struct
from pathlib import Path


def _read_vlq(data: bytes, pos: int):
    """Lit un entier à longueur variable (format MIDI)."""
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def _vlq(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def _parse_track(track: bytes, notes: list, tempo_holder: list):
    """Extrait les notes d'une piste. Ignore la batterie (canal 10)."""
    tick, i, status = 0, 0, 0
    active = {}  # (canal, hauteur) -> [(début, vélocité), ...]

    while i < len(track):
        delta, i = _read_vlq(track, i)
        tick += delta
        byte = track[i]

        if byte == 0xFF:  # méta-événement
            meta = track[i + 1]
            length, j = _read_vlq(track, i + 2)
            if meta == 0x51 and length == 3 and not tempo_holder:
                tempo_holder.append(int.from_bytes(track[j:j + 3], "big"))
            i = j + length
            if meta == 0x2F:  # fin de piste
                break
            continue

        if byte in (0xF0, 0xF7):  # sysex
            length, j = _read_vlq(track, i + 1)
            i = j + length
            continue

        if byte & 0x80:
            status = byte
            i += 1
        kind, channel = status & 0xF0, status & 0x0F

        if kind in (0xC0, 0xD0):  # un seul octet de données
            i += 1
            continue

        d1, d2 = track[i], track[i + 1]
        i += 2
        if channel == 9:  # batterie : ignorée
            continue

        key = (channel, d1)
        if kind == 0x90 and d2 > 0:
            active.setdefault(key, []).append((tick, d2))
        elif kind == 0x80 or (kind == 0x90 and d2 == 0):
            if active.get(key):
                start, velocity = active[key].pop(0)
                notes.append((start, max(tick, start + 1), d1, velocity))

    for (channel, pitch), starts in active.items():  # notes jamais relâchées
        for start, velocity in starts:
            notes.append((start, max(tick, start + 1), pitch, velocity))


def read_midi(path) -> dict:
    """Retourne {"ticks_per_beat", "tempo" (µs par noire), "notes": [(début, fin, hauteur, vélocité)]}.

    Les temps sont en « ticks » MIDI. Plusieurs pistes sont fusionnées en une seule liste.
    """
    data = Path(path).read_bytes()
    if data[:4] != b"MThd":
        raise ValueError("Ce n'est pas un fichier MIDI valide")
    header_len = struct.unpack(">I", data[4:8])[0]
    _, _, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError("Division temporelle SMPTE non prise en charge")

    pos = 8 + header_len
    notes, tempo = [], []
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        if chunk_id == b"MTrk":
            _parse_track(body, notes, tempo)

    notes.sort()
    return {"ticks_per_beat": division, "tempo": tempo[0] if tempo else 500000, "notes": notes}


def write_midi(path, notes, tempo_bpm: float = 100, ticks_per_beat: int = 480, program: int = 0):
    """Écrit un fichier MIDI (format 0, une piste).

    notes : liste de (début_en_temps, fin_en_temps, hauteur, vélocité) ; les temps sont en noires (beats).
    """
    events = []  # (tick, ordre, octets) ; ordre 0 = note off avant note on au même instant
    for start, end, pitch, velocity in notes:
        t0 = int(round(start * ticks_per_beat))
        t1 = max(int(round(end * ticks_per_beat)), t0 + 1)
        pitch, velocity = int(pitch), max(1, min(127, int(velocity)))
        events.append((t0, 1, bytes([0x90, pitch, velocity])))
        events.append((t1, 0, bytes([0x80, pitch, 0])))
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    track = bytearray()
    tempo = int(60_000_000 / tempo_bpm)
    track += _vlq(0) + b"\xFF\x51\x03" + tempo.to_bytes(3, "big")
    track += _vlq(0) + b"\xFF\x58\x04\x04\x02\x18\x08"            # mesure 4/4
    track += _vlq(0) + bytes([0xC0, program])                      # instrument
    last = 0
    for tick, _, raw in events:
        track += _vlq(tick - last) + raw
        last = tick
    track += _vlq(0) + b"\xFF\x2F\x00"                             # fin de piste

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks_per_beat)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(header + b"MTrk" + struct.pack(">I", len(track)) + bytes(track))
