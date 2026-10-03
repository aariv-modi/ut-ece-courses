"""Undergraduate ECE course list from the UT catalog A-Z pages.

2026-27 page (current catalog): authority for which courses exist + titles + descriptions (hours digit hidden as 'X').
2025-26 page: hours digit + prerequisite text. Registrar/syllabus codes fill in hours digits for new numbers.
Undergraduate = last two digits < 80 (UT numbering). Honors (suffix H) are separate numbers in ECE.
"""
import re, json, html, collections
from bs4 import BeautifulSoup
from common import ROOT

RAW = ROOT / "data/raw"
norm = lambda s: re.sub(r"\s+", " ", html.unescape(s)).replace("\xa0", " ").strip()
CODE = r"[\dX]\d{2}[A-Z]*"
HEAD = re.compile(rf"ECE ((?:{CODE}(?: \(TCCN:[^)]*\))?(?:, |, and | and )?)+)\.\s*(.*?)\.?$")


def parse(path):
    out = []
    for h5 in BeautifulSoup(open(path, encoding="utf8").read(), "html.parser").select("h5"):
        m = HEAD.match(norm(h5.get_text()))
        if not m:
            continue
        body, n = [], h5.find_next_sibling()
        while n is not None and n.name not in ("h5", "h3", "h4"):
            body.append(norm(n.get_text(" "))); n = n.find_next_sibling()
        for code in re.findall(CODE, re.sub(r"\(TCCN:[^)]*\)", "", m.group(1))):
            out.append({"code": code, "title": m.group(2), "text": norm(" ".join(body))})
    return out


if __name__ == "__main__":
    new, old = parse(RAW / "atoz_ece_2627.html"), parse(RAW / "atoz_ece_2526.html")
    und = lambda c: int(c[1:3]) < 80
    digits = collections.defaultdict(set)          # level+suffix -> hours digits seen anywhere
    seen = collections.defaultdict(set)            # ... seen in the registrar / repository (actually scheduled)
    old_d = collections.defaultdict(set)
    for r in old:
        if und(r["code"]): old_d[r["code"][1:]].add(r["code"][0])
    for f in (ROOT / "data/registrar").glob("ece_*_agg.tsv"):
        for l in open(f, encoding="utf8"):
            m = re.match(r"ECE (\d{3}[A-Z]*) ", l)
            if m and und(m.group(1)): seen[m.group(1)[1:]].add(m.group(1)[0])
    pj = ROOT / "data/sections_repo.json"
    if pj.exists():
        for r in json.load(open(pj)):
            m = re.match(r"(\d{3}[A-Z]*)$", r["course"])
            if m and und(m.group(1)): seen[m.group(1)[1:]].add(m.group(1)[0])
    for lv in set(old_d) | set(seen):
        digits[lv] = seen[lv] if seen[lv] else old_d[lv]
    out, unresolved = {}, []
    for r in new:
        if not und(r["code"]): continue
        lv = r["code"][1:]
        if lv in ("19S", "29S"):
            unresolved.append((r["code"], "study-abroad credit record")); continue
        ds = sorted(digits.get(lv, []))
        if not ds:
            unresolved.append((r["code"], r["title"])); continue
        for d in ds:
            key = d + lv
            if key in out: continue
            o = next((x for x in old if x["code"] == key), None)
            out[key] = {"number": key, "code": f"ECE {key}", "title": r["title"], "hours": d, "catalog_text": r["text"],
                        "catalog_2526_text": o["text"] if o else None, "catalog_2526_title": o["title"] if o else None}
    live = set()
    for f in (ROOT / "data/registrar").glob("ece_*_agg.tsv"):
        for l in open(f, encoding="utf8"):
            m = re.match(r"ECE (\d{3}[A-Z]*) ", l)
            if m: live.add(m.group(1))
    for r in old:
        if und(r["code"]) and r["code"] in live and r["code"] not in out:
            out[r["code"]] = {"number": r["code"], "code": f"ECE {r['code']}", "title": r["title"], "hours": r["code"][0],
                              "catalog_text": r["text"], "catalog_2526_text": r["text"], "catalog_2526_title": r["title"],
                              "catalog_note": "The 2026-27 catalog does not list this number; the registrar still schedules it."}
    # fold 3-hour/4-hour twins (ECE 302 / 402 ...) and variable-hour families (160/260/360/460, 179K/379K/479K) into one course
    FAMILY = {"60": "3", "79K": "3", "09K": "3"}
    for key in sorted(out):
        lv = key[1:]
        tgt = None
        if lv in FAMILY and key[0] != FAMILY[lv]:
            tgt = FAMILY[lv] + lv
        elif key[0] == "4" and ("3" + lv) in out:
            tgt = "3" + lv
        if tgt and tgt in out and tgt != key:
            out[tgt].setdefault("also_numbers", []).append(key); del out[key]
        elif tgt and tgt not in out:
            out[tgt] = dict(out[key], number=tgt, code=f"ECE {tgt}", hours=tgt[0], also_numbers=[key]); del out[key]
    json.dump(out, open(ROOT / "data/courses.json", "w", encoding="utf8"), indent=1)
    print(len(out), "undergrad courses from the 2026-27 catalog; unresolved hours digit:", unresolved)
    print("levels with several hour digits:", {k: sorted(v) for k, v in digits.items() if len(v) > 1})
    print("2025-26-only (not in 2026-27 catalog):", sorted(r["code"] for r in old if und(r["code"]) and r["code"][1:] not in {x["code"][1:] for x in new}))
