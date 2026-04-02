from flask import Flask, request, jsonify
from chatbot import ask_chatbot
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json["message"]

    reply = ask_chatbot(user_input)

    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)