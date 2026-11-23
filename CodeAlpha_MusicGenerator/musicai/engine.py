"""Chargement des modèles disponibles et génération d'un morceau complet (MIDI + WAV + notes)."""

import pickle
import time
import uuid
from pathlib import Path

from .midi_io import write_midi
from .sampler import generate_notes
from .synth import render_wav

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUTPUTS = ROOT / "outputs"

MODEL_LABELS = {"lstm": "LSTM (réseau de neurones)", "markov": "Chaîne de Markov (référence)"}


class Engine:
    def __init__(self):
        self.predictors = {}
        self.info = {}
        self._load()

    def _load(self):
        markov = MODELS / "markov.pkl"
        if markov.exists():
            with open(markov, "rb") as f:
                self.predictors["markov"] = pickle.load(f).predictor()
        lstm = MODELS / "lstm.pt"
        if lstm.exists():
            try:
                from .lstm import LSTMPredictor, load_checkpoint, pick_device
                model, extra = load_checkpoint(lstm)
                self.predictors["lstm"] = LSTMPredictor(model, pick_device())
                self.info["lstm"] = extra
            except Exception as exc:  # PyTorch absent ou fichier illisible
                self.info["lstm_error"] = str(exc)

    def available(self):
        return [{"id": k, "label": MODEL_LABELS[k]} for k in ("lstm", "markov") if k in self.predictors]

    def generate(self, model="lstm", seconds=20, tempo=100, temperature=0.9, top_k=30, polyphony=6, seed=None):
        if model not in self.predictors:
            raise ValueError("Modèle indisponible. Lancez python train.py")
        seconds = min(max(float(seconds), 5), 90)
        tempo = min(max(float(tempo), 50), 180)
        notes, tokens = generate_notes(self.predictors[model], seconds, tempo,
                                       temperature=float(temperature), top_k=int(top_k),
                                       max_polyphony=int(polyphony), seed=seed)
        if not notes:
            raise RuntimeError("Aucune note générée, réessayez.")
        stamp = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        OUTPUTS.mkdir(exist_ok=True)
        beat = tempo / 60.0
        write_midi(OUTPUTS / f"{stamp}.mid", [(s * beat, e * beat, p, 80) for s, e, p in notes], tempo_bpm=tempo)
        render_wav([(s, e, p, 80) for s, e, p in notes], OUTPUTS / f"{stamp}.wav")
        return {
            "id": stamp, "model": model, "tempo": tempo, "duration": max(e for _, e, _ in notes),
            "notes": [[round(s, 3), round(e, 3), p] for s, e, p in notes],
            "midi": f"/outputs/{stamp}.mid", "wav": f"/outputs/{stamp}.wav",
        }
