"""
vector_rag.py  —  Vector RAG Engine (ChromaDB + Sentence Transformers) v3
══════════════════════════════════════════════════════════════════════════
- ใช้ chunk_text เป็น context inject ให้โมเดล
- รองรับ category + legal_bucket filter
- drop-in replacement สำหรับ rag.py

Model : paraphrase-multilingual-MiniLM-L12-v2 (384 dim)
DB    : ChromaDB persistent (data/vector_db/)
"""

import json
from pathlib import Path

BASE       = Path(__file__).parent / "data"
VECTOR_DIR = BASE / "vector_db"
ID_MAP_F   = BASE / "processed" / "id_to_row.json"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model      = None
_collection = None
_id_map     = None


def _load():
    global _model, _collection, _id_map
    if _model is not None: return

    if not VECTOR_DIR.exists():
        raise FileNotFoundError(
            f"Vector DB ไม่พบที่ {VECTOR_DIR}\n"
            "กรุณารัน: python scripts/Build_vector_db.py"
        )
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(f"Missing: {e}\npip install chromadb sentence-transformers")

    print(f"[VectorRAG] Loading model: {MODEL_NAME} …")
    _model = SentenceTransformer(MODEL_NAME)

    print(f"[VectorRAG] Connecting to ChromaDB …")
    client      = chromadb.PersistentClient(path=str(VECTOR_DIR))
    _collection = client.get_collection("exotic_pets")
    print(f"[VectorRAG] {_collection.count()} docs ✓")

    with open(ID_MAP_F, encoding="utf-8") as f:
        _id_map = json.load(f)
    print("[VectorRAG] Ready.")


def retrieve(query: str, top_k: int = 3, threshold: float = 0.25,
             where: dict = None):
    _load()
    q_vec  = _model.encode(query, normalize_embeddings=True).tolist()
    kwargs = {"query_embeddings": [q_vec], "n_results": top_k}
    if where:
        kwargs["where"] = where

    res     = _collection.query(**kwargs)
    results = []
    for doc_id, dist, meta in zip(
            res["ids"][0], res["distances"][0], res["metadatas"][0]):
        score = 1.0 - dist   # cosine distance → similarity
        if score < threshold: continue
        row = _id_map.get(doc_id)
        if row:
            results.append({"row": row, "score": round(score, 4)})
    return results


def retrieve_with_filter(query: str, category: str = None,
                         top_k: int = 5, threshold: float = 0.20):
    """Hybrid: filter by category metadata + semantic ranking"""
    where = {"category": {"$eq": category}} if category else None
    return retrieve(query, top_k=top_k, threshold=threshold, where=where)


def build_context(query: str, top_k: int = 3, threshold: float = 0.25):
    """
    Returns (context_str, sources, has_data)
    context_str = chunk_text ของแต่ละ matched species
    """
    results = retrieve(query, top_k=top_k, threshold=threshold)
    if not results: return "", [], False

    parts, sources = [], []
    for i, r in enumerate(results):
        row, score = r["row"], r["score"]
        # ใช้ chunk_text ที่มีข้อมูลครบทุก field รวม legal v6
        chunk = row.get("chunk_text", "")
        parts.append(f"--- ข้อมูลสัตว์ {i+1} (ความเกี่ยวข้อง {score*100:.0f}%) ---\n{chunk}")
        sources.append({
            "id":      row.get("id"),
            "name_en": row.get("common_name_en"),
            "name_th": row.get("common_name_th"),
            "sci":     row.get("scientific_name"),
            "score":   score,
        })
    return "\n\n".join(parts), sources, True


def build_system_prompt(context_str: str = "") -> str:
    base = (
        "คุณคือ ExoticMate ผู้เชี่ยวชาญด้านสัตว์ exotic\n"
        "กฎ: ตอบเฉพาะข้อมูลใน [DATA] เท่านั้น ห้ามสร้างข้อมูลใหม่ "
        "ตอบภาษาไทย กระชับ เป็นมิตร"
    )
    if not context_str:
        return base + "\n\nไม่พบข้อมูลที่เกี่ยวข้อง กรุณาแจ้งผู้ใช้"
    return (f"{base}\n\n[DATA]\n{context_str}\n\n"
            "ตอบคำถามโดยอิงจากข้อมูลข้างต้นเท่านั้น")
