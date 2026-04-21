#!/usr/bin/env python3
import json, re, unicodedata
from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

BASE  = Path(__file__).parent.parent / "data"
PROC  = BASE / "processed"
PROC.mkdir(exist_ok=True)
MAIN_XL  = BASE / "exotic_pets_improved_final.xlsx"
LEGAL_XL = BASE / "exotic_pets_legal_final_fixed.xlsx"
CLEAN = PROC / "clean.json"
TRAIN = PROC / "train.json"
TEST  = PROC / "test.json"
VOCAB = PROC / "tfidf_vocab.json"
REPORT= PROC / "eval_report.json"

# 1. LOAD & MERGE
print("=== Step 1: Loading & Merging ===")
df_main  = pd.read_excel(MAIN_XL)
df_legal = pd.read_excel(LEGAL_XL)
print(f"  Main:  {df_main.shape}")
print(f"  Legal: {df_legal.shape}")

LEGAL_EXTRA = ["id","final_legal_answer_th_v6","final_permit_answer_th_v6",
               "safe_for_auto_decision_th_v6","action_needed_th_v6",
               "final_confidence_th_v6","legal_species_bucket_v6",
               "app_display_summary_th_v5","plain_legal_summary_th",
               "legal_reliability_score","illegal_clear_flag_th"]
LEGAL_EXTRA = [c for c in LEGAL_EXTRA if c in df_legal.columns]

df = df_main.merge(df_legal[LEGAL_EXTRA], on="id", how="left")
print(f"  Merged: {df.shape}")

# 2. CLEAN
print("\n=== Step 2: Cleaning ===")
def norm(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return ""
    t = unicodedata.normalize("NFC", str(val))
    t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)
    return re.sub(r"\s+", " ", t).strip()

KEEP = ["id","category","subcategory","common_name_en","common_name_th","scientific_name",
        "origin_region","typical_size_cm","lifespan_years","diet","diet_details_th",
        "feeding_schedule_th","habitat","activity_pattern","temperament",
        "distinguishing_features_th","handling_level","care_level","beginner_friendly",
        "recommended_enclosure","temperature_c_range","humidity_percent_range","social_needs",
        "danger_level","venomous_or_toxic","estimated_price_range_thb",
        "possession_status_th","possession_requirement_th","legal_status_hint_th",
        "legal_note_th","wildlife_law_category_th","breeding_status_th","trade_status_th",
        "import_export_status_th","final_legal_answer_th_v6","final_permit_answer_th_v6",
        "safe_for_auto_decision_th_v6","action_needed_th_v6","final_confidence_th_v6",
        "legal_species_bucket_v6","app_display_summary_th_v5","plain_legal_summary_th",
        "legal_reliability_score","illegal_clear_flag_th"]
KEEP = [c for c in KEEP if c in df.columns]

rows = []
for _, row in df.iterrows():
    r = {k: norm(row.get(k,"")) for k in KEEP}
    if not r.get("common_name_en") and not r.get("common_name_th"): continue
    rows.append(r)
print(f"  Rows after cleaning: {len(rows)}")

# 3. CHUNK TEXT (1 row = 1 chunk)
print("\n=== Step 3: Building Chunks ===")
def fv(v): return v if v else "-"

def build_chunk_text(r):
    L = [
        f"# {fv(r.get('common_name_th'))} / {fv(r.get('common_name_en'))}",
        f"ชื่อวิทยาศาสตร์: {fv(r.get('scientific_name'))}",
        f"หมวดหมู่: {fv(r.get('category'))} › {fv(r.get('subcategory'))}",
        f"ถิ่นกำเนิด: {fv(r.get('origin_region'))}",
    ]
    if r.get("distinguishing_features_th"):
        L += ["","## ลักษณะเด่น", r["distinguishing_features_th"]]
    L += ["","## ข้อมูลพื้นฐาน",
          f"ขนาด: {fv(r.get('typical_size_cm'))} ซม. | อายุขัย: {fv(r.get('lifespan_years'))} ปี",
          f"นิสัย: {fv(r.get('temperament'))} | ช่วงเวลาหากิน: {fv(r.get('activity_pattern'))}",
          f"ความต้องการสังคม: {fv(r.get('social_needs'))}",
          "","## อาหาร",
          f"ประเภท: {fv(r.get('diet'))}"]
    if r.get("diet_details_th"):    L.append(f"รายละเอียด: {r['diet_details_th']}")
    if r.get("feeding_schedule_th"):L.append(f"ตารางอาหาร: {r['feeding_schedule_th']}")
    L += ["","## การดูแล",
          f"ระดับความยาก: {fv(r.get('care_level'))} | การจับ: {fv(r.get('handling_level'))}",
          f"เหมาะมือใหม่: {fv(r.get('beginner_friendly'))}",
          f"ที่พักพิง: {fv(r.get('recommended_enclosure'))}",
          f"อุณหภูมิ (°C): {fv(r.get('temperature_c_range'))}",
          f"ความชื้น (%): {fv(r.get('humidity_percent_range'))}",
          f"ถิ่นที่อยู่: {fv(r.get('habitat'))}",
          "","## ความปลอดภัย",
          f"ระดับอันตราย: {fv(r.get('danger_level'))} | มีพิษ: {fv(r.get('venomous_or_toxic'))}",
          "","## ราคา",
          f"ราคาประมาณ (บาท): {fv(r.get('estimated_price_range_thb'))}",
          "","## กฎหมาย",
          f"สถานะครอบครอง: {fv(r.get('possession_status_th'))}",
          f"ข้อกำหนด: {fv(r.get('possession_requirement_th'))}",
          f"หมวดกฎหมาย: {fv(r.get('wildlife_law_category_th'))}"]
    if r.get("final_legal_answer_th_v6"):
        L += ["","## คำตอบทางกฎหมาย (v6)",
              f"สรุปกฎหมาย: {r['final_legal_answer_th_v6']}"]
    if r.get("final_permit_answer_th_v6"):
        L.append(f"ใบอนุญาต: {r['final_permit_answer_th_v6']}")
    if r.get("action_needed_th_v6"):
        L.append(f"สิ่งที่ต้องทำ: {r['action_needed_th_v6']}")
    if r.get("final_confidence_th_v6"):
        L.append(f"ความเชื่อมั่น: {r['final_confidence_th_v6']}")
    if r.get("plain_legal_summary_th"):
        L += ["", f"สรุปสั้น: {r['plain_legal_summary_th']}"]
    return "\n".join(L)

def build_search_text(r):
    parts = [r.get("common_name_en",""),r.get("common_name_th",""),
             r.get("scientific_name",""),r.get("category",""),r.get("subcategory",""),
             r.get("diet",""),r.get("habitat",""),r.get("temperament",""),
             r.get("care_level",""),r.get("danger_level",""),r.get("venomous_or_toxic",""),
             r.get("beginner_friendly",""),r.get("social_needs",""),
             r.get("legal_species_bucket_v6","")]
    return " ".join(p for p in parts if p).lower()

for r in rows:
    r["chunk_text"]   = build_chunk_text(r)
    r["_search_text"] = build_search_text(r)

print(f"  Chunks: {len(rows)}  (1 row = 1 chunk)")
print(f"  Sample chunk preview:\n{rows[0]['chunk_text'][:300]}\n  ...")

# 4. DEDUPLICATION
print("\n=== Step 4: Deduplication ===")
seen, deduped = {}, []
for r in rows:
    sci = r.get("scientific_name","").lower().strip()
    if sci and sci in seen:
        print(f"  DUPLICATE: {r['id']} = {seen[sci]} ({sci})")
    else:
        if sci: seen[sci] = r["id"]
        deduped.append(r)
print(f"  Unique: {len(deduped)}")

# 5. CATEGORY STATS
cats = Counter(r["category"] for r in deduped)
print("\n  Category distribution:")
for cat, cnt in sorted(cats.items(), key=lambda x:-x[1]):
    print(f"    {cat:<15} {cnt:>4}")

# 6. TRAIN/TEST SPLIT
print("\n=== Step 5: Train/Test Split ===")
labels = [r["category"] for r in deduped]
if min(cats.values()) < 2:
    train_rows, test_rows = train_test_split(deduped, test_size=0.2, random_state=42)
else:
    train_rows, test_rows = train_test_split(deduped, test_size=0.2, random_state=42, stratify=labels)
print(f"  Train: {len(train_rows)}  |  Test: {len(test_rows)}")

def strip_internal(data):
    return [{k:v for k,v in r.items() if k!="_search_text"} for r in data]

with open(TRAIN,"w",encoding="utf-8") as fh:
    json.dump({"split":"train","count":len(train_rows),"rows":strip_internal(train_rows)},fh,ensure_ascii=False,indent=2)
with open(TEST,"w",encoding="utf-8") as fh:
    json.dump({"split":"test","count":len(test_rows),"rows":strip_internal(test_rows)},fh,ensure_ascii=False,indent=2)

# 7. TF-IDF
print("\n=== Step 6: TF-IDF Index ===")
texts = [r["_search_text"] for r in deduped]
vec   = TfidfVectorizer(analyzer="char_wb", ngram_range=(2,4), max_features=12000, sublinear_tf=True)
M     = vec.fit_transform(texts)
print(f"  Matrix: {M.shape} | vocab: {len(vec.vocabulary_)}")

with open(VOCAB,"w",encoding="utf-8") as fh:
    json.dump({"vocabulary":{k:int(v) for k,v in vec.vocabulary_.items()},
               "idf":vec.idf_.tolist(),"ngram_range":list(vec.ngram_range),
               "max_features":int(vec.max_features)},fh,ensure_ascii=False,indent=2)

with open(CLEAN,"w",encoding="utf-8") as fh:
    json.dump({"count":len(deduped),"rows":deduped},fh,ensure_ascii=False,indent=2)

# 8. EVAL
print("\n=== Step 7: Self-Retrieval Eval ===")
tm = vec.transform([r["_search_text"] for r in test_rows])
S  = cosine_similarity(tm, M)
id2i = {r["id"]:i for i,r in enumerate(deduped)}
top1=top3=mrr_sum=0
details=[]
cat_hits=defaultdict(lambda:{"hit1":0,"total":0})
for i,tr in enumerate(test_rows):
    gi  = id2i.get(tr["id"])
    rk  = np.argsort(-S[i])
    rn  = int(np.where(rk==gi)[0][0])+1 if gi is not None else None
    h1  = (rn==1) if rn else False
    h3  = (rn<=3) if rn else False
    rr  = (1.0/rn) if rn else 0.0
    if h1: top1+=1
    if h3: top3+=1
    mrr_sum+=rr
    cat_hits[tr["category"]]["total"]+=1
    if h1: cat_hits[tr["category"]]["hit1"]+=1
    details.append({"id":tr["id"],"name":tr.get("common_name_en"),"rank":rn,"hit@1":h1,"hit@3":h3,"rr":round(rr,4)})

n=len(test_rows)
report={"metrics":{"n":n,"top1_acc":round(top1/n,4),"top3_acc":round(top3/n,4),"mrr":round(mrr_sum/n,4)},
        "per_category":{cat:{"acc":round(v["hit1"]/v["total"],4)if v["total"] else 0,**v} for cat,v in cat_hits.items()},
        "details":details}
with open(REPORT,"w",encoding="utf-8") as fh:
    json.dump(report,fh,ensure_ascii=False,indent=2)

# SUMMARY
print("\n"+"="*60)
print("  DATA PREPARATION COMPLETE")
print("="*60)
print(f"  Source (main)    : {df_main.shape[0]} rows × {df_main.shape[1]} cols")
print(f"  Source (legal)   : {df_legal.shape[0]} rows × {df_legal.shape[1]} cols")
print(f"  Merged & cleaned : {len(deduped)} rows  (1 row = 1 chunk)")
print(f"  Train / Test     : {len(train_rows)} / {len(test_rows)}")
print(f"  TF-IDF vocab     : {len(vec.vocabulary_)} features")
print(f"  Top-1 Accuracy   : {top1/n:.2%}")
print(f"  Top-3 Accuracy   : {top3/n:.2%}")
print(f"  MRR              : {mrr_sum/n:.4f}")
print("\n  Per-category accuracy:")
for cat, v in report["per_category"].items():
    bar = "█"*v["hit1"] + "░"*(v["total"]-v["hit1"])
    print(f"    {cat:<15} {bar}  {v['acc']:.0%} ({v['hit1']}/{v['total']})")
print()
for fp in [CLEAN,TRAIN,TEST,VOCAB,REPORT]:
    print(f"  {fp.name:<25} {fp.stat().st_size:>10,} bytes")
print("="*60)
print("\n✅ ขั้นตอนถัดไป: python scripts/build_vector_db.py\n")
