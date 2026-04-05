from flask import Flask, request, jsonify
from chatbot import ask_chatbot
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    data       = request.json or {}
    user_input = data.get("message", "").strip()
    history    = data.get("history", [])   # ← รับ conversation history จาก frontend

    if not user_input:
        return jsonify({"error": "message is required"}), 400

    result = ask_chatbot(user_input, history=history)
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "rag": "enabled", "model": "gemini-2.5-flash"})

if __name__ == "__main__":
    app.run(debug=True)
