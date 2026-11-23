"""
Étape 1 — Collecter les données MIDI.

    python collect_data.py --demo          # 10 mélodies de démonstration (immédiat, sans internet)
    python collect_data.py --bach          # corpus de Bach de music21 (centaines de chorals, nécessite : pip install music21)
    python collect_data.py --from DOSSIER  # copie vos propres fichiers .mid dans data/midi
"""

import argparse
import shutil
from pathlib import Path

from musicai.demo_tunes import write_demo_files

DATA = Path(__file__).parent / "data" / "midi"


def collect_bach(limit):
    try:
        from music21 import corpus
    except ImportError:
        raise SystemExit("music21 n'est pas installé. Lancez : pip install music21")
    DATA.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in corpus.getComposer("bach"):
        if limit and count >= limit:
            break
        try:
            score = corpus.parse(path)
            score.write("midi", fp=str(DATA / f"bach_{count:03d}.mid"))
            count += 1
        except Exception as exc:
            print(f"  ignoré : {path} ({exc})")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="écrit les mélodies de démonstration")
    parser.add_argument("--bach", action="store_true", help="exporte le corpus de Bach de music21")
    parser.add_argument("--from", dest="source", help="dossier contenant vos fichiers .mid")
    parser.add_argument("--limit", type=int, default=0, help="nombre maximum de fichiers (Bach)")
    args = parser.parse_args()

    if not (args.demo or args.bach or args.source):
        parser.print_help()
        return

    DATA.mkdir(parents=True, exist_ok=True)
    if args.demo:
        paths = write_demo_files(DATA)
        print(f"{len(paths)} morceaux de démonstration écrits dans {DATA}")
    if args.bach:
        print("Export du corpus de Bach (peut prendre une minute)…")
        print(f"{collect_bach(args.limit)} morceaux de Bach écrits dans {DATA}")
    if args.source:
        files = [p for p in Path(args.source).rglob("*") if p.suffix.lower() in (".mid", ".midi")]
        for p in files:
            shutil.copy(p, DATA / p.name)
        print(f"{len(files)} fichiers copiés dans {DATA}")


if __name__ == "__main__":
    main()
