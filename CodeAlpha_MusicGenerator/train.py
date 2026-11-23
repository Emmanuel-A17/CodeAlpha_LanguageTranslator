"""
Étape 2 — Entraîner le modèle.

    python train.py                       # LSTM (nécessite PyTorch), enregistré dans models/lstm.pt
    python train.py --epochs 40 --hidden 384
    python train.py --markov-only         # modèle de référence sans PyTorch, enregistré dans models/markov.pkl

Le LSTM apprend à prédire le token suivant (entropie croisée) sur des fenêtres de --seq tokens.
Le meilleur modèle selon la perte de validation est conservé (arrêt anticipé).
"""

import argparse
import pickle
import time
from pathlib import Path

import numpy as np

from musicai.dataset import build_training_data, load_pieces, pieces_to_token_lists, AUGMENT_SHIFTS
from musicai.markov import MarkovModel

ROOT = Path(__file__).parent
MODELS = ROOT / "models"


def train_markov(data_dir):
    pieces = load_pieces(data_dir, log=print)
    model = MarkovModel(pieces_to_token_lists(pieces, AUGMENT_SHIFTS))
    MODELS.mkdir(exist_ok=True)
    with open(MODELS / "markov.pkl", "wb") as f:
        pickle.dump(model, f)
    print(f"Modèle de Markov enregistré : {MODELS / 'markov.pkl'} ({len(pieces)} morceaux)")


def make_batches(stream, seq, batch, rng):
    """Fenêtres aléatoires : entrée = tokens[i:i+seq], cible = tokens[i+1:i+seq+1]."""
    starts = rng.integers(0, len(stream) - seq - 1, size=batch)
    x = np.stack([stream[s:s + seq] for s in starts])
    y = np.stack([stream[s + 1:s + seq + 1] for s in starts])
    return x, y


def train_lstm(args):
    try:
        import torch
        from torch import nn
    except ImportError:
        raise SystemExit("PyTorch n'est pas installé. Lancez : pip install torch\n"
                         "(ou utilisez  python train.py --markov-only  pour le modèle de référence)")
    from musicai.lstm import MusicLSTM, pick_device, save_checkpoint

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = pick_device()
    data = build_training_data(args.data, augment=not args.no_augment, limit=args.limit)
    train, val = data["train"], data["val"]
    print(f"{data['pieces']} morceaux ({data['train_pieces']} entraînement / {data['val_pieces']} validation), "
          f"{data['train_tokens']} tokens d'entraînement, appareil : {device}")
    if len(train) < args.seq * 4:
        raise SystemExit("Pas assez de données pour cette longueur de séquence. Ajoutez des MIDI ou baissez --seq.")

    model = MusicLSTM(embed=args.embed, hidden=args.hidden, layers=args.layers, dropout=args.dropout).to(device)
    print(f"{sum(p.numel() for p in model.parameters()):,} paramètres")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    loss_fn = nn.CrossEntropyLoss()
    steps = max(1, len(train) // (args.seq * args.batch))   # ~ un passage complet des données par époque

    def validation_loss():
        if val is None or len(val) < args.seq + 2:
            return None
        model.eval()
        losses = []
        with torch.no_grad():
            for i in range(0, len(val) - args.seq - 1, args.seq):
                x = torch.tensor(val[i:i + args.seq][None], device=device)
                y = torch.tensor(val[i + 1:i + args.seq + 1][None], device=device)
                logits, _ = model(x)
                losses.append(loss_fn(logits[0], y[0]).item())
        return float(np.mean(losses)) if losses else None

    best, bad, start = float("inf"), 0, time.time()
    MODELS.mkdir(exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for _ in range(steps):
            x, y = make_batches(train, args.seq, args.batch, rng)
            x, y = torch.tensor(x, device=device), torch.tensor(y, device=device)
            logits, _ = model(x)
            loss = loss_fn(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += loss.item()
        scheduler.step()
        train_loss, val_loss = total / steps, validation_loss()
        score = val_loss if val_loss is not None else train_loss
        note = ""
        if score < best - 1e-4:
            best, bad, note = score, 0, "  ✓ meilleur"
            save_checkpoint(model, MODELS / "lstm.pt", {"epoch": epoch, "loss": best, "pieces": data["pieces"]})
        else:
            bad += 1
        val_text = f" | validation {val_loss:.3f}" if val_loss is not None else ""
        print(f"Époque {epoch:3d}/{args.epochs} | entraînement {train_loss:.3f}{val_text} | {time.time() - start:.0f}s{note}")
        if bad >= args.patience:
            print("Arrêt anticipé : plus d'amélioration.")
            break
    print(f"Terminé. Meilleure perte : {best:.3f} -> {MODELS / 'lstm.pt'}")
    train_markov(args.data)   # le modèle de référence est entraîné aussi, pour comparer


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(ROOT / "data" / "midi"))
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--seq", type=int, default=128, help="longueur des fenêtres d'entraînement (tokens)")
    p.add_argument("--embed", type=int, default=96)
    p.add_argument("--hidden", type=int, default=256)
    p.add_argument("--layers", type=int, default=2)
    p.add_argument("--dropout", type=float, default=0.25)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--patience", type=int, default=6)
    p.add_argument("--limit", type=int, default=None, help="nombre maximum de fichiers MIDI lus")
    p.add_argument("--no-augment", action="store_true", help="désactive la transposition dans les 12 tonalités")
    p.add_argument("--markov-only", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    if args.markov_only:
        train_markov(args.data)
    else:
        train_lstm(args)


if __name__ == "__main__":
    main()
