"""
rag.py  —  RAG Engine for Exotic Pet Chatbot
═════════════════════════════════════════════
- Loads the processed clean.json + tfidf_vocab.json at startup
- retrieve(query, top_k) → list of matched species rows
- build_context(query)   → (context_str, sources, has_data)
- build_system_prompt(context_str) → full system prompt for Gemini
"""

import json, re, unicodedata, math
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────
BASE      = Path(__file__).parent / "data" / "processed"
CLEAN_F   = BASE / "clean.json"
VOCAB_F   = BASE / "tfidf_vocab.json"

# ── Lazy-loaded globals ────────────────────────────────────────────────
_dataset    = None
_vocab      = None
_idf        = None
_index_vecs = None   # list of sparse dicts  { term_idx: tfidf_weight }


def _load():
    """Load artefacts once."""
    global _dataset, _vocab, _idf, _index_vecs
    if _dataset is not None:
        return

    print("[RAG] Loading dataset …")
    with open(CLEAN_F, encoding="utf-8") as f:
        data = json.load(f)
    _dataset = data["rows"]

    print("[RAG] Loading TF-IDF vocab …")
    with open(VOCAB_F, encoding="utf-8") as f:
        vdata = json.load(f)
    _vocab = vdata["vocabulary"]   # str → int index
    _idf   = vdata["idf"]          # list[float]

    print("[RAG] Building index vectors …")
    _index_vecs = [_vectorize(r["_search_text"]) for r in _dataset]
    print(f"[RAG] Ready — {len(_dataset)} species indexed.")


# ── Text normalization ─────────────────────────────────────────────────
def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


# ── Char n-gram extraction (2-4, word-boundary aware) ─────────────────
def _char_ngrams(text: str):
    padded = f" {text} "
    counts = {}
    for n in range(2, 5):
        for i in range(len(padded) - n + 1):
            gram = padded[i:i + n]
            counts[gram] = counts.get(gram, 0) + 1
    return counts


# ── Build TF-IDF sparse vector as dict ────────────────────────────────
def _vectorize(text: str) -> dict:
    _load()
    ngrams   = _char_ngrams(_normalize(text))
    total    = sum(ngrams.values()) or 1
    vec      = {}
    for gram, cnt in ngrams.items():
        idx = _vocab.get(gram)
        if idx is not None:
            tf        = math.log(1 + cnt / total)   # sublinear TF
            vec[idx]  = tf * _idf[idx]
    return vec


# ── Cosine similarity between two sparse dicts ────────────────────────
def _cosine(a: dict, b: dict) -> float:
    dot   = sum(a[k] * b[k] for k in a if k in b)
    normA = math.sqrt(sum(v * v for v in a.values()))
    normB = math.sqrt(sum(v * v for v in b.values()))
    denom = normA * normB
    return dot / denom if denom else 0.0


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: retrieve
# ══════════════════════════════════════════════════════════════════════
def retrieve(query: str, top_k: int = 3, threshold: float = 0.05):
    """
    Returns list of dicts sorted by relevance score:
      { "row": {...species data...}, "score": float }
    """
    _load()
    q_vec   = _vectorize(query)
    scored  = [
        {"row": row, "score": _cosine(q_vec, iv)}
        for row, iv in zip(_dataset, _index_vecs)
    ]
    scored.sort(key=lambda x: -x["score"])
    return [s for s in scored[:top_k] if s["score"] >= threshold]


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: build_context
# ══════════════════════════════════════════════════════════════════════
def build_context(query: str, top_k: int = 3, threshold: float = 0.05):
    """
    Returns:
      context_str  : formatted string for system prompt
      sources      : list of { id, name_en, name_th, score }
      has_data     : bool
    """
    results = retrieve(query, top_k, threshold)
    if not results:
        return "", [], False

    parts = []
    sources = []
    for i, r in enumerate(results):
        row = r["row"]
        score = r["score"]

        block = (
            f"[สัตว์ {i+1}] ความเกี่ยวข้อง {score*100:.0f}%\n"
            f"ชื่อไทย: {row.get('common_name_th', '-')}\n"
            f"ชื่อภาษาอังกฤษ: {row.get('common_name_en', '-')}\n"
            f"ชื่อวิทยาศาสตร์: {row.get('scientific_name', '-')}\n"
            f"หมวดหมู่: {row.get('category', '-')} / {row.get('subcategory', '-')}\n"
            f"ถิ่นกำเนิด: {row.get('origin_region', '-')}\n"
            f"ขนาด (ซม.): {row.get('typical_size_cm', '-')}\n"
            f"อายุขัย (ปี): {row.get('lifespan_years', '-')}\n"
            f"อาหาร: {row.get('diet', '-')}\n"
            f"ที่อยู่อาศัย: {row.get('habitat', '-')}\n"
            f"ช่วงเวลาหากิน: {row.get('activity_pattern', '-')}\n"
            f"นิสัย: {row.get('temperament', '-')}\n"
            f"ความยากในการจับ/การดูแล: {row.get('handling_level', '-')} / {row.get('care_level', '-')}\n"
            f"เหมาะสำหรับมือใหม่: {row.get('beginner_friendly', '-')}\n"
            f"ที่พักพิงแนะนำ: {row.get('recommended_enclosure', '-')}\n"
            f"อุณหภูมิ (°C): {row.get('temperature_c_range', '-')}\n"
            f"ความชื้น (%): {row.get('humidity_percent_range', '-')}\n"
            f"ความต้องการทางสังคม: {row.get('social_needs', '-')}\n"
            f"ระดับอันตราย: {row.get('danger_level', '-')}\n"
            f"มีพิษ/เป็นอันตราย: {row.get('venomous_or_toxic', '-')}\n"
            f"ราคาประมาณ (บาท): {row.get('estimated_price_range_thb', '-')}\n"
            f"สถานะการครอบครองในไทย: {row.get('possession_status_th', '-')}\n"
            f"ข้อกำหนดการครอบครอง: {row.get('possession_requirement_th', '-')}\n"
            f"สถานะทางกฎหมาย: {row.get('legal_status_hint_th', '-')}\n"
            f"หมายเหตุกฎหมาย: {row.get('legal_note_th', '-')}\n"
        )
        parts.append(block)
        sources.append({
            "id":       row.get("id"),
            "name_en":  row.get("common_name_en"),
            "name_th":  row.get("common_name_th"),
            "sci":      row.get("scientific_name"),
            "score":    round(score, 4),
        })

    context_str = "\n".join(parts)
    return context_str, sources, True


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: build_system_prompt
# ══════════════════════════════════════════════════════════════════════
def build_system_prompt(context_str: str = "") -> str:
    BASE_PROMPT = """คุณคือผู้ช่วยแชทบอทด้านสัตว์ exotic ที่ตอบคำถามจากฐานข้อมูลที่กำหนดเท่านั้น

กฎสำคัญ:
1. ตอบเฉพาะข้อมูลที่มีอยู่ในฐานข้อมูลที่ให้มา ห้ามคาดเดาหรือสร้างข้อมูลใหม่
2. หากไม่มีข้อมูลในฐานข้อมูล ให้ตอบว่า "ขอโทษครับ ไม่มีข้อมูลสัตว์ชนิดนี้ในฐานข้อมูลของเรา"
3. ตอบเป็นภาษาไทยเสมอ ยกเว้นชื่อวิทยาศาสตร์
4. หากถามเรื่องสุขภาพหรืออาการป่วย ให้แนะนำพบสัตวแพทย์ exotic เสมอ
5. ตอบอย่างกระชับ ตรงประเด็น และเป็นมิตร"""

    if not context_str:
        return BASE_PROMPT + "\n\nหมายเหตุ: ไม่พบข้อมูลที่เกี่ยวข้องในฐานข้อมูล กรุณาแจ้งผู้ใช้"

    return f"""{BASE_PROMPT}

════════════════════════════════════════
ข้อมูลสัตว์ที่เกี่ยวข้องจากฐานข้อมูล:
════════════════════════════════════════
{context_str}
════════════════════════════════════════
ตอบคำถามโดยอิงจากข้อมูลข้างต้นเท่านั้น"""
