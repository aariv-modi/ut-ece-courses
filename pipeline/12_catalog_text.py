"""Authoritative description + prerequisite text + notes per course, with provenance and conflict flags -> data/catalog_text.json

Descriptions : UT catalog 2026-27 A-Z page (current catalog); registrar text for topic-split numbers that carry a topic description.
Prerequisites: 1) UT Registrar course schedule wording (latest term the course was scheduled)  2) UT catalog 2025-26.
               Disagreement between 1) and 2) is recorded as a flag. A syllabus stating something different is flagged later (16_export).
"""
import json, re, collections
from common import ROOT

ds = json.load(open(ROOT / "data/dataset.json", encoding="utf8"))["courses"]
courses = json.load(open(ROOT / "data/courses.json", encoding="utf8"))
ov = json.load(open(ROOT / "data/overrides.json", encoding="utf8"))
slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
tidy = lambda s: re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s+", " ", s)).strip()
canon = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
CUT = r"(?:Designed to accommodate|Restricted enrollment|Partially taught|Taught as a Web|Course number may be repeated|Additional hour|Hour\(s\) to be arranged|Laboratory hour|Priority is for|Same As|Restricted to|See department headnote|Only one of the following|May not be counted|Inquiry-based learning|Mandatory exams|Class meets)"
NOTE_KEEP = re.compile(r"^(Restricted|May not be counted|Only one of the following|Same As|Taught as a Web|Partially taught|Course number may be repeated|Priority is for|Inquiry-based learning|Designed to accommodate|Electrical and Computer Engineering \d+\w* and|Offered on the|Laboratory hour|Mathematics \d+\w* and \d+\w* may not both|Students who have received|A student may not earn credit|Credit for Mathematics|Mathematic \d+)", re.I)


def notes_from(text):
    sents = re.split(r"(?<=[.])\s+(?=[A-Z])", text or "")
    out = []
    for x in sents:
        x = tidy(x.replace("See department headnote", ""))
        if NOTE_KEEP.match(x) and len(x) <= 260:
            out.append(x if x.endswith(".") else x + ".")
    return out


# ---- registrar detail pages: heading -> (term id, body)
det = {}
for i in (1, 2, 3, 4):
    for line in open(ROOT / f"data/registrar/ece_details_{i}.tsv", encoding="utf8"):
        head, term, body = line.rstrip("\n").split("|", 2)
        det[head] = (term, body)
TERM_RANK = {"20259": 0, "20262": 1, "20269": 2, "20272": 3}
SPLIT = set(ov["split_courses"])


ALIAS = dict(ov.get("code_aliases", {}))
for k_, v_ in courses.items():
    for o_ in v_.get("also_numbers", []):
        ALIAS[o_] = k_


def key_of(head):
    m = re.match(r"ECE (\d{3}[A-Z]*) (.*)", head)
    code, title = ALIAS.get(m.group(1), m.group(1)), m.group(2).strip()
    if code in SPLIT:
        return f"{code}-{slug(ov['registrar_title_topics'][title])}", False
    return code, False


best = {}   # course key -> (is_honors, -term_rank, head); prefer non-honors, then latest term
for head, (term, body) in det.items():
    key, hon = key_of(head)
    rank = (hon, -TERM_RANK[term])
    if key not in best or rank < best[key][0]:
        best[key] = (rank, head)


def split_body(body):
    """-> (description, prerequisite, tail_notes_text)"""
    m = re.search(r"(?:Additional prerequisites?|Prerequisite)s?:\s*", body)
    td = re.search(r"Topic description:\s*(.*?)(?=\s+Additional prerequisites?:|\s+Inquiry-based|$)", body)
    pre = None
    if m and "vary with the topic" not in body[m.start():m.start() + 90]:
        pre = tidy(re.split(r"\s+" + CUT, body[m.end():])[0])
    desc = tidy(re.split(r"(?:Additional prerequisites?|Prerequisite)s?:", body)[0])
    return desc, pre, td.group(1) if td else None


out = {}
for key, c in ds.items():
    base = c.get("base_number") or key
    rec = {"description": None, "description_source": None, "prerequisites": None, "prerequisites_source": None,
           "flags": [], "registrar": None, "catalog_2526": None, "notes": []}
    cat = courses.get(base) or {}
    ctext = cat.get("catalog_text") or ""
    old = cat.get("catalog_2526_text") or ""
    reg_desc = reg_pre = None
    if key in best:
        head = best[key][1]; term, body = det[head]
        reg_desc, reg_pre, topic_desc = split_body(body)
        rec["registrar"] = {"text": reg_pre, "term": {"20259": "Fall 2025", "20262": "Spring 2026", "20269": "Fall 2026", "20272": "Spring 2027"}[term]}
        rec["notes"] = notes_from(re.sub(r"^.*?(?=(Prerequisite|Mathematics \d|Restricted|Only one|May not|Same As))", "", body, count=1, flags=re.S)) if False else notes_from(body)
        if c.get("base_number") and topic_desc:
            rec["description"], rec["description_source"] = tidy(topic_desc), f"UT Registrar course schedule ({rec['registrar']['term']}), topic description"
    # description
    if rec["description"] is None and not c.get("base_number"):
        d = tidy(re.split(r"\s+" + CUT + r"|\s+Prerequisite", ctext)[0]) if ctext else ""
        if d:
            rec["description"], rec["description_source"] = d, "UT catalog 2026-27"
        elif reg_desc:
            rec["description"], rec["description_source"] = reg_desc, f"UT Registrar course schedule ({rec['registrar']['term']})"
    # catalog 2025-26 prerequisite
    m = re.search(r"Prerequisite[s]?:\s*(.*)$", old)
    cat_pre = tidy(re.split(r"\s+" + CUT, m.group(1))[0]) if m else None
    rec["catalog_2526"] = cat_pre
    if key in best:
        rec["prerequisites"] = reg_pre or "None listed"
        rec["prerequisites_source"] = f"UT Registrar course schedule ({rec['registrar']['term']})"
        if c.get("base_number"):
            m2 = re.search(r"Additional prerequisites?:\s*(.*?)(?=\s+Inquiry|$)", det[best[key][1]][1])
            if m2 and reg_pre: rec["prerequisites"] = reg_pre.rstrip(".") + ". Additional prerequisite: " + tidy(m2.group(1))
        if cat_pre and not c.get("base_number") and canon(cat_pre) != canon(reg_pre):
            rec["flags"].append({"type": "registrar_vs_catalog_2526", "registrar": reg_pre, "catalog_2526": cat_pre})
        if not cat_pre and reg_pre and old and not c.get("base_number"):
            rec["flags"].append({"type": "registrar_has_prereq_catalog_none", "registrar": reg_pre})
    elif cat_pre:
        rec["prerequisites"], rec["prerequisites_source"] = cat_pre, "UT catalog 2025-26"
        if not rec["notes"]: rec["notes"] = notes_from(old)
    if not rec["notes"] and old:
        rec["notes"] = notes_from(old)
    out[key] = rec

json.dump(out, open(ROOT / "data/catalog_text.json", "w", encoding="utf8"), indent=1)
print("descriptions:", collections.Counter(r["description_source"] for r in out.values()))
print("prerequisites:", collections.Counter((r["prerequisites_source"] or "none").split(" (")[0] for r in out.values()))
print("flags:", collections.Counter(f["type"] for r in out.values() for f in r["flags"]))
print("no description:", [k for k, r in out.items() if not r["description"]])
