"""
Interface web : choisir la webcam ou une vidéo, voir la détection et le suivi en direct.

    python app.py      puis ouvrir http://127.0.0.1:5000
"""

import threading
import uuid
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify, request

from objtrack.detector import CLASS_NAMES, YoloDetector
from objtrack.pipeline import open_source, run

ROOT = Path(__file__).parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
ALLOWED = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

_detector = None
_lock = threading.Lock()
state = {"config": None, "stop": threading.Event(), "stats": {}, "error": None}


def get_detector():
    global _detector
    if _detector is None:
        _detector = YoloDetector()
    return _detector


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/classes")
def classes():
    return jsonify(CLASS_NAMES)


@app.post("/api/start")
def start():
    """Choisit la source : JSON {"source": "webcam"} ou formulaire avec un fichier « video »."""
    state["stop"].set()                                      # arrête un flux précédent
    state["error"], state["stats"] = None, {}
    if "video" in request.files:
        file = request.files["video"]
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED:
            return jsonify({"error": "Format non géré. Utilisez mp4, avi, mov, mkv ou webm."}), 400
        path = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
        file.save(path)
        source, options = str(path), request.form
    else:
        body = request.get_json(silent=True) or {}
        source, options = str(body.get("camera", "0")), body
    classes_raw = options.get("classes") or ""
    chosen = [c for c in (classes_raw if isinstance(classes_raw, list) else classes_raw.split(",")) if c in CLASS_NAMES]
    try:
        conf = min(max(float(options.get("conf", 0.4)), 0.1), 0.9)
    except ValueError:
        conf = 0.4
    state["config"] = {"source": source, "conf": conf, "classes": chosen}
    return jsonify({"ok": True})


def mjpeg(config, stop):
    try:
        detector = get_detector()
        detector.conf, detector.classes = config["conf"], set(config["classes"]) or None
        cap = open_source(config["source"])
    except Exception as exc:
        state["error"] = str(exc)
        return
    try:
        for frame, stats in run(cap, detector, detect_every=1, stop=stop.is_set):
            state["stats"] = {**stats, "visible": dict(stats["visible"]), "total": dict(stats["total"])}
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
    finally:
        cap.release()
        state["stats"] = {**state["stats"], "ended": True}


@app.get("/stream")
def stream():
    config = state["config"]
    if not config:
        return jsonify({"error": "Choisissez d'abord une source."}), 400
    with _lock:
        state["stop"].set()
        stop = state["stop"] = threading.Event()
    return Response(mjpeg(config, stop), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/stop")
def stop():
    state["stop"].set()
    return jsonify({"ok": True})


@app.get("/api/stats")
def stats():
    return jsonify({**state["stats"], "error": state["error"]})


if __name__ == "__main__":
    print("Ouvrez http://127.0.0.1:5000 dans votre navigateur")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
