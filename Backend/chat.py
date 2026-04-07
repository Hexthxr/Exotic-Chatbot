from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import chats_collection
from chatbot import ask_chatbot
from datetime import datetime
from bson import ObjectId

chat_bp = Blueprint("chat", __name__)

# ✅ สร้างห้องใหม่
@chat_bp.route("/create-room", methods=["POST"])
@jwt_required(optional=True)
def create_room():
    user_id = get_jwt_identity()

    room = {
        "user_id": user_id,
        "title": "New Chat",
        "messages": [],
        "created_at": datetime.utcnow()
    }

    result = chats_collection.insert_one(room)

    return jsonify({"room_id": str(result.inserted_id)})


# ✅ ส่งข้อความ
@chat_bp.route("/chat", methods=["POST"])
@jwt_required(optional=True)
def chat():
    data = request.json
    user_id = get_jwt_identity()

    room_id = data.get("room_id")
    message = data.get("message")

    room = chats_collection.find_one({"_id": ObjectId(room_id), "user_id": user_id})

    if not room:
        return jsonify({"error": "Room not found"}), 404

    result = ask_chatbot(message, history=room["messages"])

    chats_collection.update_one(
        {"_id": ObjectId(room_id)},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "content": message},
                        {"role": "bot", "content": result["response"]}
                    ]
                }
            }
        }
    )

    # ตั้งชื่อห้องอัตโนมัติ (ครั้งแรก)
    if len(room["messages"]) == 0:
        chats_collection.update_one(
            {"_id": ObjectId(room_id)},
            {"$set": {"title": message[:20]}}
        )

    return jsonify(result)


# ✅ ดึง list ห้อง
@chat_bp.route("/rooms", methods=["GET"])
@jwt_required(optional=True)
def get_rooms():
    user_id = get_jwt_identity()

    rooms = chats_collection.find({"user_id": user_id})

    return jsonify([
        {
            "id": str(r["_id"]),
            "title": r.get("title", "Chat")
        }
        for r in rooms
    ])


# ✅ ดึง history ของห้อง
@chat_bp.route("/history/<room_id>", methods=["GET"])
@jwt_required(optional=True)
def get_history(room_id):
    user_id = get_jwt_identity()

    room = chats_collection.find_one({
        "_id": ObjectId(room_id),
        "user_id": user_id
    })

    if not room:
        return jsonify({"error": "Not found"}), 404

    return jsonify(room["messages"])