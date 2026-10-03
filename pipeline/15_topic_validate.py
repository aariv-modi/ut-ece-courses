"""Validate data/topic_out/<course>.json files: schema + every evidence quote must occur in that instructor's text.

usage: python 15_topic_validate.py [course ...]   (no args = every file in data/topic_out)
Exit code 1 if any hard error. Warnings are printed but allowed.
"""
import json, re, sys, pathlib
from common import ROOT

STATUS = {"stated", "possible", "textbook"}
LOGISTICS = re.compile(r"\b(exam|midterm|final exam|quiz|grading|grade|syllabus review|office hours|deadline|late policy|attendance|review session|project presentation|introduction to the course|course overview|logistics)\b", re.I)


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace(" ", " ")
    s = re.sub(r"-\s*\n\s*", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_ok(q, src_norm, src_set):
    qn = norm(q)
    if not qn:
        return False
    if qn in src_norm:
        return True
    segs = [norm(x) for x in re.split(r"\.\.\.|…", q) if len(norm(x)) >= 4]
    if len(segs) > 1 and all(s in src_norm for s in segs):
        return True
    w = qn.split()
    return len(w) >= 4 and sum(x in src_set for x in w) / len(w) >= 0.92      # table text split across lines


def validate(course):
    errs, warns = [], []
    ip, op = ROOT / f"data/topic_in/{course}.json", ROOT / f"data/topic_out/{course}.json"
    if not op.exists():
        return [f"{course}: output file missing"], []
    try:
        out = json.load(open(op, encoding="utf8"))
    except Exception as e:
        return [f"{course}: invalid JSON ({e})"], []
    inp = json.load(open(ip, encoding="utf8"))
    texts = {}
    for i in inp["instructors"]:
        t = (ROOT / i["text_file"]).read_text(encoding="utf8", errors="ignore")
        texts[i["name"]] = (norm(t), set(norm(t).split()), len(t))
    names = set(texts)
    if out.get("course") != course:
        errs.append(f"{course}: 'course' field is {out.get('course')!r}")
    if set(out.get("instructors", {})) != names:
        errs.append(f"{course}: 'instructors' keys {sorted(out.get('instructors', {}))} != expected {sorted(names)}")
    seen = set()
    per = {n: 0 for n in names}
    for t in out.get("topics", []):
        lab = t.get("label", "")
        if not lab or len(lab) > 90:
            errs.append(f"{course}: bad label {lab!r}")
        k = norm(lab)
        if k in seen:
            errs.append(f"{course}: duplicate topic label {lab!r}")
        seen.add(k)
        if LOGISTICS.search(lab):
            warns.append(f"{course}: label looks like logistics: {lab!r}")
        cov = t.get("coverage") or {}
        if not cov:
            errs.append(f"{course}: topic {lab!r} has no coverage")
        for n, c in cov.items():
            if n not in names:
                errs.append(f"{course}: {lab!r} credits unknown instructor {n!r}"); continue
            if c.get("status") not in STATUS:
                errs.append(f"{course}: {lab!r}/{n}: bad status {c.get('status')!r}")
            ev = c.get("evidence", "")
            if not ev or len(ev.split()) > 70:
                errs.append(f"{course}: {lab!r}/{n}: evidence missing or too long")
            elif not quote_ok(ev, texts[n][0], texts[n][1]) and c.get("status") != "textbook":
                errs.append(f"{course}: {lab!r}/{n}: evidence quote not found in that instructor's text: {ev[:80]!r}")
            elif c.get("status") == "textbook" and not c.get("toc_url"):
                errs.append(f"{course}: {lab!r}/{n}: textbook status needs toc_url")
            per[n] += 1
    for n, cnt in per.items():
        lvl = (out.get("instructors", {}).get(n, {}) or {}).get("detail_level")
        if cnt == 0 and lvl != "minimal":
            warns.append(f"{course}/{n}: no topics credited but detail_level is {lvl!r}")
    if len(out.get("topics", [])) < 3 and not all((v or {}).get("detail_level") == "minimal" for v in out.get("instructors", {}).values()):
        warns.append(f"{course}: only {len(out.get('topics', []))} topics")
    return errs, warns


if __name__ == "__main__":
    courses = sys.argv[1:] or sorted(p.stem for p in (ROOT / "data/topic_out").glob("*.json"))
    bad = 0
    for c in courses:
        e, w = validate(c)
        for x in e: print("ERROR", x)
        for x in w: print("warn ", x)
        bad += bool(e)
        if not e and not w:
            print("ok   ", c)
    sys.exit(1 if bad else 0)
