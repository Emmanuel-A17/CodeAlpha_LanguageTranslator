"""
Collecte et prétraitement des données : dossier de fichiers MIDI -> séquences de tokens.

    .mid  ->  notes (début, fin, hauteur)  ->  tokens  ->  grand flux d'entiers pour l'entraînement
"""

from pathlib import Path

import numpy as np

from .midi_io import read_midi
from .tokens import STEPS_PER_BEAT, notes_to_tokens, transpose_notes

AUGMENT_SHIFTS = list(range(-5, 7))   # transpositions de -5 à +6 demi-tons (12 tonalités)
MIN_NOTES = 8                         # on ignore les fichiers presque vides


def load_midi_notes(path):
    """Fichier .mid -> [(début_pas, fin_pas, hauteur)], temps quantifiés à la double-croche."""
    midi = read_midi(path)
    per_beat = midi["ticks_per_beat"]
    notes = []
    for start, end, pitch, _ in midi["notes"]:
        s = int(round(start / per_beat * STEPS_PER_BEAT))
        e = int(round(end / per_beat * STEPS_PER_BEAT))
        notes.append((s, max(e, s + 1), pitch))
    return notes


def load_pieces(folder, limit=None, log=None):
    """Lit tous les .mid / .midi d'un dossier. Retourne [{"name", "notes"}]."""
    folder = Path(folder)
    files = sorted(list(folder.rglob("*.mid")) + list(folder.rglob("*.midi")))
    pieces, skipped = [], 0
    for path in files:
        if limit and len(pieces) >= limit:
            break
        try:
            notes = load_midi_notes(path)
        except Exception as exc:  # fichier abîmé ou format non géré
            skipped += 1
            if log:
                log(f"  ignoré : {path.name} ({exc})")
            continue
        if len(notes) < MIN_NOTES:
            skipped += 1
            continue
        pieces.append({"name": path.stem, "notes": notes})
    if log and skipped:
        log(f"  {skipped} fichier(s) ignoré(s)")
    return pieces


def pieces_to_token_lists(pieces, shifts=(0,)):
    """Chaque pièce (et chaque transposition) devient une liste de tokens [BOS, ..., EOS]."""
    out = []
    for piece in pieces:
        for shift in shifts:
            tokens = notes_to_tokens(transpose_notes(piece["notes"], shift) if shift else piece["notes"])
            if len(tokens) > 10:
                out.append(tokens)
    return out


def to_stream(token_lists) -> np.ndarray:
    """Concatène les morceaux en un seul flux d'entiers."""
    if not token_lists:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate([np.asarray(t, dtype=np.int64) for t in token_lists])


def split_pieces(pieces, val_fraction=0.1, seed=0):
    """Sépare entraînement / validation par morceau (jamais deux transpositions d'une même pièce de part et d'autre)."""
    if len(pieces) < 8 or val_fraction <= 0:
        return pieces, []
    order = np.random.default_rng(seed).permutation(len(pieces))
    n_val = max(1, int(round(len(pieces) * val_fraction)))
    val_idx = set(order[:n_val].tolist())
    train = [p for i, p in enumerate(pieces) if i not in val_idx]
    val = [p for i, p in enumerate(pieces) if i in val_idx]
    return train, val


def build_training_data(folder, augment=True, val_fraction=0.1, limit=None, log=print):
    """Pipeline complet. Retourne un dictionnaire avec les flux d'entraînement / validation et des statistiques."""
    pieces = load_pieces(folder, limit=limit, log=log)
    if not pieces:
        raise RuntimeError(f"Aucun fichier MIDI exploitable dans « {folder} ». Lancez : python collect_data.py --demo")
    train_pieces, val_pieces = split_pieces(pieces, val_fraction)
    shifts = AUGMENT_SHIFTS if augment else (0,)
    train_stream = to_stream(pieces_to_token_lists(train_pieces, shifts))
    val_stream = to_stream(pieces_to_token_lists(val_pieces, (0,)))
    return {
        "train": train_stream,
        "val": val_stream if len(val_stream) > 0 else None,
        "pieces": len(pieces),
        "train_pieces": len(train_pieces),
        "val_pieces": len(val_pieces),
        "train_tokens": int(len(train_stream)),
        "augmented": bool(augment),
    }
