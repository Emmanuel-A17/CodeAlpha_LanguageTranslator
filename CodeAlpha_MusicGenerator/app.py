"""
Étape 4 — Interface web.

    python app.py      puis ouvrir http://127.0.0.1:5000
"""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from musicai.engine import OUTPUTS, Engine

ROOT = Path(__file__).parent
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="")
engine = Engine()


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/outputs/<path:name>")
def outputs(name):
    return send_from_directory(OUTPUTS, name)


@app.get("/api/status")
def status():
    return jsonify({"models": engine.available(), "lstm_error": engine.info.get("lstm_error")})


@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    try:
        seed = body.get("seed")
        result = engine.generate(
            model=body.get("model", "lstm"),
            seconds=body.get("seconds", 20),
            tempo=body.get("tempo", 100),
            temperature=body.get("temperature", 0.9),
            top_k=body.get("top_k", 30),
            polyphony=body.get("polyphony", 6),
            seed=int(seed) if seed not in (None, "") else None,
        )
    except (ValueError, RuntimeError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


if __name__ == "__main__":
    print("Ouvrez http://127.0.0.1:5000 dans votre navigateur")
    app.run(host="127.0.0.1", port=5000, debug=False)
