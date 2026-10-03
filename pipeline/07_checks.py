"""Invariant checks on the exported dataset. Exit code 1 if any rule is violated."""
import json, re, sys
from common import ROOT

ds = json.load(open(ROOT / "site/src/data/dataset.json", encoding="utf8"))
idx = json.load(open(ROOT / "site/public/search-index.json", encoding="utf8"))
WINDOW = {"Fall 2025", "Spring 2026", "Fall 2026", "Spring 2027"}
errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


check(set(ds["window"]) == WINDOW, f"window is {ds['window']}")
for num, c in ds["courses"].items():
    base = c.get("base_number") or num
    check(re.fullmatch(r"\d{3}[A-Z]?", base) and int(base[1:3]) < 80, f"{num}: not an undergraduate number")
    check(not any("summer" in t.lower() for t in c["terms_offered"]), f"{num}: summer term present")
    check(set(c["terms_offered"]) <= WINDOW, f"{num}: term outside window {c['terms_offered']}")
    check(c["status"] == ("active" if (c["terms_offered"] or c["offered_next"]) else "potentially_retired"), f"{num}: status inconsistent")
    check(c["last_offered"] is None or c["last_offered"] == c["terms_offered"][-1], f"{num}: last_offered mismatch")
    if c["status"] != "active":
        check("last_offered_earlier" in c, f"{num}: retired course missing last_offered_earlier")
        check("summer" not in str(c.get("last_offered_earlier")).lower(), f"{num}: summer in last_offered_earlier")
    for e in c["instructors"]:
        check(set(e["terms"]) <= WINDOW, f"{num}/{e['name']}: instructor term outside window")
        check(e["name"].strip() != "", f"{num}: empty instructor name")
        for t in e.get("topics", []):
            check(bool(t.get("topic")) and bool(t.get("evidence")), f"{num}/{e['name']}: topic without evidence: {t.get('topic')}")
            check(t["kind"] in ("explicit", "possible", "textbook_chapter"), f"{num}: unknown topic kind {t['kind']}")
        names = [t["topic"].lower() for t in e.get("topics", [])]
        check(len(names) == len(set(names)), f"{num}/{e['name']}: duplicate topics")
        if e.get("pdf_term"):
            check(e["pdf_term"] in WINDOW and "summer" not in e["pdf_term"].lower(), f"{num}: syllabus term {e['pdf_term']}")
    m = c.get("matrix")
    if m:
        cols = [e for e in c["instructors"] if e.get("topics")]
        check([x["name"] for x in m["columns"]] == [e["name"] for e in cols], f"{num}: matrix columns mismatch")
        seen = 0
        for row in m["rows"]:
            check(row["cells"], f"{num}: empty matrix row {row['label']}")
            for ci, cell in row["cells"].items():
                texts = {t["topic"] for t in cols[int(ci)]["topics"]}
                check(row["label"] in texts, f"{num}: matrix cell not credited to that professor: {row['label']}")
                check(bool(cell["evidence"]), f"{num}: matrix cell without evidence: {cell['topic']}")
                seen += 1
        n_topics = sum(len(e["topics"]) for e in cols)
        check(seen == n_topics, f"{num}: matrix accounts for {seen} of {n_topics} topics")
for r in idx:
    check("summer" not in r["term"].lower(), f"index: summer entry {r['course']}")
    check(r["evidence"], f"index: empty evidence {r['course']} {r['topic']}")

n_c = len(ds["courses"]); n_act = sum(c["status"] == "active" for c in ds["courses"].values())
print(f"{n_c} courses ({n_act} active), {len(idx)} indexed topics")
if errors:
    print(len(errors), "VIOLATIONS"); [print(" -", e) for e in errors[:30]]; sys.exit(1)
print("all invariants hold")
