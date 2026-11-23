"""
Représentation de la musique sous forme de « mots » (tokens) pour le réseau de neurones.

Comme un texte est une suite de mots, un morceau devient une suite d'événements :

    NOTE_ON(60)  NOTE_ON(64)  TIME_SHIFT(4)  NOTE_OFF(60)  NOTE_OFF(64)  TIME_SHIFT(2) ...

- NOTE_ON(p)   : la note p commence          (88 touches de piano : 21 à 108)
- NOTE_OFF(p)  : la note p s'arrête
- TIME_SHIFT(n): le temps avance de n pas    (1 pas = 1/4 de noire = une double-croche)
- BOS / EOS    : début / fin d'un morceau

Cette représentation gère plusieurs notes simultanées (accords, plusieurs voix)
avec un vocabulaire de seulement 194 mots.
"""

STEPS_PER_BEAT = 4
LOW, HIGH = 21, 108                 # plage de hauteurs MIDI retenue (piano)
N_PITCHES = HIGH - LOW + 1          # 88
MAX_SHIFT = 16                      # un TIME_SHIFT dure au plus 16 pas (4 noires)

BOS, EOS = 0, 1
NOTE_ON0 = 2
NOTE_OFF0 = NOTE_ON0 + N_PITCHES    # 90
SHIFT0 = NOTE_OFF0 + N_PITCHES      # 178
VOCAB_SIZE = SHIFT0 + MAX_SHIFT     # 194


def note_on(pitch: int) -> int:
    return NOTE_ON0 + pitch - LOW


def note_off(pitch: int) -> int:
    return NOTE_OFF0 + pitch - LOW


def time_shift(steps: int) -> int:
    return SHIFT0 + steps - 1


def describe(token: int):
    """Token -> ('on', hauteur) | ('off', hauteur) | ('shift', pas) | ('bos'|'eos', None)."""
    if token == BOS:
        return "bos", None
    if token == EOS:
        return "eos", None
    if NOTE_ON0 <= token < NOTE_OFF0:
        return "on", token - NOTE_ON0 + LOW
    if NOTE_OFF0 <= token < SHIFT0:
        return "off", token - NOTE_OFF0 + LOW
    if SHIFT0 <= token < VOCAB_SIZE:
        return "shift", token - SHIFT0 + 1
    raise ValueError(f"token inconnu : {token}")


def _clean(notes):
    """Garde les notes dans la plage du piano et évite deux notes identiques qui se chevauchent."""
    by_pitch = {}
    for start, end, pitch in notes:
        if LOW <= pitch <= HIGH:
            by_pitch.setdefault(pitch, []).append([start, max(end, start + 1)])
    cleaned = []
    for pitch, items in by_pitch.items():
        items.sort()
        for k, (start, end) in enumerate(items):
            if k + 1 < len(items) and items[k + 1][0] < end:
                end = items[k + 1][0]
            if end > start:
                cleaned.append((start, end, pitch))
    return cleaned


def notes_to_tokens(notes):
    """Liste de notes (début_pas, fin_pas, hauteur) -> liste de tokens (avec BOS et EOS)."""
    events = []
    for start, end, pitch in _clean(notes):
        events.append((start, 1, pitch))   # note on
        events.append((end, 0, pitch))     # note off (traité avant les « on » au même instant)
    events.sort()

    tokens, current = [BOS], 0
    for step, kind, pitch in events:
        gap = step - current
        while gap > 0:
            shift = min(gap, MAX_SHIFT)
            tokens.append(time_shift(shift))
            gap -= shift
            current += shift
        tokens.append(note_on(pitch) if kind == 1 else note_off(pitch))
    tokens.append(EOS)
    return tokens


def tokens_to_notes(tokens, max_step=None):
    """Liste de tokens -> liste de notes (début_pas, fin_pas, hauteur). Tolère les séquences invalides."""
    notes, sounding, step = [], {}, 0
    for token in tokens:
        kind, value = describe(int(token))
        if kind == "shift":
            step += value
        elif kind == "on" and value not in sounding:
            sounding[value] = step
        elif kind == "off" and value in sounding:
            start = sounding.pop(value)
            if step > start:
                notes.append((start, step, value))
    end_of_piece = step if max_step is None else min(step, max_step)
    for pitch, start in sounding.items():   # notes encore tenues à la fin
        if end_of_piece > start:
            notes.append((start, end_of_piece, pitch))
    if max_step is not None:
        notes = [(s, min(e, max_step), p) for s, e, p in notes if s < max_step]
    return sorted(notes)


def transpose_notes(notes, semitones: int):
    return [(s, e, p + semitones) for s, e, p in notes]
