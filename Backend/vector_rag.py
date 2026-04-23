"""
vector_rag.py  —  Vector RAG Engine (LangChain + OpenAI Embeddings) v4
═══════════════════════════════════════════════════════════════════════
การเปลี่ยนแปลงจาก v3:
  - Embedding  : sentence-transformers → OpenAIEmbeddings (text-embedding-3-small)
  - Retriever  : cosine top_k → MMR (Maximal Marginal Relevance)
                 หลีกเลี่ยงดึง chunk ที่ซ้ำกัน/ใกล้กันเกินไป
  - VectorStore: chromadb raw API → LangChain Chroma wrapper
  - Interface  : เหมือนเดิมทุกอย่าง (drop-in replacement สำหรับ chatbot.py)

Install:
  pip install langchain langchain-openai langchain-chroma chromadb

Run Build_vector_db.py ใหม่ก่อนใช้งาน:
  python scripts/Build_vector_db.py
"""

import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE       = Path(__file__).parent / "data"
VECTOR_DIR = BASE / "vector_db"
ID_MAP_F   = BASE / "processed" / "id_to_row.json"

# ── Lazy-loaded singletons ──────────────────────────────────────────────
_vectorstore = None
_retriever   = None
_id_map      = None


def _load():
    """โหลด VectorStore + id_map ครั้งเดียว (lazy init)"""
    global _vectorstore, _retriever, _id_map
    if _vectorstore is not None:
        return

    if not VECTOR_DIR.exists():
        raise FileNotFoundError(
            f"Vector DB ไม่พบที่ {VECTOR_DIR}\n"
            "กรุณารัน: python scripts/Build_vector_db.py"
        )

    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_chroma import Chroma
    except ImportError as e:
        raise ImportError(
            f"Missing package: {e}\n"
            "pip install langchain langchain-openai langchain-chroma chromadb"
        )

    print("[VectorRAG] Loading OpenAIEmbeddings (text-embedding-3-small) ...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    print(f"[VectorRAG] Connecting to ChromaDB at {VECTOR_DIR} ...")
    _vectorstore = Chroma(
        collection_name="exotic_pets",
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DIR),
    )
    print(f"[VectorRAG] {_vectorstore._collection.count()} docs ✓")

    # MMR retriever — ดึง fetch_k=10 แล้วเลือก k=3 ที่ diverse ที่สุด
    # lambda_mult: 0.7 = เน้น relevance มากกว่า diversity (0=diversity, 1=relevance)
    _retriever = _vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 3,
            "fetch_k": 10,
            "lambda_mult": 0.7,
        },
    )

    with open(ID_MAP_F, encoding="utf-8") as f:
        _id_map = json.load(f)

    print("[VectorRAG] Ready (LangChain MMR)")


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API  —  Interface เหมือน v3 ทุกอย่าง
# ══════════════════════════════════════════════════════════════════════

def retrieve(query: str, top_k: int = 3, threshold: float = 0.0,
             where: dict = None):
    """
    ค้นหาด้วย MMR แล้วคืน list ของ {row, score}
    - threshold: ใช้น้อยลงเพราะ MMR กรอง diversity ให้แล้ว
    - where: filter metadata (category) — ยังรองรับเหมือนเดิม
    """
    _load()

    if where:
        # LangChain Chroma รองรับ filter ผ่าน search_kwargs["filter"]
        docs_scores = _vectorstore.similarity_search_with_relevance_scores(
            query,
            k=top_k,
            filter=where,
        )
    else:
        docs_scores = _vectorstore.similarity_search_with_relevance_scores(
            query, k=top_k
        )

    results = []
    for doc, score in docs_scores:
        if score < threshold:
            continue
        species_id = doc.metadata.get("species_id", "")
        row = _id_map.get(species_id)
        if row:
            results.append({"row": row, "score": round(float(score), 4)})

    # ถ้าไม่ได้ filter → ใช้ MMR re-rank เพื่อ diversity
    if not where and _retriever:
        try:
            mmr_docs = _retriever.invoke(query)
            mmr_ids  = {d.metadata.get("species_id") for d in mmr_docs}
            # เรียงให้ MMR docs ขึ้นก่อน
            results.sort(key=lambda r: (
                0 if r["row"].get("id") in mmr_ids else 1, -r["score"]
            ))
        except Exception:
            pass  # fallback to similarity order

    return results


def retrieve_with_filter(query: str, category: str = None,
                         top_k: int = 5, threshold: float = 0.0):
    """Hybrid: filter by category metadata + MMR ranking"""
    where = {"category": category} if category else None
    return retrieve(query, top_k=top_k, threshold=threshold, where=where)


def build_context(query: str, top_k: int = 3, threshold: float = 0.0):
    """
    Returns (context_str, sources, has_data)
    context_str = chunk_text ของแต่ละ matched species
    Interface เหมือน v3 ทุก field
    """
    results = retrieve(query, top_k=top_k, threshold=threshold)
    if not results:
        return "", [], False

    parts, sources = [], []
    for i, r in enumerate(results):
        row, score = r["row"], r["score"]
        chunk = row.get("chunk_text", "")
        parts.append(
            f"--- ข้อมูลสัตว์ {i+1} (ความเกี่ยวข้อง {score*100:.0f}%) ---\n{chunk}"
        )
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
    return (
        f"{base}\n\n[DATA]\n{context_str}\n\n"
        "ตอบคำถามโดยอิงจากข้อมูลข้างต้นเท่านั้น"
    )
