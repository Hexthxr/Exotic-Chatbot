#!/usr/bin/env python3
"""
test_vector_rag.py  —  ทดสอบ Vector RAG vs TF-IDF RAG
════════════════════════════════════════════════════════
รันหลังจาก build_vector_db.py เสร็จแล้ว:
  python scripts/test_vector_rag.py
"""
 
import sys
from pathlib import Path
 
# เพิ่ม Backend/ เข้า path เพื่อ import vector_rag และ rag ได้
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
 
from vector_rag import retrieve as vec_retrieve
from rag        import retrieve as tfidf_retrieve
 
TEST_QUERIES = [
    # ภาษาไทย
    "บอลไพธอนเลี้ยงยากไหม",
    "สัตว์ที่เหมาะสำหรับมือใหม่",
    "กิ้งก่ามีพิษไหม",
    "axolotl ดูแลยังไง",
    "นกแก้วพูดได้ไหม",
    # ภาษาอังกฤษ
    "best beginner reptile",
    "leopard gecko care",
    "dangerous venomous snake",
    # Typo / ใกล้เคียง
    "บอลไพทอน",           # typo
    "อะโซลอตเติ้ล",       # phonetic Thai
    # Semantic (ไม่มีชื่อสัตว์ตรงๆ)
    "สัตว์ที่อาบน้ำไม่ต้องบ่อย",
    "สัตว์ราคาไม่แพงเลี้ยงง่าย",
    "สัตว์กลางคืนที่เงียบ",
]
 
print("=" * 70)
print("  VECTOR RAG vs TF-IDF RAG — Comparison Test")
print("=" * 70)
 
for q in TEST_QUERIES:
    vec_res   = vec_retrieve(q, top_k=3, threshold=0.0)    # ไม่ threshold เพื่อดูทุกตัว
    tfidf_res = tfidf_retrieve(q, top_k=3, threshold=0.0)
 
    vec_names   = [f"{r['row'].get('common_name_en','-')}({r['score']:.2f})"   for r in vec_res]
    tfidf_names = [f"{r['row'].get('common_name_en','-')}({r['score']:.3f})"   for r in tfidf_res]
 
    print(f"\n  Query : '{q}'")
    print(f"  Vector: {vec_names}")
    print(f"  TF-IDF: {tfidf_names}")
 
print("\n" + "=" * 70)
print("  Test complete.")
print("=" * 70)
 