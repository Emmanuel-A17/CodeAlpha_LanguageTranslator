"""
Détection et suivi d'objets en temps réel (fenêtre OpenCV).

    python track.py                       # webcam
    python track.py --source video.mp4    # fichier vidéo
    python track.py --source video.mp4 --save sortie.mp4
    python track.py --classes person car --conf 0.5 --every 2

Touches : q ou Échap pour quitter.
"""

import argparse

import cv2

from objtrack.detector import YoloDetector
from objtrack.pipeline import open_source, run


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default="0", help="0 = webcam, ou chemin d'un fichier vidéo")
    p.add_argument("--conf", type=float, default=0.4, help="seuil de confiance (0-1)")
    p.add_argument("--every", type=int, default=1, help="détecter une image sur N (2 = deux fois plus rapide)")
    p.add_argument("--classes", nargs="*", help="ne suivre que ces classes, ex. person car dog")
    p.add_argument("--save", help="enregistrer la vidéo annotée (ex. sortie.mp4)")
    p.add_argument("--no-window", action="store_true", help="n'affiche pas de fenêtre")
    args = p.parse_args()

    detector = YoloDetector(conf=args.conf, classes=args.classes)
    cap = open_source(args.source)
    writer = None
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 25

    for frame, stats in run(cap, detector, detect_every=args.every):
        if args.save and writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), fps_in, (w, h))
        if writer:
            writer.write(frame)
        if not args.no_window:
            cv2.imshow("Suivi d'objets — q pour quitter", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break

    cap.release()
    if writer:
        writer.release()
        print(f"Vidéo enregistrée : {args.save}")
    cv2.destroyAllWindows()
    try:
        print("Objets distincts suivis :", dict(stats["total"]))
    except NameError:
        pass


if __name__ == "__main__":
    main()
