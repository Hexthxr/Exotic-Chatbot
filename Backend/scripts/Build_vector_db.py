#!/usr/bin/env python3
"""
Build_vector_db.py  —  Rebuild ChromaDB Vector Database (v3)
═══════════════════════════════════════════════════════════════
Input  : data/processed/clean.json  (275 species + chunk_text)
Output : data/vector_db/            (ChromaDB persistent)

Model  : paraphrase-multilingual-MiniLM-L12-v2  (~400MB, download once)
Dim    : 384 (multilingual Thai+EN support)

Install:
  pip install chromadb sentence-transformers

Run once:
  python scripts/Build_vector_db.py
"""

import json, time
from pathlib import Path

BASE       = Path(__file__).parent.parent / "data"
CLEAN_F    = BASE / "processed" / "clean.json"
VECTOR_DIR = BASE / "vector_db"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"\n❌ Missing package: {e}")
    print("   pip install chromadb sentence-transformers\n")
    raise SystemExit(1)

# 1. Load data
print("▶ Loading clean.json …")
with open(CLEAN_F, encoding="utf-8") as f:
    data = json.load(f)
rows = data["rows"]
print(f"  Loaded {len(rows)} chunks")

# 2. Load embedding model
print(f"\n▶ Loading embedding model: {MODEL_NAME}")
print("  (ครั้งแรกจะ download ~400MB — รอสักครู่)")
model = SentenceTransformer(MODEL_NAME)
print(f"  Model loaded ✓  dim={model.get_sentence_embedding_dimension()}")

# 3. Build embed text per chunk
# ใช้ chunk_text ทั้งหมด → semantic search ครบทุก field
def build_embed_text(r: dict) -> str:
    """
    ใช้ chunk_text (structured) เป็น embed text หลัก
    เพิ่มชื่อซ้ำเพื่อเพิ่มน้ำหนักชื่อสัตว์ใน vector space
    """
    name_boost = " ".join([
        r.get("common_name_th", ""),
        r.get("common_name_th", ""),     # repeat
        r.get("common_name_en", ""),
        r.get("common_name_en", ""),
        r.get("scientific_name", ""),
    ])
    # ใช้ chunk_text ซึ่งมีทุก field แล้ว
    chunk = r.get("chunk_text", "")
    return f"{name_boost}\n\n{chunk}"

texts     = [build_embed_text(r) for r in rows]
ids       = [r["id"] for r in rows]
metadatas = [
    {
        "category":          r.get("category", ""),
        "subcategory":       r.get("subcategory", ""),
        "common_name_en":    r.get("common_name_en", ""),
        "common_name_th":    r.get("common_name_th", ""),
        "scientific_name":   r.get("scientific_name", ""),
        "care_level":        r.get("care_level", ""),
        "danger_level":      r.get("danger_level", ""),
        "venomous_or_toxic": r.get("venomous_or_toxic", ""),
        "beginner_friendly": r.get("beginner_friendly", ""),
        "diet":              r.get("diet", ""),
        "origin_region":     r.get("origin_region", ""),
        # ใหม่: legal bucket สำหรับ filter
        "legal_bucket":      r.get("legal_species_bucket_v6", ""),
        "illegal_flag":      r.get("illegal_clear_flag_th", ""),
    }
    for r in rows
]

print(f"\n  Sample embed text ({rows[0]['common_name_en']}):")
print(f"  {texts[0][:120]}…\n")

# 4. Generate embeddings
BATCH = 32
print(f"▶ Embedding {len(texts)} chunks (batch={BATCH}) …")
t0 = time.time()
embeddings = []
for i in range(0, len(texts), BATCH):
    batch = texts[i:i+BATCH]
    vecs  = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
    embeddings.extend(vecs.tolist())
    done = min(i+BATCH, len(texts))
    print(f"  [{done:>3}/{len(texts)}] {done/len(texts)*100:.0f}%", end="\r")
print(f"\n  Embedding done in {time.time()-t0:.1f}s ✓  dim={len(embeddings[0])}")

# 5. Build ChromaDB
print(f"\n▶ Building ChromaDB at: {VECTOR_DIR}")
client = chromadb.PersistentClient(path=str(VECTOR_DIR))

# ลบ collection เก่า → rebuild สะอาด
try:
    client.delete_collection("exotic_pets")
    print("  (ลบ collection เก่า → rebuild ใหม่)")
except Exception:
    pass

collection = client.create_collection(
    name="exotic_pets",
    metadata={"hnsw:space": "cosine"},
)

CHROMA_BATCH = 50
for i in range(0, len(ids), CHROMA_BATCH):
    sl = slice(i, i+CHROMA_BATCH)
    collection.add(
        ids=ids[sl],
        embeddings=embeddings[sl],
        documents=texts[sl],
        metadatas=metadatas[sl],
    )

print(f"  Indexed {collection.count()} documents ✓")

# 6. Sanity test
print("\n▶ Sanity retrieval test …")
test_queries = [
    "บอลไพธอนเลี้ยงยากไหม",
    "gecko for beginners",
    "แมงมุมทารันทูล่า",
    "axolotl ราคาเท่าไหร่",
    "นกเลี้ยงง่าย",
]
for q in test_queries:
    q_vec = model.encode(q, normalize_embeddings=True).tolist()
    res   = collection.query(query_embeddings=[q_vec], n_results=2)
    names = [f"{m['common_name_th']} ({m['common_name_en']})"
             for m in res["metadatas"][0]]
    print(f"  '{q}' → {names}")

# 7. Save id_to_row mapping
id_map_path = BASE / "processed" / "id_to_row.json"
id_map = {r["id"]: r for r in rows}
with open(id_map_path, "w", encoding="utf-8") as f:
    json.dump(id_map, f, ensure_ascii=False)

print(f"\n  id_to_row.json saved ({len(id_map)} entries)")
print("\n" + "="*55)
print("  VECTOR DB BUILD COMPLETE")
print("="*55)
print(f"  Collection  : exotic_pets")
print(f"  Documents   : {collection.count()}")
print(f"  Model       : {MODEL_NAME}")
print(f"  DB path     : {VECTOR_DIR}")
print(f"  id_to_row   : {id_map_path.name}")
print("="*55)
print("\n✅ Vector DB พร้อมใช้งาน — vector_rag.py จะโหลดอัตโนมัติ\n")
