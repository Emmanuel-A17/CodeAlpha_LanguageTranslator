"""
Génération : on demande au modèle « quel est le prochain événement ? », on tire au sort selon ses
probabilités, et on recommence. Le même code sert pour le LSTM et pour la chaîne de Markov.

Des règles simples gardent la musique valide :
  - on ne peut arrêter qu'une note qui sonne, et on ne peut jouer qu'une note qui ne sonne pas déjà ;
  - le nombre de notes simultanées est limité ;
  - un long silence est interdit.
"""

import numpy as np

from .tokens import (BOS, EOS, N_PITCHES, NOTE_OFF0, NOTE_ON0, SHIFT0, STEPS_PER_BEAT, VOCAB_SIZE,
                     describe, note_off, note_on, tokens_to_notes)

MAX_SILENCE_STEPS = 8
MAX_HOLD_STEPS = 32      # une note ne dure pas plus de 8 noires


def generate_tokens(predictor, target_steps: int, temperature: float = 1.0, top_k: int = 30,
                    max_polyphony: int = 6, seed=None):
    """Génère des tokens jusqu'à atteindre `target_steps` pas de temps (1 pas = 1/4 de noire)."""
    rng = np.random.default_rng(seed)
    temperature = max(float(temperature), 0.05)
    predictor.reset()

    tokens = [BOS]
    logits = predictor.step(BOS)
    sounding, elapsed, silent_run = set(), 0, 0
    started = {}
    max_tokens = target_steps * 10 + 200

    while elapsed < target_steps and len(tokens) < max_tokens:
        allowed = np.zeros(VOCAB_SIZE, dtype=bool)
        allowed[SHIFT0:] = True                                    # les silences / avances de temps
        if len(sounding) < max_polyphony:
            allowed[NOTE_ON0:NOTE_ON0 + N_PITCHES] = True
        for pitch in sounding:
            allowed[note_on(pitch)] = False                        # déjà en train de sonner
            allowed[note_off(pitch)] = True
        allowed[BOS] = allowed[EOS] = False
        if not sounding and silent_run >= MAX_SILENCE_STEPS:       # pas de silence interminable
            allowed[SHIFT0:] = False

        for pitch in list(sounding):                               # on coupe les notes trop longues
            if elapsed - started[pitch] >= MAX_HOLD_STEPS:
                allowed[:] = False
                allowed[note_off(pitch)] = True
                break

        scores = np.where(allowed, logits / temperature, -np.inf)
        if top_k and top_k < allowed.sum():
            threshold = np.sort(scores)[-top_k]
            scores = np.where(scores >= threshold, scores, -np.inf)
        scores -= scores.max()
        probs = np.exp(scores)
        probs /= probs.sum()
        token = int(rng.choice(VOCAB_SIZE, p=probs))

        kind, value = describe(token)
        if kind == "on":
            sounding.add(value)
            started[value] = elapsed
            silent_run = 0
        elif kind == "off":
            sounding.discard(value)
        elif kind == "shift":
            elapsed += value
            silent_run = silent_run + value if not sounding else 0
        tokens.append(token)
        logits = predictor.step(token)
    return tokens


def generate_notes(predictor, seconds: float, tempo_bpm: float, **kwargs):
    """Retourne les notes générées en secondes : [(début_s, fin_s, hauteur)]."""
    step_seconds = 60.0 / tempo_bpm / STEPS_PER_BEAT
    target_steps = max(8, int(round(seconds / step_seconds)))
    tokens = generate_tokens(predictor, target_steps, **kwargs)
    notes = tokens_to_notes(tokens, max_step=target_steps)
    return [(s * step_seconds, e * step_seconds, p) for s, e, p in notes], tokens
