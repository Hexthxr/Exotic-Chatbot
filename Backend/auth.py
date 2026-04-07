"""
auth.py  —  Authentication Blueprint
══════════════════════════════════════
POST /auth/register   → สมัครสมาชิก
POST /auth/login      → เข้าสู่ระบบ
GET  /auth/me         → ตรวจสอบ token
 
JWT Bearer token  (expire 30 วัน)
"""
 
import os, datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from bson import ObjectId
from dotenv import load_dotenv
 
load_dotenv()
 
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
JWT_SECRET = os.getenv("JWT_SECRET", "exoticmate-super-secret-2024")
 
 
# ── Token helpers ──────────────────────────────────────────────────────
def _create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
 
 
def _decode_token(token: str):
    """Returns user_id string or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except Exception:
        return None
 
 
def get_current_user() -> str | None:
    """
    ดึง user_id จาก Authorization: Bearer <token>
    Returns user_id string หรือ None ถ้าไม่มี / invalid
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return _decode_token(header[7:])
 
 
# ── Routes ─────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    from db import get_db
    data     = request.json or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
 
    # Validate
    if not username or not email or not password:
        return jsonify({"error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400
    if len(username) < 3:
        return jsonify({"error": "ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร"}), 400
    if len(password) < 6:
        return jsonify({"error": "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"}), 400
    if "@" not in email:
        return jsonify({"error": "รูปแบบอีเมลไม่ถูกต้อง"}), 400
 
    db = get_db()
    if db.users.find_one({"email": email}):
        return jsonify({"error": "อีเมลนี้ถูกใช้งานแล้ว"}), 409
    if db.users.find_one({"username": username}):
        return jsonify({"error": "ชื่อผู้ใช้นี้ถูกใช้งานแล้ว"}), 409
 
    doc    = {
        "username":      username,
        "email":         email,
        "password_hash": generate_password_hash(password),
        "created_at":    datetime.datetime.utcnow(),
    }
    result = db.users.insert_one(doc)
    token  = _create_token(str(result.inserted_id))
 
    return jsonify({
        "token": token,
        "user":  {"id": str(result.inserted_id), "username": username, "email": email},
    }), 201
 
 
@auth_bp.route("/login", methods=["POST"])
def login():
    from db import get_db
    data     = request.json or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
 
    if not email or not password:
        return jsonify({"error": "กรุณากรอกอีเมลและรหัสผ่าน"}), 400
 
    db   = get_db()
    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}), 401
 
    token = _create_token(str(user["_id"]))
    return jsonify({
        "token": token,
        "user":  {"id": str(user["_id"]), "username": user["username"], "email": user["email"]},
    })
 
 
@auth_bp.route("/me", methods=["GET"])
def me():
    from db import get_db
    user_id = get_current_user()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
 
    db   = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
 
    return jsonify({"id": str(user["_id"]), "username": user["username"], "email": user["email"]})
 