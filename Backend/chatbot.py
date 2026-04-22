"""
chatbot.py  —  RAG + Filter + Conversation Memory (5-turn sliding window)
══════════════════════════════════════════════════════════════════════════
Flow:
  1. รับ history ทั้งหมดจาก frontend
  2. ตัด sliding window เหลือแค่ 5 turns ล่าสุด (10 messages)
     → ให้โมเดลจำบริบทใน session แต่ไม่หนักเกินไป
  3. detect_intent → filter path หรือ RAG path
  4. inject chunk_text เป็น context
  5. call Gemini
"""
 
import os, csv, json, re, time
from pathlib import Path
from google import genai
from dotenv import load_dotenv
 
# ── Load RAG engine ─────────────────────────────────────────────────────
_use_vector = False
try:
    from vector_rag import build_context, build_system_prompt, retrieve_with_filter
    _use_vector = True
    print("[chatbot] ✅ Using Vector RAG (ChromaDB)")
except Exception:
    from rag import build_context, build_system_prompt
    print("[chatbot] ⚠️  Using TF-IDF RAG")
 
from filter_query import detect_intent, apply_filter, sort_rows, build_filter_context
 
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
 
# ── Config ──────────────────────────────────────────────────────────────
MEMORY_TURNS = 5        # ← จำ 5 บทสนทนา (= 10 messages: 5 user + 5 model)
GPT_MODEL    = "gemini-2.5-flash"
 
# ── Load dataset once (จาก clean.json ที่ data_prep สร้างไว้) ──────────
_raw_rows = None
 
def _get_rows():
    global _raw_rows
    if _raw_rows is None:
        clean_path = Path(__file__).parent / "data" / "processed" / "clean.json"
        with open(clean_path, encoding="utf-8") as f:
            _raw_rows = json.load(f)["rows"]
        print(f"[chatbot] Loaded {len(_raw_rows)} species from clean.json")
    return _raw_rows
 
 
# ── System prompt ────────────────────────────────────────────────────────
BASE_SYSTEM = """คุณคือ ExoticMate ผู้เชี่ยวชาญด้านสัตว์ exotic
 
กฎสำคัญ:
1. ตอบเฉพาะข้อมูลที่มีใน [DATA] เท่านั้น ห้ามสร้างข้อมูลใหม่
2. ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์
3. หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ exotic
4. ตอบกระชับ ตรงประเด็น เป็นมิตร ใช้ emoji ประกอบ
5. จดจำบริบทการสนทนาได้จาก history"""
 
 
# ══════════════════════════════════════════════════════════════════════
#  SLIDING WINDOW  —  ตัด history เหลือ MEMORY_TURNS turns ล่าสุด
# ══════════════════════════════════════════════════════════════════════
def _apply_memory_window(history: list, n_turns: int = MEMORY_TURNS) -> list:
    """
    รับ history ทั้งหมด คืน sliding window n_turns turns ล่าสุด
    1 turn = 1 user + 1 model message = 2 items
    
    ตัวอย่าง n_turns=5:
      history มี 20 messages → คืน 10 messages (5 turn ล่าสุด)
      history มี 4 messages  → คืน 4 messages (ทั้งหมด ไม่ตัด)
    """
    max_messages = n_turns * 2   # 5 turns × 2 = 10 messages
    if len(history) <= max_messages:
        return history
    
    windowed = history[-max_messages:]
    
    # ตรวจให้แน่ใจว่า message แรกใน window เป็น role=user เสมอ
    # (ป้องกัน conversation เริ่มด้วย model)
    while windowed and windowed[0].get("role") != "user":
        windowed = windowed[1:]
    
    print(f"[chatbot] Memory window: {len(history)} → {len(windowed)} messages ({n_turns} turns)")
    return windowed
 
 
# ══════════════════════════════════════════════════════════════════════
#  FOLLOW-UP DETECTION + SPECIES ENRICHMENT
# ══════════════════════════════════════════════════════════════════════
FOLLOWUP_PATTERNS = [
    r"^(แล้ว|ถ้า|แบบ|แต่|และ|หรือ|อีก)",
    r"(มั้ย|ไหม|หน่อย)$",
]
 
def _is_followup(text: str, history: list) -> bool:
    if not history: return False
    t = text.strip().lower()
    if len(t) < 20: return True
    return any(re.search(p, t) for p in FOLLOWUP_PATTERNS)
 
 
def _extract_last_species(history: list) -> str:
    rows = _get_rows()
    for msg in reversed(history):
        for part in msg.get("parts", []):
            text = part.get("text", "").lower()
            for row in rows:
                name_en = row.get("common_name_en", "").lower()
                if name_en and name_en in text:
                    return name_en
    return ""
 
 
# ══════════════════════════════════════════════════════════════════════
#  BUILD GEMINI CONTENTS
# ══════════════════════════════════════════════════════════════════════
def _build_contents(history: list, context: str, user_input: str) -> list:
    """
    สร้าง contents array สำหรับ Gemini multi-turn
 
    ── ปัญหาเดิม ──
    inject [SYSTEM] เฉพาะตอน history=[] (แชทใหม่เท่านั้น)
    → กลับมา resume แชทเก่า โมเดลลืม system prompt ทันที
 
    ── แก้ไข ──
    inject [SYSTEM] + context เป็น turn แรกเสมอ (ทุก request)
    ตามด้วย windowed history → ตามด้วยคำถามใหม่
    Gemini จะเห็น rules + fresh context ทุกครั้งไม่ว่าจะเป็น session ใหม่หรือ resume
    """
    # ── System turn (inject ทุกครั้ง) ──────────────────────────────────
    system_text = BASE_SYSTEM
    if context:
        system_text += f"\n\n════════════════════\n[DATA]\n{context}\n════════════════════"
 
    contents = [
        # user turn — system instructions + data context
        {
            "role":  "user",
            "parts": [{"text": f"[SYSTEM]\n{system_text}"}],
        },
        # model ack — บอก Gemini ว่ารับทราบแล้ว
        {
            "role":  "model",
            "parts": [{"text": "รับทราบครับ พร้อมตอบคำถามจากฐานข้อมูลที่กำหนด"}],
        },
    ]
 
    # ── Windowed conversation history ───────────────────────────────────
    # (ทั้งแชทใหม่และ resume — ถ้า history ว่างก็ข้ามได้เลย)
    if history:
        contents.extend(history)
 
    # ── คำถามปัจจุบัน ────────────────────────────────────────────────────
    contents.append({
        "role":  "user",
        "parts": [{"text": user_input}],
    })
 
    return contents
 
 
# ══════════════════════════════════════════════════════════════════════
#  GEMINI CALL (retry 3x)
# ══════════════════════════════════════════════════════════════════════
def _call_gemini(contents: list) -> str:
    for attempt in range(3):
        try:
            res = client.models.generate_content(model=GPT_MODEL, contents=contents)
            if res.text:
                return res.text
        except Exception as e:
            print(f"[chatbot] Gemini attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return "ขออภัย ระบบกำลังมีปัญหา กรุณาลองใหม่อีกครั้ง"
 
 
# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
def ask_chatbot(user_input: str, history: list = None) -> dict:
    """
    Args:
      user_input : คำถามปัจจุบัน
      history    : full conversation history จาก frontend
                   format: [{"role": "user"/"model", "parts": [{"text": "..."}]}]
    Returns:
      reply      : str
      sources    : list
      mode       : str
    """
    if history is None:
        history = []
 
    try:
        rows    = _get_rows()
        context = ""
        sources = []
        mode    = "vector" if _use_vector else "tfidf"
 
        # ── Step 1: Apply sliding window (5 turns) ─────────────────────
        windowed_history = _apply_memory_window(history, MEMORY_TURNS)
 
        # ── Step 2: Enrich short follow-up queries ──────────────────────
        enriched_input = user_input
        if _is_followup(user_input, windowed_history):
            last_species = _extract_last_species(windowed_history)
            if last_species:
                enriched_input = f"{user_input} {last_species}"
                print(f"[chatbot] Follow-up enriched: '{user_input}' → '{enriched_input}'")
 
        # ── Step 3: Filter path (categorical queries) ────────────────────
        intent = detect_intent(enriched_input)
        if intent:
            filtered = apply_filter(rows, intent["filters"])
            filtered = sort_rows(filtered, intent.get("sort_by", ""))
            if filtered:
                context = build_filter_context(filtered, intent, max_rows=20)
                sources = [{
                    "id":      r.get("id"),
                    "name_en": r.get("common_name_en"),
                    "name_th": r.get("common_name_th"),
                    "care":    r.get("care_level"),
                    "danger":  r.get("danger_level"),
                } for r in filtered[:10]]
                mode = "filter"
 
        # ── Step 4: RAG path (specific species) ─────────────────────────
        if not context:
            context, sources, has_data = build_context(enriched_input, top_k=3)
            mode = ("vector_rag" if _use_vector else "tfidf_rag") if has_data else "rag_empty"
 
        # ── Step 5: Guard — ถ้าไม่มีข้อมูลเลย ──────────────────────────
        if not context:
            return {
                "reply":   "ขออภัยครับ ไม่พบข้อมูลในฐานข้อมูลของเรา กรุณาถามเกี่ยวกับสัตว์ exotic ที่รองรับ",
                "sources": [],
                "mode":    "no_data",
            }
 
        # ── Step 6: Build contents + Call Gemini ─────────────────────────
        contents = _build_contents(windowed_history, context, user_input)
        reply    = _call_gemini(contents)
 
        return {
            "reply":   reply,
            "sources": sources,
            "mode":    mode,
        }
 
    except Exception as e:
        print(f"[chatbot] ERROR: {e}")
        import traceback; traceback.print_exc()
        return {
            "reply":   "ระบบมีปัญหา กรุณาลองใหม่ครับ",
            "sources": [],
            "mode":    "error",
        }