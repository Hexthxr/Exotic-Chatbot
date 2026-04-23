#!/usr/bin/env python3
"""
Build_vector_db.py  —  Rebuild ChromaDB Vector Database (LangChain v4)
═══════════════════════════════════════════════════════════════════════
การเปลี่ยนแปลงจาก v3:
  - Embedding  : sentence-transformers → OpenAIEmbeddings (text-embedding-3-small)
  - Chunking   : 1 species = 1 doc (เหมือนเดิม แต่ embed ด้วย OpenAI)
  - VectorStore: chromadb raw API → LangChain Chroma wrapper
  - Metadata   : เพิ่ม species_id เพื่อ lookup กลับไปหา full row ใน id_to_row.json

Input  : data/processed/clean.json
Output : data/vector_db/  (ChromaDB persistent — LangChain format)

Install:
  pip install langchain langchain-openai langchain-chroma chromadb python-dotenv

Run:
  python scripts/Build_vector_db.py
"""

import os, json, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE       = Path(__file__).parent.parent / "data"
CLEAN_F    = BASE / "processed" / "clean.json"
VECTOR_DIR = BASE / "vector_db"
ID_MAP_F   = BASE / "processed" / "id_to_row.json"

# ── Validate env ────────────────────────────────────────────────────────
if not os.getenv("OPENAI_API_KEY"):
    print("\n❌ OPENAI_API_KEY ไม่พบใน .env")
    print("   กรุณาเพิ่ม OPENAI_API_KEY=sk-... ใน Backend/.env\n")
    raise SystemExit(1)

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
except ImportError as e:
    print(f"\n❌ Missing package: {e}")
    print("   pip install langchain langchain-openai langchain-chroma chromadb\n")
    raise SystemExit(1)

# ══════════════════════════════════════════════════════════════════════
#  Step 1: Load clean.json
# ══════════════════════════════════════════════════════════════════════
print("▶ Loading clean.json ...")
with open(CLEAN_F, encoding="utf-8") as f:
    data = json.load(f)
rows = data["rows"]
print(f"  Loaded {len(rows)} species")

# ══════════════════════════════════════════════════════════════════════
#  Step 2: Build LangChain Documents
#  page_content = chunk_text (structured markdown ต่อ species)
#  metadata     = fields สำคัญสำหรับ filter + lookup
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Building LangChain Documents ...")

def build_embed_text(r: dict) -> str:
    """
    ข้อความสำหรับ embed:
    ซ้ำชื่อสัตว์ที่หัวเพื่อเพิ่มน้ำหนัก → ค้นหาชื่อได้แม่นขึ้น
    ตามด้วย chunk_text ที่มีข้อมูลครบทุก field
    """
    name_boost = " ".join([
        r.get("common_name_th", ""),
        r.get("common_name_th", ""),   # repeat x2
        r.get("common_name_en", ""),
        r.get("common_name_en", ""),
        r.get("scientific_name", ""),
    ])
    return f"{name_boost}\n\n{r.get('chunk_text', '')}"

docs = []
for r in rows:
    doc = Document(
        page_content=build_embed_text(r),
        metadata={
            # ── lookup key ──────────────────────────────────────
            "species_id":        r.get("id", ""),
            # ── filter fields ───────────────────────────────────
            "category":          r.get("category", ""),
            "subcategory":       r.get("subcategory", ""),
            "care_level":        r.get("care_level", ""),
            "danger_level":      r.get("danger_level", ""),
            "beginner_friendly": r.get("beginner_friendly", ""),
            "venomous_or_toxic": r.get("venomous_or_toxic", ""),
            "legal_bucket":      r.get("legal_species_bucket_v6", ""),
            "illegal_flag":      r.get("illegal_clear_flag_th", ""),
            # ── display fields ──────────────────────────────────
            "common_name_en":    r.get("common_name_en", ""),
            "common_name_th":    r.get("common_name_th", ""),
            "scientific_name":   r.get("scientific_name", ""),
        },
    )
    docs.append(doc)

print(f"  Built {len(docs)} documents")
print(f"\n  Sample doc ({rows[0]['common_name_en']}):")
print(f"  page_content[:150]: {docs[0].page_content[:150]}...")
print(f"  metadata keys: {list(docs[0].metadata.keys())}")

# ══════════════════════════════════════════════════════════════════════
#  Step 3: Embed + Store ใน ChromaDB ผ่าน LangChain
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Initializing OpenAIEmbeddings (text-embedding-3-small) ...")
print("  (แต่ละ species จะถูก embed ผ่าน OpenAI API — ใช้เวลาสักครู่)")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

# ลบ Vector DB เก่าออกก่อน rebuild สะอาด
if VECTOR_DIR.exists():
    import shutil
    shutil.rmtree(VECTOR_DIR)
    print(f"  (ลบ vector_db เก่า → rebuild ใหม่)")
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# Embed + index ทั้งหมดผ่าน LangChain (batch อัตโนมัติ)
print(f"\n▶ Embedding + Indexing {len(docs)} documents ...")
print("  OpenAI text-embedding-3-small: ~1500 tokens/doc, batch=100")
t0 = time.time()

BATCH = 50   # ส่ง OpenAI API ทีละ 50 docs เพื่อหลีกเลี่ยง rate limit
vectorstore = None
for i in range(0, len(docs), BATCH):
    batch = docs[i:i+BATCH]
    done  = min(i + BATCH, len(docs))
    print(f"  [{done:>3}/{len(docs)}] embedding batch {i//BATCH + 1} ...", end="\r")

    if vectorstore is None:
        vectorstore = Chroma.from_documents(
            documents=batch,
            embedding=embeddings,
            collection_name="exotic_pets",
            persist_directory=str(VECTOR_DIR),
        )
    else:
        vectorstore.add_documents(batch)

    time.sleep(0.3)   # หลีกเลี่ยง rate limit

print(f"\n  Done in {time.time()-t0:.1f}s")
print(f"  Indexed: {vectorstore._collection.count()} documents ✓")

# ══════════════════════════════════════════════════════════════════════
#  Step 4: Save id_to_row.json (lookup map สำหรับ vector_rag.py)
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Saving id_to_row.json ...")
id_map = {r["id"]: r for r in rows}
with open(ID_MAP_F, "w", encoding="utf-8") as f:
    json.dump(id_map, f, ensure_ascii=False)
print(f"  Saved {len(id_map)} entries → {ID_MAP_F.name}")

# ══════════════════════════════════════════════════════════════════════
#  Step 5: Sanity Test — MMR retrieval
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Sanity test (MMR retrieval) ...")

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.7},
)

test_queries = [
    "บอลไพธอนเลี้ยงยากไหม",
    "gecko for beginners",
    "แมงมุมทารันทูล่า",
    "axolotl ราคาเท่าไหร่",
    "นกเลี้ยงง่าย",
    "สัตว์มีพิษที่เลี้ยงได้",
]

for q in test_queries:
    results = retriever.invoke(q)
    names = [
        f"{d.metadata.get('common_name_th', '?')} ({d.metadata.get('common_name_en', '?')})"
        for d in results
    ]
    print(f"  '{q}'")
    print(f"    → {names}\n")

# ══════════════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  VECTOR DB BUILD COMPLETE (LangChain v4)")
print("=" * 60)
print(f"  Collection    : exotic_pets")
print(f"  Documents     : {vectorstore._collection.count()}")
print(f"  Embedding     : text-embedding-3-small (OpenAI)")
print(f"  Retriever     : MMR (k=3, fetch_k=10, lambda=0.7)")
print(f"  DB path       : {VECTOR_DIR}")
print(f"  id_to_row.json: {ID_MAP_F.name}")
print("=" * 60)
print("\n✅ Vector DB พร้อมใช้งาน — เริ่ม Flask server ได้เลย\n")
