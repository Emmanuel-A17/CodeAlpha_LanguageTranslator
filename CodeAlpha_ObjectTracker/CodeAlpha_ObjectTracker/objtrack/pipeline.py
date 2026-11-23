"""Boucle principale : image -> détection -> suivi -> dessin. Utilisée par track.py (fenêtre) et app.py (navigateur)."""

import time
from collections import Counter, defaultdict, deque

import cv2

from .draw import draw_hud, draw_tracks
from .sort import KalmanBox, Sort


def open_source(source):
    """'0' / '1' = webcam ; sinon chemin d'un fichier vidéo."""
    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else str(source))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la source vidéo : {source}")
    return cap


def run(cap, detector, detect_every=1, max_width=960, trail_length=30, stop=lambda: False):
    """Générateur : donne (image annotée, statistiques) pour chaque image de la vidéo."""
    KalmanBox._next_id = 0
    tracker = Sort()
    trails = defaultdict(lambda: deque(maxlen=trail_length))
    seen = {}                      # id -> classe : objets distincts rencontrés
    last_dets, index = [], 0
    fps, previous = 0.0, time.perf_counter()

    while not stop():
        ok, frame = cap.read()
        if not ok:
            break
        if max_width and frame.shape[1] > max_width:
            scale = max_width / frame.shape[1]
            frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        if index % detect_every == 0:                      # on peut ne détecter qu'une image sur N pour aller plus vite
            last_dets = [(x1, y1, x2, y2, s, name) for x1, y1, x2, y2, s, name in detector.detect(frame)]
            tracks = tracker.update(last_dets)
        else:
            tracks = tracker.update([])
        index += 1

        for x1, y1, x2, y2, tid, label, _ in tracks:
            trails[tid].append((int((x1 + x2) / 2), int(y2)))
            seen[tid] = label

        now = time.perf_counter()
        fps = 0.9 * fps + 0.1 / max(now - previous, 1e-6) if fps else 1 / max(now - previous, 1e-6)
        previous = now

        annotated = draw_hud(draw_tracks(frame, tracks, trails), fps, len(tracks))
        stats = {"fps": round(fps, 1), "visible": Counter(t[5] for t in tracks), "total": Counter(seen.values()),
                 "frame": index}
        yield annotated, stats
