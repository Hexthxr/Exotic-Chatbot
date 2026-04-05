"""
chatbot.py  —  RAG + Filter + Conversation History
════════════════════════════════════════════════════
Flow:
  1. detect_intent → categorical query (นกเลี้ยงง่าย, สัตว์เลื้อยคลานไม่มีพิษ ฯ)
     → filter dataset → build context → Gemini
  2. ไม่ match → RAG (TF-IDF cosine similarity ค้นชื่อสัตว์)
  3. ทุก turn: ส่ง messages[] history ให้ Gemini (multi-turn conversation)
"""

import os, csv
from pathlib import Path
from google import genai
from dotenv import load_dotenv

from rag import build_context, build_system_prompt
from filter_query import detect_intent, apply_filter, sort_rows, build_filter_context

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client  = genai.Client(api_key=api_key)

# ── Load raw CSV once ───────────────────────────────────────────────────
_raw_rows = None

def _get_rows():
    global _raw_rows
    if _raw_rows is None:
        csv_path = Path(__file__).parent / "data" / "exotic_pets.csv"
        with open(csv_path, encoding="utf-8-sig") as f:
            _raw_rows = list(csv.DictReader(f))
        print(f"[chatbot] Loaded {len(_raw_rows)} species from CSV")
    return _raw_rows


# ── Base system prompt ──────────────────────────────────────────────────
BASE_SYSTEM = """คุณคือ ExoticMate ผู้เชี่ยวชาญด้านสัตว์ exotic ที่ตอบคำถามจากฐานข้อมูลที่กำหนดเท่านั้น

กฎสำคัญ:
1. ตอบเฉพาะข้อมูลที่มีในฐานข้อมูลที่ให้มา ห้ามสร้างข้อมูลใหม่
2. ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์
3. หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ exotic เสมอ
4. ตอบอย่างกระชับ ตรงประเด็น เป็นมิตร ใช้ emoji ประกอบ"""


def _build_gemini_contents(history: list, new_context: str, user_input: str) -> list:
    """
    สร้าง contents array สำหรับ Gemini multi-turn
    history format: [{"role": "user"/"model", "parts": [{"text": "..."}]}, ...]
    """
    contents = []

    # Inject system as first user turn (Gemini 2.x ยังไม่รองรับ system role โดยตรง)
    if not history:
        # Turn แรก: แนบ context + system ไปด้วย
        system_with_context = BASE_SYSTEM
        if new_context:
            system_with_context += f"\n\n════════════════════\nข้อมูลจากฐานข้อมูล:\n════════════════════\n{new_context}\n════════════════════"
        contents.append({
            "role": "user",
            "parts": [{"text": f"[SYSTEM]\n{system_with_context}\n\n[USER]\n{user_input}"}]
        })
    else:
        # Turn ต่อๆ ไป: ส่ง history ทั้งหมด + context ใหม่ (ถ้ามี)
        for msg in history:
            contents.append(msg)

        # ถ้ามี context ใหม่จากการ filter/RAG ให้แนบใน user turn นี้
        if new_context:
            user_text = (
                f"[ข้อมูลเพิ่มเติมจากฐานข้อมูล]\n{new_context}\n\n"
                f"[คำถาม]\n{user_input}"
            )
        else:
            user_text = user_input

        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })

    return contents


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
def ask_chatbot(user_input: str, history: list = None) -> dict:
    """
    Args:
      user_input : คำถามปัจจุบัน
      history    : list of {"role": "user"/"model", "parts": [{"text": "..."}]}
                   ส่งมาจาก frontend (เก็บทุก turn)
    Returns:
      reply      : str
      has_data   : bool
      sources    : list
      mode       : "filter" | "rag" | "error"
    """
    if history is None:
        history = []

    try:
        rows        = _get_rows()
        context_str = ""
        sources     = []
        mode        = "rag"

        # ── Path A: Categorical / filter query ─────────────────────────
        intent = detect_intent(user_input)
        if intent:
            filtered = apply_filter(rows, intent["filters"])
            filtered = sort_rows(filtered, intent.get("sort_by", "care_level_rank"))

            if filtered:
                context_str = build_filter_context(filtered, intent, max_rows=25)
                sources = [
                    {
                        "id":      r.get("id"),
                        "name_en": r.get("common_name_en"),
                        "name_th": r.get("common_name_th"),
                        "care":    r.get("care_level"),
                        "danger":  r.get("danger_level"),
                        "diet":    r.get("diet"),
                    }
                    for r in filtered[:10]
                ]
                mode = "filter"

        # ── Path B: Specific species query → RAG ───────────────────────
        if not context_str:
            context_str, sources, has_rag_data = build_context(
                user_input, top_k=3, threshold=0.05
            )
            mode = "rag" if has_rag_data else "rag_empty"

        # ── Build Gemini contents with history ─────────────────────────
        contents = _build_gemini_contents(history, context_str, user_input)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )

        reply    = response.text or "ขอโทษครับ ไม่สามารถสร้างคำตอบได้"
        has_data = bool(context_str)

        return {
            "reply":    reply,
            "has_data": has_data,
            "sources":  sources,
            "mode":     mode,
        }

    except Exception as e:
        print(f"[chatbot] ERROR: {e}")
        return {
            "reply":    "ระบบมีปัญหา กรุณาลองใหม่อีกครั้งครับ",
            "has_data": False,
            "sources":  [],
            "mode":     "error",
        }
