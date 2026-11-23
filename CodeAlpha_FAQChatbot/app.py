"""
CodeAlpha - Tâche 2 : Chatbot for FAQs
Serveur Flask : sert l'interface de chat et expose l'API du chatbot.

Lancer :  python app.py   puis ouvrir  http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, request, send_from_directory

from chatbot import NLP_BACKEND, FAQChatbot

app = Flask(__name__, static_folder="static", static_url_path="/static")
bot = FAQChatbot()

MAX_MESSAGE_LENGTH = 500


@app.after_request
def add_cors_headers(response):
    """Autorise l'interface même si la page est ouverte via Live Server (autre port)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", faqs=len(bot.faqs), nlp=NLP_BACKEND, topic=bot.topic)


@app.get("/api/suggestions")
def suggestions():
    return jsonify(bot.popular())


@app.get("/api/faqs")
def faqs():
    return jsonify(bot.catalog())


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}

    # Clic sur une question suggérée : on renvoie directement sa réponse
    faq_id = payload.get("faq_id")
    if isinstance(faq_id, int):
        result = bot.answer_by_id(faq_id)
        if result:
            return jsonify(result)

    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify(error="Le message est vide."), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify(error=f"Le message dépasse {MAX_MESSAGE_LENGTH} caractères."), 400

    return jsonify(bot.reply(message))


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify(error="Route introuvable."), 404
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Chatbot FAQ prêt ({len(bot.faqs)} FAQ, moteur NLP : {NLP_BACKEND})")
    print(f"  Ouvrir : http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
