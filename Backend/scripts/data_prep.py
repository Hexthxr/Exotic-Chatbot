#!/usr/bin/env python3
"""
data_prep.py  —  Data Preparation Pipeline
════════════════════════════════════════════
Input  : data/exotic_pets.csv  (260 species)
Output : data/processed/
  ├── clean.json          cleaned full dataset
  ├── train.json          80% split
  ├── test.json           20% split
  ├── tfidf_vocab.json    TF-IDF vocabulary + IDF weights
  └── eval_report.json    quick retrieval sanity check

Steps:
  1. Load & validate CSV
  2. Clean / normalize fields
  3. Build rich search text per row
  4. Deduplication check (scientific name)
  5. Train / Test split (stratified by category)
  6. Build TF-IDF index over ALL rows
  7. Quick self-retrieval evaluation
  8. Save artefacts
"""

import csv, json, re, unicodedata, sys
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

# ── paths ──────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent.parent / "data"
PROC   = BASE / "processed"
PROC.mkdir(exist_ok=True)

CSV_IN   = BASE / "exotic_pets.csv"
CLEAN    = PROC / "clean.json"
TRAIN    = PROC / "train.json"
TEST     = PROC / "test.json"
VOCAB    = PROC / "tfidf_vocab.json"
REPORT   = PROC / "eval_report.json"

# ══════════════════════════════════════════════════════════════════════
#  1. LOAD
# ══════════════════════════════════════════════════════════════════════
print("▶ Loading CSV …")
rows = []
with open(CSV_IN, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"  Loaded {len(rows)} rows | columns: {len(reader.fieldnames)}")

# ══════════════════════════════════════════════════════════════════════
#  2. CLEAN & NORMALIZE
# ══════════════════════════════════════════════════════════════════════
def norm(text: str) -> str:
    """Basic normalization."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Fields we keep (all non-empty)
KEEP = [
    "id", "category", "subcategory",
    "common_name_en", "common_name_th", "scientific_name",
    "origin_region", "typical_size_cm", "lifespan_years",
    "diet", "habitat", "activity_pattern", "temperament",
    "handling_level", "care_level", "beginner_friendly",
    "recommended_enclosure", "temperature_c_range", "humidity_percent_range",
    "social_needs", "danger_level", "venomous_or_toxic",
    "estimated_price_range_thb",
    "possession_status_th", "possession_requirement_th",
    "legal_status_hint_th", "legal_note_th",
    "wildlife_law_category_th",
]

cleaned = []
for row in rows:
    r = {k: norm(row.get(k, "")) for k in KEEP}
    # Skip rows with no useful name data
    if not r["common_name_en"] and not r["common_name_th"] and not r["scientific_name"]:
        continue
    cleaned.append(r)

print(f"  After cleaning: {len(cleaned)} rows")

# ══════════════════════════════════════════════════════════════════════
#  3. BUILD RICH SEARCH TEXT
#     Concatenation of key fields used for TF-IDF retrieval
# ══════════════════════════════════════════════════════════════════════
def build_search_text(r: dict) -> str:
    parts = [
        r["common_name_en"],
        r["common_name_th"],
        r["scientific_name"],
        r["category"],
        r["subcategory"],
        r["diet"],
        r["habitat"],
        r["temperament"],
        r["care_level"],
        r["danger_level"],
        r["venomous_or_toxic"],
        r["beginner_friendly"],
        r["social_needs"],
        r["possession_status_th"],
        r["legal_status_hint_th"],
    ]
    return " ".join(p for p in parts if p).lower()

for r in cleaned:
    r["_search_text"] = build_search_text(r)

# ══════════════════════════════════════════════════════════════════════
#  4. DEDUPLICATION (by scientific name)
# ══════════════════════════════════════════════════════════════════════
print("▶ Checking duplicates …")
seen_sci = {}
deduped = []
for r in cleaned:
    sci = r["scientific_name"].lower().strip()
    if sci and sci in seen_sci:
        print(f"  ⚠ Duplicate scientific name: {r['id']} = {seen_sci[sci]} ({sci})")
    else:
        if sci:
            seen_sci[sci] = r["id"]
        deduped.append(r)

print(f"  Unique rows: {len(deduped)}")

# ══════════════════════════════════════════════════════════════════════
#  5. CATEGORY STATS
# ══════════════════════════════════════════════════════════════════════
cats = Counter(r["category"] for r in deduped)
print("\n  Category distribution:")
for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"    {cat:<15} {cnt:>4}")

# ══════════════════════════════════════════════════════════════════════
#  6. TRAIN / TEST SPLIT  80 / 20
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Splitting train/test …")

labels = [r["category"] for r in deduped]
min_count = min(cats.values())

if min_count < 2:
    print("  ⚠ Some categories have <2 samples → non-stratified split")
    train_rows, test_rows = train_test_split(deduped, test_size=0.2, random_state=42)
else:
    train_rows, test_rows = train_test_split(
        deduped, test_size=0.2, random_state=42, stratify=labels
    )

print(f"  Train: {len(train_rows)}  |  Test: {len(test_rows)}")

def strip_internal(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]

with open(TRAIN, "w", encoding="utf-8") as f:
    json.dump({"split": "train", "count": len(train_rows), "rows": strip_internal(train_rows)},
              f, ensure_ascii=False, indent=2)
with open(TEST, "w", encoding="utf-8") as f:
    json.dump({"split": "test",  "count": len(test_rows),  "rows": strip_internal(test_rows)},
              f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════════════
#  7. TF-IDF INDEX  (over full deduped set)
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Building TF-IDF index …")

texts = [r["_search_text"] for r in deduped]

vectorizer = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(2, 4),
    max_features=12000,
    sublinear_tf=True,
)
tfidf_matrix = vectorizer.fit_transform(texts)
print(f"  Matrix: {tfidf_matrix.shape} | vocab: {len(vectorizer.vocabulary_)}")

with open(VOCAB, "w", encoding="utf-8") as f:
    json.dump({
        "vocabulary": {k: int(v) for k, v in vectorizer.vocabulary_.items()},
        "idf":        vectorizer.idf_.tolist(),
        "ngram_range": list(vectorizer.ngram_range),
        "max_features": int(vectorizer.max_features),
    }, f, ensure_ascii=False, indent=2)

# Save clean dataset (includes _search_text for RAG engine)
with open(CLEAN, "w", encoding="utf-8") as f:
    json.dump({"count": len(deduped), "rows": deduped}, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════════════
#  8. QUICK SELF-RETRIEVAL EVAL  (test set vs full index)
# ══════════════════════════════════════════════════════════════════════
print("\n▶ Running self-retrieval evaluation …")

test_texts  = [r["_search_text"] for r in test_rows]
test_matrix = vectorizer.transform(test_texts)
sims        = cosine_similarity(test_matrix, tfidf_matrix)

id_to_idx = {r["id"]: i for i, r in enumerate(deduped)}

top1 = top3 = mrr_sum = 0
details = []
cat_hits = defaultdict(lambda: {"hit1": 0, "total": 0})

for i, test_row in enumerate(test_rows):
    gt_idx  = id_to_idx.get(test_row["id"])
    ranked  = np.argsort(-sims[i])
    rank    = int(np.where(ranked == gt_idx)[0][0]) + 1 if gt_idx is not None else None

    hit1 = rank == 1 if rank else False
    hit3 = rank <= 3 if rank else False
    rr   = 1.0 / rank if rank else 0.0

    if hit1: top1 += 1
    if hit3: top3 += 1
    mrr_sum += rr

    cat = test_row["category"]
    cat_hits[cat]["total"] += 1
    if hit1: cat_hits[cat]["hit1"] += 1

    top3_names = [deduped[ranked[k]]["common_name_en"] for k in range(min(3, len(ranked)))]
    details.append({
        "id": test_row["id"], "name": test_row["common_name_en"],
        "rank": rank, "hit@1": hit1, "hit@3": hit3, "rr": round(rr, 4),
        "top3": top3_names,
    })

n = len(test_rows)
report = {
    "metrics": {
        "n": n,
        "top1_acc": round(top1/n, 4),
        "top3_acc": round(top3/n, 4),
        "mrr":      round(mrr_sum/n, 4),
    },
    "per_category": {
        cat: {"acc": round(v["hit1"]/v["total"], 4), **v}
        for cat, v in cat_hits.items()
    },
    "details": details,
}
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════════════
#  9. SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "═"*55)
print("  DATA PREPARATION COMPLETE")
print("═"*55)
print(f"  Raw rows:        {len(rows)}")
print(f"  After cleaning:  {len(deduped)}")
print(f"  Train:           {len(train_rows)}")
print(f"  Test:            {len(test_rows)}")
print(f"  TF-IDF vocab:    {len(vectorizer.vocabulary_)}")
print(f"  Top-1 Accuracy:  {top1/n:.2%}")
print(f"  Top-3 Accuracy:  {top3/n:.2%}")
print(f"  MRR:             {mrr_sum/n:.4f}")
print()
print("  Output files:")
for fp in [CLEAN, TRAIN, TEST, VOCAB, REPORT]:
    print(f"    {fp.name:<25} {fp.stat().st_size:>10,} bytes")
print("═"*55)
