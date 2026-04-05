"""
filter_query.py  —  Structured Filter Layer
══════════════════════════════════════════════════
แปลง categorical queries → structured filters บน dataset
รองรับ multi-condition: "นกเลี้ยงง่าย", "สัตว์เลื้อยคลานไม่มีพิษ" ฯลฯ
"""

import re
from collections import defaultdict

CARE_RANK   = {"easy": 1, "medium": 2, "hard": 3, "expert": 4}
DANGER_RANK = {"low": 1, "medium": 2, "high": 3}

# ── หมวดหมู่สัตว์ (category mapping) ───────────────────────────────────
CATEGORY_PATTERNS = {
    "Bird":      [r"นก", r"bird", r"แก้ว", r"ฟินช์", r"คาเมเลียน.*นก"],
    "Reptile":   [r"สัตว์เลื้อยคลาน", r"reptile", r"งู", r"กิ้งก่า", r"เต่า", r"จระเข้", r"ตะกวด", r"gecko", r"python", r"boa", r"skink"],
    "Mammal":    [r"สัตว์เลี้ยงลูกด้วยนม", r"mammal", r"หนู", r"แฮมสเตอร์", r"ชูการ์", r"เฮดจ์ฮ็อก", r"เฟอเรท", r"ชินชิล่า", r"กระรอก"],
    "Amphibian": [r"สัตว์ครึ่งบกครึ่งน้ำ", r"amphibian", r"กบ", r"axolotl", r"แอกโซ", r"ซาลาแมนเดอร์"],
    "Aquatic":   [r"สัตว์น้ำ", r"aquatic", r"ปลา", r"กุ้ง", r"ปู", r"arowana", r"อโรวาน่า"],
}

# ── คุณสมบัติ (attribute patterns) ─────────────────────────────────────
ATTR_PATTERNS = [
    {
        "tags": ["easy_care", "beginner"],
        "patterns": [r"เลี้ยงง่าย", r"ง่าย", r"ดูแลง่าย", r"ไม่ยุ่งยาก", r"มือใหม่",
                     r"เริ่มต้น", r"ไม่มีประสบการณ์", r"ครั้งแรก", r"beginner", r"แนะนํา.*เลี้ยง",
                     r"ควรเลี้ยง", r"น่าเลี้ยง"],
        "filters": {"care_level": "easy"},
        "label_suffix": "ที่เลี้ยงง่าย",
    },
    {
        "tags": ["no_permit"],
        "patterns": [r"ไม่ต้อง.*ใบอนุญาต", r"ไม่ต้องขออนุญาต", r"เลี้ยงได้เลย",
                     r"ไม่ต้องแจ้ง", r"ไม่ต้องมีใบ", r"เลี้ยงได้โดยไม่ต้อง"],
        "filters": {"beginner_friendly": "yes"},
        "label_suffix": "ที่เลี้ยงได้ (beginner-friendly)",
    },
    {
        "tags": ["non_venomous"],
        "patterns": [r"ไม่มีพิษ", r"ปลอดภัย", r"non.?venomous", r"ไม่พิษ"],
        "filters": {"venomous_or_toxic": "no", "danger_level": "low"},
        "label_suffix": "ที่ไม่มีพิษ",
    },
    {
        "tags": ["venomous"],
        "patterns": [r"มีพิษ", r"venomous", r"เป็นพิษ"],
        "filters": {"venomous_or_toxic__not": "no"},
        "label_suffix": "ที่มีพิษ",
    },
    {
        "tags": ["cheap"],
        "patterns": [r"ราคาถูก", r"ราคาไม่แพง", r"งบน้อย", r"ประหยัด", r"affordable"],
        "filters": {"price_range": "low"},
        "sort_by": "price_asc",
        "label_suffix": "ราคาประหยัด",
    },
    {
        "tags": ["expert_only"],
        "patterns": [r"เลี้ยงยาก", r"ดูแลยาก", r"ผู้เชี่ยวชาญ", r"expert", r"advanced"],
        "filters": {"care_level__in": ["hard", "expert"]},
        "label_suffix": "สำหรับผู้มีประสบการณ์",
    },
    {
        "tags": ["dangerous"],
        "patterns": [r"อันตราย", r"dangerous"],
        "filters": {"danger_level__in": ["high", "medium"]},
        "label_suffix": "ที่มีความเป็นอันตราย",
    },
]


def detect_intent(query: str):
    """
    Returns dict:
      category_filter: str or None
      attr_filters:    dict
      sort_by:         str
      label:           str
    หรือ None ถ้าไม่ match เลย
    """
    q = query.lower().strip()

    # ── ตรวจหา category ────────────────────────────────────────────────
    matched_category = None
    for cat, patterns in CATEGORY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, q):
                matched_category = cat
                break
        if matched_category:
            break

    # ── ตรวจหา attribute ───────────────────────────────────────────────
    matched_attr = None
    for attr in ATTR_PATTERNS:
        for pat in attr["patterns"]:
            if re.search(pat, q):
                matched_attr = attr
                break
        if matched_attr:
            break

    # ── ถ้าไม่ match อะไรเลย → ใช้ RAG ──────────────────────────────────
    if not matched_category and not matched_attr:
        return None

    # ── รวม filters ────────────────────────────────────────────────────
    combined_filters = {}
    if matched_category:
        combined_filters["category"] = matched_category
    if matched_attr:
        combined_filters.update(matched_attr["filters"])

    # ── label ──────────────────────────────────────────────────────────
    cat_label  = matched_category or "สัตว์ exotic"
    attr_label = matched_attr["label_suffix"] if matched_attr else ""
    label = f"{cat_label} {attr_label}".strip()

    sort_by = (matched_attr or {}).get("sort_by", "care_level_rank")

    return {
        "filters":  combined_filters,
        "sort_by":  sort_by,
        "label":    label,
    }


# ══════════════════════════════════════════════════════════════════════
#  APPLY FILTER
# ══════════════════════════════════════════════════════════════════════
def _price_low(price_str: str) -> int:
    m = re.search(r"(\d+)", (price_str or "").replace(",", ""))
    return int(m.group(1)) if m else 999999


def apply_filter(rows: list, filters: dict) -> list:
    result = rows
    for key, val in filters.items():
        if key == "category":
            result = [r for r in result if r.get("category", "").strip() == val]
        elif key == "beginner_friendly":
            result = [r for r in result if r.get("beginner_friendly", "").strip() == val]
        elif key == "care_level":
            result = [r for r in result if r.get("care_level", "").strip() == val]
        elif key == "care_level__in":
            result = [r for r in result if r.get("care_level", "").strip() in val]
        elif key == "danger_level":
            result = [r for r in result if r.get("danger_level", "").strip() == val]
        elif key == "danger_level__in":
            result = [r for r in result if r.get("danger_level", "").strip() in val]
        elif key == "venomous_or_toxic":
            result = [r for r in result if r.get("venomous_or_toxic", "").strip() == val]
        elif key == "venomous_or_toxic__not":
            result = [r for r in result if r.get("venomous_or_toxic", "").strip() != val]
        elif key == "price_range" and val == "low":
            result = sorted(result, key=lambda r: _price_low(r.get("estimated_price_range_thb", "")))
    return result


def sort_rows(rows: list, sort_by: str) -> list:
    if sort_by == "care_level_rank":
        return sorted(rows, key=lambda r: CARE_RANK.get(r.get("care_level", "").strip(), 9))
    elif sort_by == "danger_level_rank":
        return sorted(rows, key=lambda r: DANGER_RANK.get(r.get("danger_level", "").strip(), 9))
    elif sort_by == "price_asc":
        return sorted(rows, key=lambda r: _price_low(r.get("estimated_price_range_thb", "")))
    return rows


def build_filter_context(rows: list, intent: dict, max_rows: int = 25) -> str:
    label   = intent.get("label", "สัตว์ที่ตรงกับเงื่อนไข")
    display = rows[:max_rows]
    lines   = [f"พบ {len(rows)} ชนิดในหมวด: {label}\n"]

    groups = defaultdict(list)
    for r in display:
        groups[r.get("category", "Other")].append(r)

    for cat, items in sorted(groups.items()):
        lines.append(f"\n[{cat}] {len(items)} ชนิด")
        for r in items:
            price  = r.get("estimated_price_range_thb", "-") or "-"
            care   = r.get("care_level", "-")
            danger = r.get("danger_level", "-")
            venom  = r.get("venomous_or_toxic", "-")
            diet   = r.get("diet", "-")
            bfr    = "✅" if r.get("beginner_friendly", "").strip() == "yes" else "⚠️"
            lines.append(
                f"  {bfr} {r.get('common_name_th','-')} / {r.get('common_name_en','-')}\n"
                f"     วิทย์: {r.get('scientific_name','-')}\n"
                f"     ดูแล: {care} | อันตราย: {danger} | พิษ: {venom} | อาหาร: {diet}\n"
                f"     ราคา: {price} บาท | กรง: {r.get('recommended_enclosure','-')}"
            )

    if len(rows) > max_rows:
        lines.append(f"\n...และอีก {len(rows)-max_rows} ชนิด")

    return "\n".join(lines)
