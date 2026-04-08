"""
vector_rag.py  —  Vector RAG Engine (ChromaDB + Sentence Transformers)
════════════════════════════════════════════════════════════════════════
แทนที่ TF-IDF ด้วย semantic search จาก dense vector embeddings
 
Model  : paraphrase-multilingual-MiniLM-L12-v2
DB     : ChromaDB (persistent local)
Dim    : 384
 
Public API (เหมือน rag.py เดิม — drop-in replacement):
  retrieve(query, top_k, threshold)  → list[{row, score}]
  build_context(query, top_k)        → (context_str, sources, has_data)
  build_system_prompt(context_str)   → str
"""
 
import json
from pathlib import Path
 
BASE        = Path(__file__).parent / "data"
VECTOR_DIR  = BASE / "vector_db"
ID_MAP_F    = BASE / "processed" / "id_to_row.json"
 
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
 
# ── Lazy globals ───────────────────────────────────────────────────────
_model      = None
_collection = None
_id_map     = None   # dict: id → full row dict
 
 
def _load():
    global _model, _collection, _id_map
    if _model is not None:
        return
 
    # ── ตรวจว่ามีไฟล์ DB หรือยัง ────────────────────────────────────
    if not VECTOR_DIR.exists():
        raise FileNotFoundError(
            f"Vector DB ไม่พบที่ {VECTOR_DIR}\n"
            "กรุณารัน: python scripts/build_vector_db.py ก่อน"
        )
 
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            f"Missing package: {e}\n"
            "ติดตั้งด้วย: pip install chromadb sentence-transformers"
        )
 
    print(f"[VectorRAG] Loading model: {MODEL_NAME} …")
    _model = SentenceTransformer(MODEL_NAME)
 
    print(f"[VectorRAG] Connecting to ChromaDB at {VECTOR_DIR} …")
    client      = chromadb.PersistentClient(path=str(VECTOR_DIR))
    _collection = client.get_collection("exotic_pets")
    print(f"[VectorRAG] Collection loaded — {_collection.count()} docs ✓")
 
    print(f"[VectorRAG] Loading id_to_row map …")
    with open(ID_MAP_F, encoding="utf-8") as f:
        _id_map = json.load(f)
    print(f"[VectorRAG] Ready.")
 
 
# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: retrieve
# ══════════════════════════════════════════════════════════════════════
def retrieve(query: str, top_k: int = 3, threshold: float = 0.25,
             where: dict = None):
    """
    Args:
      query     : คำถามจากผู้ใช้
      top_k     : จำนวนผลลัพธ์สูงสุด
      threshold : cosine similarity ขั้นต่ำ (0-1)
      where     : ChromaDB metadata filter เช่น {"category": "Bird"}
 
    Returns:
      list of {"row": dict, "score": float}
      เรียงจากมากไปน้อย
    """
    _load()
 
    q_vec  = _model.encode(query, normalize_embeddings=True).tolist()
    kwargs = dict(query_embeddings=[q_vec], n_results=top_k)
    if where:
        kwargs["where"] = where
 
    res = _collection.query(**kwargs)
 
    results = []
    for doc_id, distance, meta in zip(
        res["ids"][0], res["distances"][0], res["metadatas"][0]
    ):
        # ChromaDB cosine → distance = 1 - similarity
        score = 1.0 - distance
        if score < threshold:
            continue
        row = _id_map.get(doc_id)
        if row:
            results.append({"row": row, "score": round(score, 4)})
 
    return results
 
 
# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: retrieve_with_filter  (ใช้ metadata filter + semantic)
# ══════════════════════════════════════════════════════════════════════
def retrieve_with_filter(query: str, category: str = None,
                         top_k: int = 5, threshold: float = 0.20):
    """
    Hybrid: filter by category metadata + rank by semantic similarity
    เหมาะกับ query แบบ "งูเลี้ยงง่าย" หรือ "นกไม่มีพิษ"
    """
    where = None
    if category:
        where = {"category": {"$eq": category}}
    return retrieve(query, top_k=top_k, threshold=threshold, where=where)
 
 
# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: build_context
# ══════════════════════════════════════════════════════════════════════
def build_context(query: str, top_k: int = 3, threshold: float = 0.25):
    """
    Returns (context_str, sources, has_data) — เหมือน rag.py เดิม
    """
    results = retrieve(query, top_k=top_k, threshold=threshold)
    if not results:
        return "", [], False
 
    parts   = []
    sources = []
 
    for i, r in enumerate(results):
        row   = r["row"]
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
            "id":      row.get("id"),
            "name_en": row.get("common_name_en"),
            "name_th": row.get("common_name_th"),
            "sci":     row.get("scientific_name"),
            "score":   score,
        })
 
    return "\n".join(parts), sources, True
 
 
# ══════════════════════════════════════════════════════════════════════
#  PUBLIC: build_system_prompt  (เหมือน rag.py เดิม)
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
 