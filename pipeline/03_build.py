"""Merge courses + sections into the per-course dataset the site needs -> data/dataset.json"""
import json, re, datetime, collections
from common import ROOT

TERM_ORDER = ["Fall 2025", "Spring 2026", "Fall 2026"]   # past/current, oldest -> newest
NEXT = "Spring 2027"
REPO_BASE = "https://utdirect.utexas.edu"

courses = json.load(open(ROOT / "data/courses.json", encoding="utf8"))
sections = json.load(open(ROOT / "data/sections.json", encoding="utf8"))
ov = json.load(open(ROOT / "data/overrides.json", encoding="utf8"))
slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

# variable-topic numbers: every distinct topic is its own course
for base in ov["split_courses"]:
    base_rec = courses.pop(base)
    for s in sections:
        if s["base"] == base:
            courses.setdefault(s["course"], dict(base_rec, number=s["course"], title=s["topic"], base_number=base,
                                                 code=f"ECE {base}", catalog_text=base_rec["catalog_text"]))

out = {}
for num, c in courses.items():
    secs = [s for s in sections if s["course"] == num]
    by_term = {t: [s for s in secs if s["term"] == t] for t in TERM_ORDER + [NEXT]}
    taught_past = [t for t in TERM_ORDER if by_term[t]]
    rec = dict(c)
    rec["terms_offered"] = taught_past
    rec["last_offered"] = taught_past[-1] if taught_past else None
    rec["offered_next"] = bool(by_term[NEXT])
    rec["status"] = "active" if (taught_past or by_term[NEXT]) else "potentially_retired"
    rec["section_counts"] = {t: len(v) for t, v in by_term.items() if v}
    inst, cands = {}, collections.defaultdict(list)
    for ti, t in enumerate(TERM_ORDER + [NEXT]):
        for s in by_term[t]:
            for name in s["instructors"]:
                e = inst.setdefault(name, {"name": name, "terms": [], "syllabus_path": None, "syllabus_term": None, "pdf_path": None, "pdf_term": None, "syllabus_title": None, "name_verified": True})
                if t not in e["terms"]:
                    e["terms"].append(t)
                m_ = re.search(r"/download/(\d+)/", s["syllabus_path"] or "")
                if s["syllabus_path"] and not (m_ and m_.group(1) in ov.get("exclude_syllabus_ids", {})):
                    cands[name].append((ti, s["syllabus_path"], s["title"]))
    pdf_id = lambda p: int(re.search(r"/download/(\d+)/", p).group(1)) if "/download/" in p else -1
    for name, cs_ in cands.items():   # most recent syllabus: latest term; within a term the highest PDF id (any is acceptable)
        e = inst[name]
        ti, p, ttl = max(cs_, key=lambda x: (x[0], pdf_id(x[1]), x[1]))
        e["syllabus_path"], e["syllabus_term"], e["syllabus_title"] = p, (TERM_ORDER + [NEXT])[ti], ttl
        pdfs = [x for x in cs_ if "/download/" in x[1]]
        if pdfs:
            ti2, p2, _ = max(pdfs, key=lambda x: (x[0], pdf_id(x[1])))
            e["pdf_path"], e["pdf_term"] = p2, (TERM_ORDER + [NEXT])[ti2]
    for e in inst.values():
        pp = e.pop("pdf_path"); e["pdf_url"] = REPO_BASE + pp if pp else None
        p = e.pop("syllabus_path"); e["syllabus_url"] = (p if p and p.startswith("http") else REPO_BASE + p) if p else None
    rec["instructors"] = sorted(inst.values(), key=lambda e: (e["terms"][-1] != NEXT, e["name"]))
    rec["next_instructors_unlisted"] = bool(by_term[NEXT]) and not any(s["instructors"] for s in by_term[NEXT])
    out[num] = rec

json.dump({"generated": datetime.date.today().isoformat(), "window": TERM_ORDER + [NEXT], "courses": out},
          open(ROOT / "data/dataset.json", "w", encoding="utf8"), indent=1)
a = [c for c in out.values() if c["status"] == "active"]
print(len(out), "courses;", len(a), "active;", len(out) - len(a), "potentially retired;", "offered next:", sum(c["offered_next"] for c in out.values()))
print("instructor entries:", sum(len(c["instructors"]) for c in out.values()), "| with syllabus:", sum(1 for c in out.values() for e in c["instructors"] if e["syllabus_url"]))
print("retired:", sorted(k for k, c in out.items() if c["status"] != "active"))
