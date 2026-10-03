"""Build per-course inputs for the topic analysis agents (math): data/topic_in/<course>.json + balanced batches."""
import json, os, re
from common import ROOT

ds = json.load(open(ROOT / "data/dataset.json", encoding="utf8"))["courses"]
ct = json.load(open(ROOT / "data/catalog_text.json", encoding="utf8"))
web = {f[:-4] for f in os.listdir(ROOT / "data/syllabi_web") if f.endswith(".txt")}
out_dir = ROOT / "data/topic_in"; out_dir.mkdir(exist_ok=True)
for old in out_dir.glob("*.json"):
    old.unlink()

items = []
for k, c in ds.items():
    ins = []
    for e in c["instructors"]:
        if e.get("syllabus_is_web_only"):
            code = re.search(r"/doc/([a-z0-9]+)", e["syllabus_url"]).group(1)
            if code not in web:
                continue
            tf, kind, term, url = f"data/syllabi_web/{code}.txt", "web", e["syllabus_term"], e["syllabus_url"]
        elif e.get("syllabus_id"):
            tf, kind, term, url = f"data/syllabi/{e['syllabus_id']}.txt", "pdf", e["pdf_term"], e["pdf_url"]
        else:
            continue
        if not (ROOT / tf).exists():
            continue
        n = len((ROOT / tf).read_text(encoding="utf8", errors="ignore"))
        entry = {"name": e["name"], "terms_taught": e["terms"], "syllabus_term": term, "kind": kind, "text_file": tf,
                 "pdf_file": (tf[:-4] + ".pdf") if kind == "pdf" else None, "url": url, "chars": n}
        ins.append(entry)
    if not ins:
        continue
    rec = ct.get(k, {})
    json.dump({"course": k, "code": c["code"], "title": c["title"], "is_variable_topic_offering": bool(c.get("base_number")),
               "official_description": rec.get("description"), "official_prerequisites": rec.get("prerequisites"), "instructors": ins},
              open(out_dir / f"{k}.json", "w", encoding="utf8"), indent=1)
    items.append((k, sum(i["chars"] for i in ins), len(ins)))

# batches: multi-instructor courses stay whole; fill each batch to ~130k chars of syllabus text
batches, cur, cur_n = [], [], 0
for k, n, m in sorted(items, key=lambda x: (-x[2], -x[1])):
    if m >= 6 or (m >= 2 and n > 60000):
        batches.append([k]); continue
    if cur and cur_n + n > 130000:
        batches.append(cur); cur, cur_n = [], 0
    cur.append(k); cur_n += n
if cur:
    batches.append(cur)
for i, b in enumerate(batches):
    json.dump(b, open(out_dir / f"_batch_{i+1:02d}.json", "w"), indent=1)
print(len(items), "courses ->", len(batches), "batches; chars per batch:", [sum(dict((k, n) for k, n, _ in items)[x] for x in b) for b in batches])
