"""
Modèle de référence : chaîne de Markov (n-grammes) sur les tokens.

Il apprend en une seconde, sans PyTorch, et sert de point de comparaison au LSTM :
il ne se souvient que des 4 derniers tokens, alors que le LSTM garde une mémoire plus longue.
"""

import numpy as np

from .tokens import VOCAB_SIZE


class MarkovModel:
    def __init__(self, token_lists, order: int = 4):
        self.order = order
        self.tables = [dict() for _ in range(order + 1)]   # tables[k][contexte de k tokens] -> {token: effectif}
        for tokens in token_lists:
            for i, token in enumerate(tokens):
                for k in range(0, order + 1):
                    if i - k < 0:
                        break
                    context = tuple(tokens[i - k:i])
                    counts = self.tables[k].setdefault(context, {})
                    counts[token] = counts.get(token, 0) + 1

    def predictor(self):
        return MarkovPredictor(self)


class MarkovPredictor:
    """Même interface que le LSTM : reset() puis step(token) -> logits sur tout le vocabulaire."""

    def __init__(self, model: MarkovModel):
        self.model = model
        self.history = []

    def reset(self):
        self.history = []

    def step(self, token: int) -> np.ndarray:
        self.history.append(token)
        probs = np.full(VOCAB_SIZE, 1e-6)
        for k in range(0, self.model.order + 1):
            if k > len(self.history):
                break
            context = tuple(self.history[len(self.history) - k:]) if k else ()
            counts = self.model.tables[k].get(context)
            if not counts:
                continue
            total = sum(counts.values())
            weight = (k + 1) ** 2            # les contextes longs comptent davantage
            for t, c in counts.items():
                probs[t] += weight * c / total
        return np.log(probs / probs.sum())
