"""
db.py  —  MongoDB Connection
══════════════════════════════
Lazy singleton connection to MongoDB Atlas
"""
 
import os
from pymongo import MongoClient
from dotenv import load_dotenv
 
load_dotenv()
 
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://Exotic_db_user:Exotic1412@exoticmate.yeyv1fy.mongodb.net/exotic_chatbot?retryWrites=true&w=majority"
)
 
_client = None
_db     = None
 
 
def get_db():
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db     = _client["exotic_chatbot"]
        # ── Ensure indexes ──────────────────────────────────────
        _db.users.create_index("email",    unique=True)
        _db.users.create_index("username", unique=True)
        _db.chat_sessions.create_index([("user_id", 1), ("updated_at", -1)])
        print("[DB] Connected to MongoDB Atlas ✓")
    return _db
 