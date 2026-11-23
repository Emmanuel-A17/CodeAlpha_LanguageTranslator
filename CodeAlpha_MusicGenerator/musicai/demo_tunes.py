"""
Petit jeu de données de démonstration : mélodies traditionnelles / du domaine public,
transcrites de façon simplifiée, avec un accompagnement ajouté automatiquement
(basse + accords choisis selon la mélodie de chaque mesure).

Il sert à faire fonctionner le projet tout de suite. Pour de bons résultats, entraînez
le modèle sur de vrais fichiers MIDI (voir README et collect_data.py).

Notation de la mélodie :  "E4:1.5 D4:0.5 R:1"   (hauteur:durée en noires ; R = silence ; durée 1 par défaut)
"""

import re
from pathlib import Path

from .midi_io import write_midi

# nom : (tonique, mode, noires par mesure, tempo, noires d'anacrouse, mélodie)
TUNES = {
    "ode_a_la_joie": (0, "major", 4, 108, 0,
        "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 E4:1.5 D4:.5 D4:2 "
        "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 D4:1.5 C4:.5 C4:2 "
        "D4 D4 E4 C4 D4 E4:.5 F4:.5 E4 C4 D4 E4:.5 F4:.5 E4 D4 C4 D4 G3:2 "
        "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 D4:1.5 C4:.5 C4:2"),
    "twinkle_twinkle": (0, "major", 4, 100, 0,
        "C4 C4 G4 G4 A4 A4 G4:2 F4 F4 E4 E4 D4 D4 C4:2 G4 G4 F4 F4 E4 E4 D4:2 "
        "G4 G4 F4 F4 E4 E4 D4:2 C4 C4 G4 G4 A4 A4 G4:2 F4 F4 E4 E4 D4 D4 C4:2"),
    "frere_jacques": (0, "major", 4, 120, 0,
        "C4 D4 E4 C4 C4 D4 E4 C4 E4 F4 G4:2 E4 F4 G4:2 "
        "G4:.5 A4:.5 G4:.5 F4:.5 E4 C4 G4:.5 A4:.5 G4:.5 F4:.5 E4 C4 C4 G3 C4:2 C4 G3 C4:2"),
    "au_clair_de_la_lune": (0, "major", 4, 96, 0,
        "C4 C4 C4 D4 E4:2 D4:2 C4 E4 D4 D4 C4:4 C4 C4 C4 D4 E4:2 D4:2 C4 E4 D4 D4 C4:4 "
        "D4 D4 D4 D4 A3:2 A3:2 D4 C4 B3 A3 G3:4 C4 C4 C4 D4 E4:2 D4:2 C4 E4 D4 D4 C4:4"),
    "menuet_en_sol": (7, "major", 3, 120, 0,
        "D5 G4:.5 A4:.5 B4:.5 C5:.5 D5 G4 G4 E5 C5:.5 D5:.5 E5:.5 F#5:.5 G5 G4 G4 "
        "C5 D5:.5 C5:.5 B4:.5 A4:.5 B4 C5:.5 B4:.5 A4:.5 G4:.5 F#4 G4:.5 A4:.5 B4 G4:3"),
    "greensleeves": (9, "minor", 3, 100, 1,
        "A4:1 C5:2 D5 E5:1.5 F5:.5 E5 D5:2 B4 G4:1.5 A4:.5 B4 C5:2 A4 A4:1.5 G#4:.5 A4 B4:2 G#4 E4:2 A4 "
        "C5:2 D5 E5:1.5 F5:.5 E5 D5:2 B4 G4:1.5 A4:.5 B4 C5:1.5 B4:.5 A4 G#4:1.5 F#4:.5 G#4 A4:3"),
    "jingle_bells": (0, "major", 4, 120, 0,
        "E4 E4 E4:2 E4 E4 E4:2 E4 G4 C4:1.5 D4:.5 E4:4 F4 F4 F4:1.5 F4:.5 F4 E4 E4 E4:.5 E4:.5 "
        "E4 D4 D4 E4 D4:2 G4:2 C4:4"),
    "amazing_grace": (7, "major", 3, 80, 1,
        "D4:1 G4:2 B4:.5 G4:.5 B4:2 A4 G4:2 E4 D4:2 D4 G4:2 B4:.5 G4:.5 B4:2 A4 D5:3 "
        "D5:2 B4:.5 D5:.5 B4:2 G4 E4:2 D4:.5 E4:.5 G4:2 E4 D4:2 D4 G4:2 B4:.5 G4:.5 B4:2 A4 G4:3"),
    "auld_lang_syne": (7, "major", 4, 90, 1,
        "D4:1 G4:1.5 G4:.5 G4 B4 A4:1.5 G4:.5 A4 B4:.5 A4:.5 G4:1.5 G4:.5 B4 D5 E5:4 "
        "E5:1.5 D5:.5 D5 B4 G4:1.5 G4:.5 B4 A4:.5 G4:.5 A4:1.5 G4:.5 A4 B4 G4:4"),
    "pour_elise": (9, "minor", 3, 120, 1,
        "E5:.5 D#5:.5 E5:.5 D#5:.5 E5:.5 B4:.5 D5:.5 C5:.5 A4:2 A4:1 C4:.5 E4:.5 A4 B4:1 E4:.5 G#4:.5 B4 "
        "C5:1 E4:.5 E5:.5 D#5:.5 E5:.5 D#5:.5 E5:.5 B4:.5 D5:.5 C5:.5 A4:2 A4:1 C4:.5 E4:.5 A4 "
        "B4:1 E4:.5 C5:.5 B4 A4:3"),
}

_NOTE = re.compile(r"^([A-G])([#b]?)(-?\d)$")
_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_name_to_midi(name: str) -> int:
    letter, accidental, octave = _NOTE.match(name).groups()
    return 12 * (int(octave) + 1) + _SEMITONE[letter] + (1 if accidental == "#" else -1 if accidental == "b" else 0)


def parse_melody(text: str):
    """'E4:1.5 R:1' -> [(début, fin, hauteur)] en noires."""
    notes, t = [], 0.0
    for token in text.split():
        name, _, dur = token.partition(":")
        duration = float(dur) if dur else 1.0
        if name != "R":
            notes.append((t, t + duration, note_name_to_midi(name)))
        t += duration
    return notes


def _chords(tonic: int, mode: str):
    """Accords de la tonalité : (racine, intervalles), avec un petit bonus de préférence."""
    major, minor = (0, 4, 7), (0, 3, 7)
    if mode == "major":
        chords = [(tonic, major, 0.3), (tonic + 2, minor, 0), (tonic + 4, minor, 0),
                  (tonic + 5, major, 0.15), (tonic + 7, major, 0.15), (tonic + 9, minor, 0)]
    else:
        chords = [(tonic, minor, 0.3), (tonic + 5, minor, 0.1), (tonic + 7, major, 0.15),
                  (tonic + 8, major, 0), (tonic + 3, major, 0), (tonic + 10, major, 0)]
    return [(root % 12, intervals, bonus) for root, intervals, bonus in chords]


def _best_chord(melody, bar_start, bar_end, chords):
    best, best_score = chords[0], -1.0
    for root, intervals, bonus in chords:
        pcs = {(root + i) % 12 for i in intervals}
        score = bonus
        for start, end, pitch in melody:
            overlap = min(end, bar_end) - max(start, bar_start)
            if overlap > 0 and pitch % 12 in pcs:
                score += overlap + (1.0 if start <= bar_start + 0.01 else 0.0)
        if score > best_score:
            best, best_score = (root, intervals), score
    return best


def tune_notes(tune):
    """Mélodie + accompagnement -> [(début, fin, hauteur, vélocité)] en noires."""
    tonic, mode, per_bar, _, pickup, text = tune
    melody = parse_melody(text)
    total = max(end for _, end, _ in melody)
    chords = _chords(tonic, mode)

    notes = [(s, e, p, 90) for s, e, p in melody]
    bar_start = float(pickup)
    while bar_start < total - 0.01:
        bar_end = bar_start + per_bar
        root, intervals = _best_chord(melody, bar_start, bar_end, chords)
        bass = 36 + root                                           # basse entre 36 et 47
        triad = [55 + ((root + i - 55) % 12) for i in intervals]   # accord entre 55 et 66
        if per_bar == 3:                                           # valse : basse, accord, accord
            notes.append((bar_start, bar_start + 1, bass, 70))
            for beat in (1, 2):
                notes += [(bar_start + beat, bar_start + beat + 0.9, p, 55) for p in triad]
        else:                                                      # 4 temps : basse sur 1 et 3, accords sur 2 et 4
            notes.append((bar_start, bar_start + 2, bass, 70))
            notes.append((bar_start + 2, bar_start + 4, bass + 7, 65))
            for beat in (1, 3):
                notes += [(bar_start + beat, bar_start + beat + 0.9, p, 55) for p in triad]
        bar_start = bar_end
    return notes


def write_demo_files(folder) -> list:
    """Écrit les morceaux de démonstration en .mid dans `folder`. Retourne les chemins créés."""
    folder = Path(folder)
    paths = []
    for name, tune in TUNES.items():
        path = folder / f"{name}.mid"
        write_midi(path, tune_notes(tune), tempo_bpm=tune[3])
        paths.append(path)
    return paths
