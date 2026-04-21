"""
rag.py  —  TF-IDF RAG Engine (Chunking Edition v3)
═══════════════════════════════════════════════════
- 1 species = 1 chunk (chunk_text ครบทุก field)
- TF-IDF ใช้ _search_text สำหรับ retrieval
- build_context() return chunk_text โดยตรง
"""

import json, re, unicodedata, math
from pathlib import Path

BASE    = Path(__file__).parent / "data" / "processed"
CLEAN_F = BASE / "clean.json"
VOCAB_F = BASE / "tfidf_vocab.json"

_dataset    = None
_vocab      = None
_idf        = None
_index_vecs = None


def _load():
    global _dataset, _vocab, _idf, _index_vecs
    if _dataset is not None: return
    print("[RAG] Loading dataset …")
    with open(CLEAN_F, encoding="utf-8") as f:
        _dataset = json.load(f)["rows"]
    with open(VOCAB_F, encoding="utf-8") as f:
        v = json.load(f)
    _vocab = v["vocabulary"]
    _idf   = v["idf"]
    _index_vecs = [_vectorize(r["_search_text"]) for r in _dataset]
    print(f"[RAG] Ready — {len(_dataset)} chunks indexed")


def _normalize(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _char_ngrams(text):
    padded = f" {text} "
    counts = {}
    for n in range(2, 5):
        for i in range(len(padded)-n+1):
            g = padded[i:i+n]
            counts[g] = counts.get(g, 0) + 1
    return counts


def _vectorize(text):
    _load()
    ng    = _char_ngrams(_normalize(text))
    total = sum(ng.values()) or 1
    vec   = {}
    for g, cnt in ng.items():
        idx = _vocab.get(g)
        if idx is not None:
            vec[idx] = math.log(1 + cnt/total) * _idf[idx]
    return vec


def _cosine(a, b):
    dot   = sum(a[k]*b[k] for k in a if k in b)
    normA = math.sqrt(sum(v*v for v in a.values()))
    normB = math.sqrt(sum(v*v for v in b.values()))
    return dot/(normA*normB) if normA*normB else 0.0


def retrieve(query: str, top_k: int = 3, threshold: float = 0.05):
    _load()
    q_vec  = _vectorize(query)
    scored = [{"row": r, "score": _cosine(q_vec, iv)}
              for r, iv in zip(_dataset, _index_vecs)]
    scored.sort(key=lambda x: -x["score"])
    return [s for s in scored[:top_k] if s["score"] >= threshold]


def build_context(query: str, top_k: int = 3, threshold: float = 0.05):
    results = retrieve(query, top_k, threshold)
    if not results: return "", [], False

    parts, sources = [], []
    for i, r in enumerate(results):
        row, score = r["row"], r["score"]
        # ใช้ chunk_text ที่สร้างไว้แล้วใน data_prep
        chunk = row.get("chunk_text", "")
        parts.append(f"--- ข้อมูลสัตว์ {i+1} (ความเกี่ยวข้อง {score*100:.0f}%) ---\n{chunk}")
        sources.append({
            "id":      row.get("id"),
            "name_en": row.get("common_name_en"),
            "name_th": row.get("common_name_th"),
            "sci":     row.get("scientific_name"),
            "score":   round(score, 4),
        })
    return "\n\n".join(parts), sources, True


def build_system_prompt(context_str: str = "") -> str:
    base = ("คุณคือ ExoticMate ผู้เชี่ยวชาญสัตว์ exotic "
            "ตอบเฉพาะข้อมูลในฐานข้อมูลเท่านั้น ห้ามสร้างข้อมูลใหม่ "
            "ตอบภาษาไทย กระชับ เป็นมิตร")
    if not context_str:
        return base + "\n\nไม่พบข้อมูลที่เกี่ยวข้องในฐานข้อมูล"
    return f"{base}\n\n[ข้อมูลจากฐานข้อมูล]\n{context_str}\n\nตอบจากข้อมูลข้างต้นเท่านั้น"
