"""
app.py  —  Flask API (with Auth + MongoDB session storage)
═══════════════════════════════════════════════════════════
POST  /chat                  → ส่งข้อความ (ถ้า login จะบันทึก session ลง MongoDB)
GET   /sessions              → ดึงรายการ sessions ของ user (auth required)
GET   /sessions/<id>         → ดึงข้อความใน session (auth required)
DELETE /sessions/<id>        → ลบ session (auth required)
PATCH /sessions/<id>/title   → แก้ไขชื่อ session (auth required)
POST  /auth/register         → สมัครสมาชิก
POST  /auth/login            → เข้าสู่ระบบ
GET   /auth/me               → ข้อมูล user ปัจจุบัน
GET   /health                → health check
"""
 
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from bson import ObjectId
 
from chatbot import ask_chatbot
from auth    import auth_bp, get_current_user
from db      import get_db
 
app = Flask(__name__)
CORS(app)
app.register_blueprint(auth_bp)
 
 
# ══════════════════════════════════════════════════════════════════════
#  CHAT  (core endpoint — บันทึก session ถ้า login)
# ══════════════════════════════════════════════════════════════════════
@app.route("/chat", methods=["POST"])
def chat():
    data       = request.json or {}
    user_input = data.get("message", "").strip()
    history    = data.get("history", [])
    session_id = data.get("session_id")   # MongoDB _id (str) — ส่งมาจาก frontend ถ้ามีแล้ว
 
    if not user_input:
        return jsonify({"error": "message is required"}), 400
 
    # ── RAG + Gemini ────────────────────────────────────────────────
    result = ask_chatbot(user_input, history=history)
 
    # ── Persist to MongoDB if authenticated ─────────────────────────
    user_id = get_current_user()
    if user_id:
        db      = get_db()
        now     = datetime.datetime.utcnow()
        user_msg = {"role": "user",      "content": user_input,       "ts": now}
        bot_msg  = {"role": "assistant", "content": result["reply"],  "ts": now}
 
        if session_id:
            # Append messages to existing session
            db.chat_sessions.update_one(
                {"_id": ObjectId(session_id), "user_id": user_id},
                {
                    "$push": {"messages": {"$each": [user_msg, bot_msg]}},
                    "$set":  {"updated_at": now},
                }
            )
        else:
            # Create new session — title = first user message (truncated)
            title      = user_input[:42] + ("…" if len(user_input) > 42 else "")
            new_doc    = {
                "user_id":    user_id,
                "title":      title,
                "messages":   [user_msg, bot_msg],
                "created_at": now,
                "updated_at": now,
            }
            new_id     = db.chat_sessions.insert_one(new_doc).inserted_id
            session_id = str(new_id)
 
        result["session_id"] = session_id
 
    return jsonify(result)
 
 
# ══════════════════════════════════════════════════════════════════════
#  SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════
@app.route("/sessions", methods=["GET"])
def list_sessions():
    user_id = get_current_user()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
 
    db       = get_db()
    sessions = list(
        db.chat_sessions
          .find({"user_id": user_id}, {"messages": 0})   # ไม่ดึง messages ตอน list
          .sort("updated_at", -1)
    )
    return jsonify([{
        "id":   str(s["_id"]),
        "title": s.get("title", "แชทใหม่"),
        "time":  s.get("updated_at", s.get("created_at")).isoformat(),
    } for s in sessions])
 
 
@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    user_id = get_current_user()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
 
    db      = get_db()
    session = db.chat_sessions.find_one(
        {"_id": ObjectId(session_id), "user_id": user_id}
    )
    if not session:
        return jsonify({"error": "Session not found"}), 404
 
    return jsonify({
        "id":    str(session["_id"]),
        "title": session.get("title", "แชทใหม่"),
        "time":  session.get("updated_at").isoformat(),
        "msgs":  [
            {"role": m["role"], "content": m["content"]}
            for m in session.get("messages", [])
        ],
    })
 
 
@app.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    user_id = get_current_user()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
 
    db = get_db()
    db.chat_sessions.delete_one({"_id": ObjectId(session_id), "user_id": user_id})
    return jsonify({"ok": True})
 
 
@app.route("/sessions/<session_id>/title", methods=["PATCH"])
def update_title(session_id):
    user_id = get_current_user()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
 
    title = (request.json or {}).get("title", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
 
    db = get_db()
    db.chat_sessions.update_one(
        {"_id": ObjectId(session_id), "user_id": user_id},
        {"$set": {"title": title, "updated_at": datetime.datetime.utcnow()}}
    )
    return jsonify({"ok": True})
 
 
# ══════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "rag": "enabled", "model": "gemini-2.5-flash", "auth": "mongodb"})
 
 
if __name__ == "__main__":
    app.run(debug=True)