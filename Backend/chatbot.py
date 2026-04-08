# """
# chatbot.py  —  RAG + Filter + Conversation History  (v2 — context memory fix)
# ════════════════════════════════════════════════════════════════════════════════
# """
 
# import os, csv, re
# from pathlib import Path
# from google import genai
# from dotenv import load_dotenv
 
# _use_vector = False
# try:
#     from vector_rag import build_context, build_system_prompt, retrieve_with_filter
#     _use_vector = True
#     print("[chatbot] ✅ Using Vector RAG (ChromaDB)")
# except FileNotFoundError:
#     from rag import build_context, build_system_prompt
#     print("[chatbot] ⚠️  Vector DB not found → TF-IDF fallback")
# except ImportError:
#     from rag import build_context, build_system_prompt
#     print("[chatbot] ⚠️  Missing packages → TF-IDF fallback")
 
# from filter_query import detect_intent, apply_filter, sort_rows, build_filter_context
 
# load_dotenv()
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
 
# CHROMA_CAT_MAP = {
#     "Bird": "Bird", "Reptile": "Reptile", "Mammal": "Mammal",
#     "Amphibian": "Amphibian", "Aquatic": "Aquatic",
# }
 
# _raw_rows = None
 
# def _get_rows():
#     global _raw_rows
#     if _raw_rows is None:
#         csv_path = Path(__file__).parent / "data" / "exotic_pets.csv"
#         with open(csv_path, encoding="utf-8-sig") as f:
#             _raw_rows = list(csv.DictReader(f))
#     return _raw_rows
 
 
# BASE_SYSTEM = """คุณคือ ExoticMate ผู้เชี่ยวชาญด้านสัตว์ exotic ที่ตอบคำถามจากฐานข้อมูลที่กำหนดเท่านั้น
 
# กฎสำคัญ:
# 1. ตอบเฉพาะข้อมูลที่มีในฐานข้อมูลที่ให้มา ห้ามสร้างข้อมูลใหม่
# 2. ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์
# 3. หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ exotic เสมอ
# 4. ตอบอย่างกระชับ ตรงประเด็น เป็นมิตร ใช้ emoji ประกอบ
# 5. จดจำบริบทการสนทนา และตอบ follow-up ได้อย่างต่อเนื่อง"""
 
 
# FOLLOWUP_PATTERNS = [
#     r"^(แล้ว|ถ้า|แบบ|แต่|และ|หรือ|อีก|เพิ่ม|ต่อ)",
#     r"(ล่ะ|อ่ะ|นะ|มั้ย|ไหม|หน่อย)$",
#     r"^(มัน|เขา|นั้น|นี้|ตัว|ชนิด|ประเภท|อัน)",
#     r"(ของมัน|ของเขา|ของตัวนี้|ชนิดนี้|ตัวนี้)",
#     r"^(กิน|อยู่|เลี้ยง|ดูแล|ราคา|กฎหมาย|อุณหภูมิ|ขนาด|อายุ)",
# ]
 
# def _is_followup(text: str, history: list) -> bool:
#     if not history:
#         return False
#     t = text.strip().lower()
#     if len(t) < 20:
#         return True
#     for pat in FOLLOWUP_PATTERNS:
#         if re.search(pat, t):
#             return True
#     return False
 
 
# def extract_last_species(history: list) -> str:
#     rows = _get_rows()
#     for msg in reversed(history):
#         for part in msg.get("parts", []):
#             text = part.get("text", "").lower()
#             for row in rows:
#                 name_en = row.get("common_name_en", "").lower()
#                 name_th = row.get("common_name_th", "")
#                 if (name_en and name_en in text) or (name_th and name_th in text):
#                     return f"{row.get('common_name_en', '')} {name_th}".strip()
#     return ""
 
 
# def _extract_last_context_query(history: list) -> str:
#     """ดึง user query แรกสุดจาก history เพื่อ re-retrieve context"""
#     for msg in history:
#         if msg.get("role") == "user":
#             parts_text = " ".join(p.get("text", "") for p in msg.get("parts", []))
#             if "[USER]" in parts_text:
#                 parts_text = parts_text.split("[USER]")[-1]
#             if "[คำถาม]" in parts_text:
#                 parts_text = parts_text.split("[คำถาม]")[-1]
#             cleaned = parts_text.strip()
#             if cleaned and len(cleaned) > 5:
#                 return cleaned
#     return ""
 
 
# def _build_gemini_contents(history: list, new_context: str, user_input: str) -> list:
#     contents = []
#     if not history:
#         system_block = BASE_SYSTEM
#         if new_context:
#             system_block += (
#                 "\n\n════════════════════\nข้อมูลจากฐานข้อมูล:\n════════════════════\n"
#                 f"{new_context}\n════════════════════"
#             )
#         contents.append({
#             "role":  "user",
#             "parts": [{"text": f"[SYSTEM]\n{system_block}\n\n[USER]\n{user_input}"}],
#         })
#     else:
#         for msg in history:
#             contents.append(msg)
#         if new_context:
#             user_text = f"[ข้อมูลเพิ่มเติมจากฐานข้อมูล]\n{new_context}\n\n[คำถาม]\n{user_input}"
#         else:
#             user_text = user_input
#         contents.append({"role": "user", "parts": [{"text": user_text}]})
#     return contents
 
 
# def ask_chatbot(user_input: str, history: list = None) -> dict:
#     if history is None:
#         history = []
 
#     try:
#         rows        = _get_rows()
#         context_str = ""
#         sources     = []
#         mode        = "vector_rag" if _use_vector else "tfidf_rag"
 
#         # ── Step 1: ตรวจ follow-up + enrich query ────────────────────
#         is_followup    = _is_followup(user_input, history)
#         enriched_input = user_input
 
#         if is_followup:
#             last_species = extract_last_species(history)
#             if last_species:
#                 enriched_input = f"{user_input} {last_species}"
#                 print(f"[chatbot] Follow-up enriched: '{user_input}' → '{enriched_input}'")
 
#         # ── Step 2: Filter path (categorical) ────────────────────────
#         intent = detect_intent(enriched_input)
#         if intent:
#             if _use_vector:
#                 cat_key    = intent["filters"].get("category")
#                 chroma_cat = CHROMA_CAT_MAP.get(cat_key) if cat_key else None
#                 vec_results = retrieve_with_filter(
#                     enriched_input, category=chroma_cat, top_k=15, threshold=0.15,
#                 )
#                 if vec_results:
#                     candidate_rows = [r["row"] for r in vec_results]
#                     attr_filters   = {k: v for k, v in intent["filters"].items() if k != "category"}
#                     if attr_filters:
#                         candidate_rows = apply_filter(candidate_rows, attr_filters)
#                     candidate_rows = sort_rows(candidate_rows, intent.get("sort_by", "care_level_rank"))
#                     if candidate_rows:
#                         context_str = build_filter_context(candidate_rows, intent, max_rows=20)
#                         sources     = [{"id": r.get("id"), "name_en": r.get("common_name_en"),
#                                         "name_th": r.get("common_name_th")} for r in candidate_rows[:10]]
#                         mode = "vector_filter"
#             if not context_str:
#                 filtered = apply_filter(rows, intent["filters"])
#                 filtered = sort_rows(filtered, intent.get("sort_by", "care_level_rank"))
#                 if filtered:
#                     context_str = build_filter_context(filtered, intent, max_rows=25)
#                     sources     = [{"id": r.get("id"), "name_en": r.get("common_name_en"),
#                                     "name_th": r.get("common_name_th")} for r in filtered[:10]]
#                     mode = "filter"
 
#         # ── Step 3: RAG path (specific species/topic) ─────────────────
#         if not context_str:
#             context_str, sources, has_data = build_context(
#                 enriched_input, top_k=3,
#                 threshold=0.25 if _use_vector else 0.05,
#             )
#             mode = ("vector_rag" if _use_vector else "tfidf_rag") if has_data else "rag_empty"
 
#         # ── Step 4: Follow-up fallback — re-use context จาก turn แรก ─
#         if not context_str and is_followup and history:
#             prev_query = _extract_last_context_query(history)
#             if prev_query:
#                 context_str, sources, has_data = build_context(
#                     prev_query, top_k=3,
#                     threshold=0.20 if _use_vector else 0.04,
#                 )
#                 if has_data:
#                     mode = "followup_reuse"
#                     print(f"[chatbot] Reused context from: '{prev_query[:60]}'")
 
#         # ── Step 5: Call Gemini ───────────────────────────────────────
#         contents = _build_gemini_contents(history, context_str, user_input)
#         response = client.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=contents,
#         )

#         reply    = response.text or "ขอโทษครับ ไม่สามารถสร้างคำตอบได้"
 
#         return {
#             "reply":    reply,
#             "has_data": bool(context_str),
#             "sources":  sources,
#             "mode":     mode,
#             "engine":   "vector" if _use_vector else "tfidf",
#         }
 
#     except Exception as e:
#         print(f"[chatbot] ERROR: {e}")
#         import traceback; traceback.print_exc()
#         return {
#             "reply":    "ระบบมีปัญหา กรุณาลองใหม่อีกครั้งครับ",
#             "has_data": False,
#             "sources":  [],
#             "mode":     "error",
#             "engine":   "error",
#         }
 


"""
chatbot.py — RAG + Filter + Conversation History (Fixed + No Hallucination)
"""

import os
import csv
import re
import time
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Load RAG (Vector หรือ TF-IDF fallback)
# ─────────────────────────────────────────────
_use_vector = False
try:
    from vector_rag import build_context, build_system_prompt, retrieve_with_filter
    _use_vector = True
    print("[chatbot] ✅ Using Vector RAG (ChromaDB)")
except Exception:
    from rag import build_context, build_system_prompt
    print("[chatbot] ⚠️ Using TF-IDF fallback")

from filter_query import detect_intent, apply_filter, sort_rows, build_filter_context

# ─────────────────────────────────────────────
# Init Gemini
# ─────────────────────────────────────────────
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ─────────────────────────────────────────────
# CSV โหลดครั้งเดียว
# ─────────────────────────────────────────────
_raw_rows = None

def _get_rows():
    global _raw_rows
    if _raw_rows is None:
        csv_path = Path(__file__).parent / "data" / "exotic_pets.csv"
        with open(csv_path, encoding="utf-8-sig") as f:
            _raw_rows = list(csv.DictReader(f))
    return _raw_rows

# ─────────────────────────────────────────────
# System Prompt (เข้ม ป้องกันมั่ว)
# ─────────────────────────────────────────────
BASE_SYSTEM = """คุณคือ ExoticMate ผู้ช่วยแนะนำสัตว์ exotic สำหรับผู้เริ่มต้น

กฎสำคัญ:
- ใช้เฉพาะข้อมูลที่มีใน [DATA] เท่านั้น
- ห้ามสร้างชื่อสัตว์ใหม่ที่ไม่มีในข้อมูล
- สามารถ "อธิบายเพิ่มเติม" ได้ แต่ต้องไม่ขัดกับข้อมูล

รูปแบบการตอบ (สำคัญมาก):
ถ้ามีการแนะนำสัตว์ ให้ตอบเป็นหัวข้อดังนี้:

1. 🐾 ชื่อสัตว์
- ชื่อไทย / อังกฤษ

2. ⭐ ระดับการเลี้ยง
- easy / medium / hard (จากข้อมูล)

3. 🍽️ อาหาร
- กินอะไรเป็นหลัก
- ความถี่โดยประมาณ

4. 🏠 ที่อยู่อาศัย
- ต้องใช้กรง/ตู้แบบไหน
- ขนาดคร่าวๆ

5. 🌡️ สภาพแวดล้อม
- อุณหภูมิ / ความชื้น (ถ้ามีข้อมูล)
- สิ่งที่ต้องมี เช่น ที่หลบ / วัสดุรองพื้น

6. 🧼 การดูแล
- ต้องทำอะไรบ้าง เช่น ทำความสะอาด / ให้อาหาร

7. ⚠️ ข้อควรรู้
- ข้อดี/ข้อจำกัด
- เหมาะกับมือใหม่หรือไม่

ข้อกำหนด:
- ถ้าไม่มีข้อมูลบางหัวข้อ → ข้ามได้
- ห้ามเดาข้อมูลที่ไม่มี
- ตอบภาษาไทย กระชับ อ่านง่าย
- ใช้ emoji ช่วยให้อ่านง่าย
"""

# ─────────────────────────────────────────────
# Follow-up detection
# ─────────────────────────────────────────────
FOLLOWUP_PATTERNS = [
    r"^(แล้ว|ถ้า|แบบ|แต่|และ|หรือ|อีก)",
    r"(มั้ย|ไหม|หน่อย)$",
]

def _is_followup(text, history):
    if not history:
        return False
    t = text.strip().lower()
    if len(t) < 20:
        return True
    return any(re.search(p, t) for p in FOLLOWUP_PATTERNS)

# ─────────────────────────────────────────────
# Extract last species
# ─────────────────────────────────────────────
def extract_last_species(history):
    rows = _get_rows()
    for msg in reversed(history):
        for part in msg.get("parts", []):
            text = part.get("text", "").lower()
            for row in rows:
                name_en = row.get("common_name_en", "").lower()
                if name_en and name_en in text:
                    return name_en
    return ""

# ─────────────────────────────────────────────
# Build Gemini contents
# ─────────────────────────────────────────────
def _build_contents(history, context, user_input):
    contents = []

    if not history:
        system_text = BASE_SYSTEM
        if context:
            system_text += f"\n\n[DATA]\n{context}"

        contents.append({
            "role": "user",
            "parts": [{"text": f"[SYSTEM]\n{system_text}\n\n[USER]\n{user_input}"}]
        })
    else:
        contents.extend(history)

        if context:
            user_text = f"[DATA]\n{context}\n\n[QUESTION]\n{user_input}"
        else:
            user_text = user_input

        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })

    return contents

# ─────────────────────────────────────────────
# Gemini call (กัน 503)
# ─────────────────────────────────────────────
def call_gemini(contents):
    for attempt in range(3):
        try:
            print(f"[AI] attempt {attempt+1}")

            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )

            if res.text:
                return res.text

        except Exception as e:
            print("[ERROR]", e)
            time.sleep(1)

    return "ขออภัย ระบบกำลังมีผู้ใช้งานจำนวนมาก กรุณาลองใหม่อีกครั้ง"

# ─────────────────────────────────────────────
# Main chatbot
# ─────────────────────────────────────────────
def ask_chatbot(user_input, history=None):
    if history is None:
        history = []

    try:
        rows = _get_rows()
        context = ""
        sources = []
        mode = "vector" if _use_vector else "tfidf"

        # ── Follow-up ─────────────────────
        if _is_followup(user_input, history):
            last = extract_last_species(history)
            if last:
                user_input = f"{user_input} {last}"

        # ── Filter ────────────────────────
        intent = detect_intent(user_input)
        if intent:
            filtered = apply_filter(rows, intent["filters"])
            filtered = sort_rows(filtered, intent.get("sort_by", ""))

            if filtered:
                context = build_filter_context(filtered, intent, max_rows=20)
                sources = filtered[:5]
                mode = "filter"

        # ── RAG ─────────────────────────
        if not context:
            context, sources, has_data = build_context(user_input, top_k=3)
            mode = "vector_rag" if _use_vector else "tfidf_rag"

        # 🔥 GUARD: ไม่มีข้อมูล → ไม่เรียก AI
        if not context:
            return {
                "reply": "ขออภัย ไม่พบข้อมูลในฐานข้อมูลครับ",
                "sources": [],
                "mode": "no_data",
            }

        # ── Call AI ─────────────────────
        contents = _build_contents(history, context, user_input)
        reply = call_gemini(contents)

        return {
            "reply": reply,
            "sources": sources,
            "mode": mode,
        }

    except Exception as e:
        print("[chatbot ERROR]", e)
        return {
            "reply": "ระบบมีปัญหา กรุณาลองใหม่",
            "sources": [],
            "mode": "error",
        }

