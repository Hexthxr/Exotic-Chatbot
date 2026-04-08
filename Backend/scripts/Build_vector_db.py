#!/usr/bin/env python3
"""
build_vector_db.py  —  สร้าง ChromaDB Vector Database
═══════════════════════════════════════════════════════
ใช้ sentence-transformers model: paraphrase-multilingual-MiniLM-L12-v2
รองรับภาษาไทย + อังกฤษ + ชื่อวิทยาศาสตร์
 
Input  : data/processed/clean.json  (258 species)
Output : data/vector_db/            (ChromaDB persistent storage)
 
ติดตั้งก่อนรัน:
  pip install chromadb sentence-transformers
 
รันครั้งเดียว:
  python scripts/build_vector_db.py
"""
 
import json, time
from pathlib import Path
 
# ── Paths ───────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent.parent / "data"
CLEAN_F    = BASE / "processed" / "clean.json"
VECTOR_DIR = BASE / "vector_db"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
 
# ══════════════════════════════════════════════════════════════════════
#  IMPORTS (ให้ error ชัดเจนถ้ายังไม่ได้ install)
# ══════════════════════════════════════════════════════════════════════
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"\n❌ Missing package: {e}")
    print("   กรุณาติดตั้งก่อน:\n   pip install chromadb sentence-transformers\n")
    raise SystemExit(1)
 
 
# ══════════════════════════════════════════════════════════════════════
#  1. โหลดข้อมูล
# ══════════════════════════════════════════════════════════════════════
print("▶ Loading clean.json …")
with open(CLEAN_F, encoding="utf-8") as f:
    data = json.load(f)
rows = data["rows"]
print(f"  Loaded {len(rows)} species")
 
 
# ══════════════════════════════════════════════════════════════════════
#  2. โหลด Embedding Model
# ══════════════════════════════════════════════════════════════════════
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
print(f"\n▶ Loading embedding model: {MODEL_NAME}")
print("  (ครั้งแรกจะ download ~400MB — รอสักครู่)")
model = SentenceTransformer(MODEL_NAME)
print(f"  Model loaded ✓  (dim={model.get_sentence_embedding_dimension()})")
 
 
# ══════════════════════════════════════════════════════════════════════
#  3. สร้าง Rich Text สำหรับ Embed
#     รวมข้อมูลสำคัญหลายฟิลด์เพื่อให้ semantic search แม่นยำ
# ══════════════════════════════════════════════════════════════════════
def build_embed_text(r: dict) -> str:
    """สร้าง text ที่มีความหมายครบถ้วนสำหรับ embedding"""
    parts = [
        # ชื่อ (น้ำหนักสูง — repeat เพื่อเน้น)
        r.get("common_name_th", ""),
        r.get("common_name_th", ""),     # repeat เพื่อเพิ่มน้ำหนัก
        r.get("common_name_en", ""),
        r.get("common_name_en", ""),
        r.get("scientific_name", ""),
 
        # หมวดหมู่
        r.get("category", ""),
        r.get("subcategory", ""),
 
        # ลักษณะสัตว์
        f"ถิ่นกำเนิด {r.get('origin_region', '')}",
        f"ขนาด {r.get('typical_size_cm', '')} เซนติเมตร",
        f"อายุขัย {r.get('lifespan_years', '')} ปี",
        f"อาหาร {r.get('diet', '')}",
        f"ที่อยู่อาศัย {r.get('habitat', '')}",
        f"พฤติกรรม {r.get('temperament', '')}",
        f"หากิน{r.get('activity_pattern', '')}",
 
        # การดูแล
        f"ระดับการดูแล {r.get('care_level', '')}",
        f"ระดับการจับ {r.get('handling_level', '')}",
        f"เหมาะมือใหม่ {r.get('beginner_friendly', '')}",
        f"ที่พัก {r.get('recommended_enclosure', '')}",
        f"อุณหภูมิ {r.get('temperature_c_range', '')} องศา",
        f"ความชื้น {r.get('humidity_percent_range', '')} เปอร์เซ็นต์",
        f"สังคม {r.get('social_needs', '')}",
 
        # ความปลอดภัย
        f"อันตราย {r.get('danger_level', '')}",
        f"พิษ {r.get('venomous_or_toxic', '')}",
 
        # ราคา + กฎหมาย
        f"ราคา {r.get('estimated_price_range_thb', '')} บาท",
        r.get("possession_status_th", ""),
        r.get("legal_status_hint_th", ""),
        r.get("legal_note_th", ""),
        r.get("wildlife_law_category_th", ""),
    ]
    return " ".join(p for p in parts if p).strip()
 
 
texts    = [build_embed_text(r) for r in rows]
ids      = [r["id"] for r in rows]
metadatas = [
    {
        # เก็บฟิลด์สำคัญใน metadata สำหรับ filter
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
    }
    for r in rows
]
 
print(f"\n  Sample embed text (EXO001):")
print(f"  {texts[0][:120]}…\n")
 
 
# ══════════════════════════════════════════════════════════════════════
#  4. สร้าง Embeddings (batch)
# ══════════════════════════════════════════════════════════════════════
BATCH = 32
print(f"▶ Embedding {len(texts)} documents (batch={BATCH}) …")
t0         = time.time()
embeddings = []
 
for i in range(0, len(texts), BATCH):
    batch      = texts[i:i+BATCH]
    vecs       = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
    embeddings.extend(vecs.tolist())
    done = min(i + BATCH, len(texts))
    print(f"  [{done:>3}/{len(texts)}] {done/len(texts)*100:.0f}%", end="\r")
 
print(f"\n  Embedding done in {time.time()-t0:.1f}s ✓")
print(f"  Vector dim: {len(embeddings[0])}")
 
 
# ══════════════════════════════════════════════════════════════════════
#  5. สร้าง ChromaDB Collection
# ══════════════════════════════════════════════════════════════════════
print(f"\n▶ Building ChromaDB at: {VECTOR_DIR}")
 
client = chromadb.PersistentClient(path=str(VECTOR_DIR))
 
# ลบ collection เก่าถ้ามี (เพื่อ rebuild สะอาด)
try:
    client.delete_collection("exotic_pets")
    print("  (ลบ collection เก่าออกก่อน rebuild)")
except Exception:
    pass
 
# NOTE: ใส่เฉพาะ hnsw:space เท่านั้น — ChromaDB เวอร์ชันใหม่ไม่รับ M/ef_construction
collection = client.create_collection(
    name="exotic_pets",
    metadata={"hnsw:space": "cosine"},
)
 
# Upsert ทีละ batch
CHROMA_BATCH = 50
for i in range(0, len(ids), CHROMA_BATCH):
    sl = slice(i, i + CHROMA_BATCH)
    collection.add(
        ids=ids[sl],
        embeddings=embeddings[sl],
        documents=texts[sl],
        metadatas=metadatas[sl],
    )
 
print(f"  Indexed {collection.count()} documents ✓")
 
 
# ══════════════════════════════════════════════════════════════════════
#  6. Quick sanity test
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Quick retrieval test …")
test_queries = [
    "บอลไพธอนเลี้ยงยากไหม",
    "gecko for beginners",
    "สัตว์มีพิษอันตราย",
    "axolotl ราคาเท่าไหร่",
]
 
for q in test_queries:
    q_vec = model.encode(q, normalize_embeddings=True).tolist()
    res   = collection.query(query_embeddings=[q_vec], n_results=2)
    hits  = res["metadatas"][0]
    names = [f"{h['common_name_th']} ({h['common_name_en']})" for h in hits]
    print(f"  '{q}' → {names}")
 
 
# ══════════════════════════════════════════════════════════════════════
#  7. บันทึก metadata mapping (id → full row) สำหรับใช้ใน rag
# ══════════════════════════════════════════════════════════════════════
id_map_path = BASE / "processed" / "id_to_row.json"
id_map      = {r["id"]: r for r in rows}
with open(id_map_path, "w", encoding="utf-8") as f:
    json.dump(id_map, f, ensure_ascii=False)
print(f"\n  id_to_row.json saved ({len(id_map)} entries)")
 
print("\n" + "═"*55)
print("  VECTOR DB BUILD COMPLETE")
print("═"*55)
print(f"  Collection : exotic_pets")
print(f"  Documents  : {collection.count()}")
print(f"  Model      : {MODEL_NAME}")
print(f"  DB path    : {VECTOR_DIR}")
print(f"  id_to_row  : {id_map_path.name}")
print("═"*55)
print("\n✅ พร้อมใช้งาน! vector_rag.py จะโหลด DB นี้โดยอัตโนมัติ\n")
 