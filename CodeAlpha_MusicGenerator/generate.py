"""
Étape 3 — Générer de la musique en ligne de commande (sans l'interface web).

    python generate.py                          # 20 s avec le LSTM si disponible, sinon Markov
    python generate.py --model markov --seconds 30 --tempo 120 --temperature 1.0 --seed 7

Crée un fichier .mid (à ouvrir dans un logiciel de musique) et un .wav (à écouter) dans outputs/.
"""

import argparse

from musicai.engine import Engine


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", choices=["lstm", "markov"], default=None)
    p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--tempo", type=float, default=100)
    p.add_argument("--temperature", type=float, default=0.9, help="bas = prudent, haut = audacieux")
    p.add_argument("--top-k", type=int, default=30)
    p.add_argument("--polyphony", type=int, default=6)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    engine = Engine()
    available = [m["id"] for m in engine.available()]
    if not available:
        raise SystemExit("Aucun modèle entraîné. Lancez d'abord : python collect_data.py --demo puis python train.py")
    model = args.model or available[0]
    result = engine.generate(model, args.seconds, args.tempo, args.temperature, args.top_k, args.polyphony, args.seed)
    print(f"{len(result['notes'])} notes générées avec « {model} » ({result['duration']:.1f} s)")
    print(f"  MIDI : outputs/{result['id']}.mid\n  WAV  : outputs/{result['id']}.wav")


if __name__ == "__main__":
    main()
