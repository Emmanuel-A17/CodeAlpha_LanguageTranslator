"""Dessin des boîtes, étiquettes et identifiants de suivi."""

import colorsys

import cv2


def color_for(track_id):
    hue = (track_id * 0.137) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 1.0)
    return int(b * 255), int(g * 255), int(r * 255)           # OpenCV travaille en BGR


def draw_tracks(frame, tracks, trails=None):
    """tracks : [(x1, y1, x2, y2, id, classe, score)]. trails : dict id -> liste de centres (dessine la trajectoire)."""
    for x1, y1, x2, y2, tid, label, score in tracks:
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        color = color_for(tid)
        if trails and len(trails.get(tid, [])) > 1:
            pts = list(trails[tid])
            for a, b in zip(pts[:-1], pts[1:]):
                cv2.line(frame, a, b, color, 2, cv2.LINE_AA)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        text = f"#{tid} {label} {int(score * 100)}%"
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        top = max(y1 - th - base - 6, 0)
        cv2.rectangle(frame, (x1, top), (x1 + tw + 8, top + th + base + 6), color, -1)
        cv2.putText(frame, text, (x1 + 4, top + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    return frame


def draw_hud(frame, fps, count):
    cv2.rectangle(frame, (8, 8), (230, 40), (0, 0, 0), -1)
    cv2.putText(frame, f"{fps:4.1f} FPS | {count} objet(s)", (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return frame
