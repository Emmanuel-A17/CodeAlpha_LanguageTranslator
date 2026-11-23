"""
Modèle LSTM (PyTorch) : lit une suite de tokens musicaux et prédit le suivant.

    tokens -> Embedding -> LSTM (x couches) -> Dropout -> Linear -> scores (logits) sur les 194 tokens

PyTorch n'est importé qu'ici : le reste du projet (chaîne de Markov, interface) fonctionne sans.
"""

import numpy as np

from .tokens import VOCAB_SIZE

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


def require_torch():
    if torch is None:
        raise RuntimeError("PyTorch n'est pas installé. Lancez : pip install torch")


def pick_device():
    require_torch()
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


if nn is not None:
    class MusicLSTM(nn.Module):
        def __init__(self, vocab_size=VOCAB_SIZE, embed=96, hidden=256, layers=2, dropout=0.25):
            super().__init__()
            self.config = dict(vocab_size=vocab_size, embed=embed, hidden=hidden, layers=layers, dropout=dropout)
            self.embedding = nn.Embedding(vocab_size, embed)
            self.lstm = nn.LSTM(embed, hidden, num_layers=layers, batch_first=True,
                                dropout=dropout if layers > 1 else 0.0)
            self.drop = nn.Dropout(dropout)
            self.out = nn.Linear(hidden, vocab_size)

        def forward(self, x, state=None):
            h, state = self.lstm(self.drop(self.embedding(x)), state)
            return self.out(self.drop(h)), state


class LSTMPredictor:
    """Même interface que MarkovPredictor : reset() puis step(token) -> logits (numpy)."""

    def __init__(self, model, device):
        self.model = model.to(device).eval()
        self.device = device
        self.state = None

    def reset(self):
        self.state = None

    def step(self, token: int) -> np.ndarray:
        with torch.no_grad():
            x = torch.tensor([[token]], dtype=torch.long, device=self.device)
            logits, self.state = self.model(x, self.state)
        return logits[0, -1].cpu().numpy().astype(np.float64)


def save_checkpoint(model, path, extra=None):
    require_torch()
    torch.save({"config": model.config, "state_dict": model.state_dict(), "extra": extra or {}}, path)


def load_checkpoint(path, device=None):
    require_torch()
    device = device or pick_device()
    data = torch.load(path, map_location=device)
    model = MusicLSTM(**data["config"])
    model.load_state_dict(data["state_dict"])
    return model.to(device).eval(), data.get("extra", {})
