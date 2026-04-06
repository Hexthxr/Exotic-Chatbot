"""
chatbot.py  —  RAG + Filter + Conversation History
════════════════════════════════════════════════════
Flow:
  1. detect_intent → categorical query (นกเลี้ยงง่าย, สัตว์เลื้อยคลานไม่มีพิษ ฯ)
     → filter dataset → build context → Gemini
  2. ไม่ match → RAG (TF-IDF cosine similarity ค้นชื่อสัตว์)
  3. ทุก turn: ส่ง messages[] history ให้ Gemini (multi-turn conversation)
"""

import os, csv, re
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
BASE_SYSTEM = """คุณคือ ExoticMate ระบบให้ข้อมูลสัตว์ exotic เท่านั้น

กฎเหล็กที่ห้ามละเมิดเด็ดขาด:
1. หากคำถามไม่เกี่ยวกับสัตว์ exotic การเลี้ยงดู อาหาร หรือกฎหมายสัตว์
   ตอบว่า "ขอโทษครับ ฉันตอบได้เฉพาะเรื่องสัตว์ exotic เท่านั้น 🐾" แล้วหยุด
2. หากถามเรื่องกิน ฆ่า ทำร้าย หรือทำอันตรายสัตว์
   ตอบว่า "ExoticMate ให้ข้อมูลการเลี้ยงดูเท่านั้น ไม่สามารถตอบคำถามนี้ได้ครับ 🙏" แล้วหยุด
3. ตอบเฉพาะข้อมูลในฐานข้อมูลที่ให้มา ห้ามสร้างข้อมูลใหม่
4. ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์
5. หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ exotic เสมอ
6. ตอบสั้น กระชับ เป็นมิตร ใช้ emoji ประกอบ

ห้ามตอบเรื่อง: บุคคล ความสัมพันธ์ การเมือง อาหารคน เทคโนโลยี หรือเรื่องทั่วไปใดๆ ทั้งสิ้น"""


# ── Keywords สำหรับเช็ค off-topic และ harmful ──────────────────────────
EXOTIC_KEYWORDS = [
    "สัตว์", "เลี้ยง", "gecko", "python", "snake", "งู", "กิ้งก่า",
    "นก", "กบ", "เต่า", "แมงมุม", "tarantula", "chameleon", "axolotl",
    "กฎหมาย", "cites", "อาหาร", "กรง", "อุณหภูมิ", "ความชื้น",
    "ดูแล", "เพาะพันธุ์", "ซื้อ", "ราคา", "exotic", "สายพันธุ์",
    "ชื่อวิทยาศาสตร์", "ใบอนุญาต", "พิษ", "อันตราย", "อายุขัย",
    "ถิ่นกำเนิด", "นิสัย", "กินอะไร", "อยู่ที่ไหน", "ใหญ่แค่ไหน",
    "ball python", "leopard", "bearded dragon", "iguana", "tortoise",
    "parrot", "hamster", "sugar glider", "hedgehog", "ferret",
    "chinchilla", "scorpion", "monitor", "chameleon", "skink",
]

HARMFUL_KEYWORDS = [
    "ฆ่า", "ทำร้าย", "ทรมาน", "ต้ม", "ย่าง", "ทอด",
    "กำจัด", "เชือด", "แทง", "ตี", "kill", "hurt", "harm",
    "จะกิน", "กินมัน", "กินได้มั้ย", "กินได้ไหม", "เอามากิน",
]


def is_harmful(text: str) -> bool:
    """เช็คว่าถามเรื่องทำร้ายสัตว์ไหม"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in HARMFUL_KEYWORDS)


def is_off_topic(text: str) -> bool:
    """เช็คว่าไม่เกี่ยวกับสัตว์ exotic ไหม"""
    text_lower = text.lower()
    return not any(kw in text_lower for kw in EXOTIC_KEYWORDS)


def _build_gemini_contents(history: list, new_context: str, user_input: str) -> list:
    """
    สร้าง contents array สำหรับ Gemini multi-turn
    history format: [{"role": "user"/"model", "parts": [{"text": "..."}]}, ...]
    """
    contents = []

    if not history:
        system_with_context = BASE_SYSTEM
        if new_context:
            system_with_context += f"\n\n════════════════════\nข้อมูลจากฐานข้อมูล:\n════════════════════\n{new_context}\n════════════════════"
        contents.append({
            "role": "user",
            "parts": [{"text": f"[SYSTEM]\n{system_with_context}\n\n[USER]\n{user_input}"}]
        })
    else:
        for msg in history:
            contents.append(msg)

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


# ── Extract last mentioned species from history ─────────────────────────
def extract_last_species(history: list) -> str:
    """ดึงชื่อสัตว์ที่พูดถึงล่าสุดจาก conversation history"""
    rows = _get_rows()
    for msg in reversed(history):
        for part in msg.get("parts", []):
            text = part.get("text", "").lower()
            for row in rows:
                name_en = row.get("common_name_en", "").lower()
                name_th = row.get("common_name_th", "")
                if (name_en and name_en in text) or (name_th and name_th in text):
                    return f"{row.get('common_name_en', '')} {name_th}".strip()
    return ""


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
      mode       : "filter" | "rag" | "error" | "off_topic" | "harmful"
    """
    if history is None:
        history = []

    # ── เช็ค harmful ก่อนเลย ไม่ส่งให้ Gemini ──────────────────────────
    if is_harmful(user_input):
        print(f"[chatbot] Harmful detected: '{user_input}'")
        return {
            "reply":    "ExoticMate ให้ข้อมูลการเลี้ยงดูเท่านั้น ไม่สามารถตอบคำถามนี้ได้ครับ 🙏",
            "has_data": False,
            "sources":  [],
            "mode":     "harmful",
        }

    try:
        rows        = _get_rows()
        context_str = ""
        sources     = []
        mode        = "rag"

        # ── Enrich short follow-up queries with species context ─────────
        enriched_input = user_input
        if len(user_input.strip()) < 15 and history:
            last_species = extract_last_species(history)
            if last_species:
                enriched_input = f"{user_input} ของ {last_species}"
                print(f"[chatbot] Enriched: '{user_input}' → '{enriched_input}'")

        # ── เช็ค off-topic หลัง enrich แล้ว ───────────────────────────
        # ใช้ enriched_input เพื่อให้คำถามสั้นที่ต่อจากบริบทสัตว์ผ่านได้
        if is_off_topic(enriched_input):
            print(f"[chatbot] Off-topic detected: '{enriched_input}'")
            return {
                "reply":    "ขอโทษครับ ฉันตอบได้เฉพาะเรื่องสัตว์ exotic เท่านั้น 🐾",
                "has_data": False,
                "sources":  [],
                "mode":     "off_topic",
            }

        # ── Path A: Categorical / filter query ─────────────────────────
        intent = detect_intent(enriched_input)
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
                enriched_input, top_k=3, threshold=0.05
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