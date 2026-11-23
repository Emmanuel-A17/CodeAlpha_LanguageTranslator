"""
CodeAlpha - Tâche 1 : Language Translation Tool
Backend Flask : sert l'interface et expose une API de traduction.

Moteur principal : endpoint public de Google Translate (sans clé API).
Moteur de secours : API MyMemory (gratuite, sans clé).
Pour utiliser l'API officielle Google Cloud Translation, voir README.md.
"""

import os
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="/static")

MAX_CHARS = 5000
TIMEOUT = 12

# Code -> nom de la langue (affiché dans l'interface)
LANGUAGES = {
    "auto": "Détecter la langue",
    "af": "Afrikaans", "sq": "Albanais", "de": "Allemand", "en": "Anglais",
    "ar": "Arabe", "hy": "Arménien", "az": "Azéri", "eu": "Basque",
    "bn": "Bengali", "be": "Biélorusse", "my": "Birman", "bs": "Bosniaque",
    "bg": "Bulgare", "ca": "Catalan", "zh-CN": "Chinois (simplifié)",
    "zh-TW": "Chinois (traditionnel)", "ko": "Coréen", "hr": "Croate",
    "da": "Danois", "es": "Espagnol", "et": "Estonien", "fi": "Finnois",
    "fr": "Français", "gl": "Galicien", "ka": "Géorgien", "el": "Grec",
    "gu": "Gujarati", "ha": "Haoussa", "he": "Hébreu", "hi": "Hindi",
    "hu": "Hongrois", "ig": "Igbo", "id": "Indonésien", "ga": "Irlandais",
    "is": "Islandais", "it": "Italien", "ja": "Japonais", "kn": "Kannada",
    "kk": "Kazakh", "km": "Khmer", "lo": "Lao", "la": "Latin",
    "lv": "Letton", "lt": "Lituanien", "mk": "Macédonien", "ms": "Malais",
    "ml": "Malayalam", "mt": "Maltais", "mr": "Marathi", "mn": "Mongol",
    "ne": "Népalais", "no": "Norvégien", "uz": "Ouzbek", "ps": "Pachto",
    "fa": "Persan", "pl": "Polonais", "pt": "Portugais", "pa": "Pendjabi",
    "ro": "Roumain", "ru": "Russe", "sr": "Serbe", "sn": "Shona",
    "si": "Cingalais", "sk": "Slovaque", "sl": "Slovène", "so": "Somali",
    "sw": "Swahili", "sv": "Suédois", "tl": "Filipino", "tg": "Tadjik",
    "ta": "Tamoul", "cs": "Tchèque", "te": "Télougou", "th": "Thaï",
    "tr": "Turc", "uk": "Ukrainien", "ur": "Ourdou", "vi": "Vietnamien",
    "cy": "Gallois", "yo": "Yoruba", "zu": "Zoulou", "nl": "Néerlandais",
}


def translate_google(text: str, source: str, target: str):
    """Traduction via l'endpoint public de Google Translate."""
    resp = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    translated = "".join(part[0] for part in data[0] if part and part[0])
    detected = data[2] if len(data) > 2 else source
    return translated, detected


def translate_mymemory(text: str, source: str, target: str):
    """Moteur de secours : MyMemory (limité à ~500 caractères par requête)."""
    src = "en" if source == "auto" else source
    resp = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text[:500], "langpair": f"{src}|{target}"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["responseData"]["translatedText"], src


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/languages")
def languages():
    return jsonify(LANGUAGES)


@app.post("/api/translate")
def translate():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    source = payload.get("source", "auto")
    target = payload.get("target", "en")

    if not text:
        return jsonify(error="Veuillez saisir un texte à traduire."), 400
    if len(text) > MAX_CHARS:
        return jsonify(error=f"Le texte dépasse {MAX_CHARS} caractères."), 400
    if source not in LANGUAGES or target not in LANGUAGES or target == "auto":
        return jsonify(error="Langue source ou cible invalide."), 400
    if source == target:
        return jsonify(translation=text, detected=source, engine="none")

    try:
        translated, detected = translate_google(text, source, target)
        engine = "google"
    except Exception:
        try:
            translated, detected = translate_mymemory(text, source, target)
            engine = "mymemory"
        except Exception:
            return jsonify(
                error="Service de traduction indisponible. Vérifiez votre connexion internet."
            ), 502

    return jsonify(translation=translated, detected=detected, engine=engine)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Traducteur disponible sur http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
