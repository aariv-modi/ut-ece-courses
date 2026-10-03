"""Final export from the audited sources -> site/src/data/dataset.json + site/public/search-index.json

Inputs : data/dataset.json (offerings, instructors, syllabus selection), data/catalog_text.json (official description,
         prerequisites, notes), data/topic_out/<course>.json (topic list + coverage with verbatim evidence),
         data/history*.json, data/aliases.json, data/overrides.json
"""
import json, re, collections
from common import ROOT

ds = json.load(open(ROOT / "data/dataset.json", encoding="utf8"))
ct = json.load(open(ROOT / "data/catalog_text.json", encoding="utf8"))
aliases = json.load(open(ROOT / "data/aliases.json", encoding="utf8"))
overrides = json.load(open(ROOT / "data/overrides.json", encoding="utf8"))
hist = json.load(open(ROOT / "data/history.json", encoding="utf8"))
topic_dir = ROOT / "data/topic_out"
removed_links = []
stats = collections.Counter()
index = []
nums = lambda s: set(re.findall(r"\b\d{3}[A-Z]?\b", s or ""))


def _hit(needle, text):
    return re.search(r"(?<![a-z0-9])" + re.escape(needle.lower()) + r"s?(?![a-z0-9])", text) is not None


def alias_for(topic):
    """Related search terms (word-boundary match on the concept or a distinctive alias). Search-only; the UI labels such hits."""
    t, out = topic.lower(), []
    for concept, al in aliases.items():
        if any(_hit(k, t) for k in [concept] + [a for a in al if " " in a or len(a) >= 5]):
            out += [concept] + al
    return " ".join(dict.fromkeys(out))


def clean_url(u, who):
    """Public, valid URLs only: drop Canvas (login-gated) and non-URL text; add a missing https://."""
    if not u:
        return None
    u = u.strip()
    if u in overrides.get("dead_external_urls", []):
        removed_links.append({"who": who, "url": u, "reason": "dead link (HTTP 404)"}); return None
    if re.search(r"instructure\.com|canvas", u, re.I):
        removed_links.append({"who": who, "url": u, "reason": "Canvas (login-gated, not public)"}); return None
    if not re.match(r"^(https?://|www\.|[A-Za-z0-9.-]+\.(edu|com|org|io|net)(/|$))", u):
        removed_links.append({"who": who, "url": u, "reason": "not a URL"}); return None
    return u if u.startswith("http") else "https://" + u


KIND = {"stated": "explicit", "possible": "possible", "textbook": "textbook_chapter"}

for num, c in ds["courses"].items():
    rec = ct.get(num, {})
    if c["status"] != "active":
        c["last_offered_earlier"] = hist.get(num)
    # ---- official text
    if not c.get("base_number") and rec.get("description"):
        c["description"], c["description_source"] = rec["description"], rec["description_source"]
    c["prerequisites_text"] = rec.get("prerequisites") or ""
    c["prerequisites_source"] = rec.get("prerequisites_source") or ""
    c["notes"] = rec.get("notes", [])
    t = json.load(open(topic_dir / f"{num}.json", encoding="utf8")) if (topic_dir / f"{num}.json").exists() else None
    desc_votes, notes_pre = [], []
    cols = []
    for e in c["instructors"]:
        e["topics"] = []
        meta = (t or {}).get("instructors", {}).get(e["name"])
        if not meta:
            continue
        e["detail_level"] = meta.get("detail_level")
        e["textbooks"] = meta.get("textbooks") or []
        e["external_schedule_url"] = clean_url(meta.get("external_schedule_url"), f"{c['code']} / {e['name']}")
        if meta.get("document_ok") is False or (meta.get("document_note") and re.search(r"dated|stale|wrong|different (term|course)|filed", meta["document_note"], re.I)):
            e["syllabus_note"] = meta.get("document_note") or "This document may not match the course/term it is filed under."
        if meta.get("description_stated"):
            desc_votes.append(meta["description_stated"])
        ps = meta.get("prerequisites_stated")
        if ps:
            sn, rn = nums(ps), nums(c["prerequisites_text"])
            if c.get("base_number") or (sn and rn and not (sn <= rn or rn <= sn)):
                notes_pre.append({"instructor": e["name"], "term": e.get("syllabus_term"), "text": ps})
    c["prerequisites_notes"] = notes_pre
    if c.get("base_number"):
        c["description_is_generic"] = not desc_votes
        if desc_votes:
            c["description"] = collections.Counter(desc_votes).most_common(1)[0][0]
    # ---- topics + matrix
    if t and t.get("topics"):
        byname = {e["name"]: e for e in c["instructors"]}
        for pos, tp in enumerate(t["topics"]):
            for name, cov in tp["coverage"].items():
                e = byname.get(name)
                if not e:
                    continue
                e["topics"].append({"topic": tp["label"], "as_written": cov.get("as_written") or tp["label"], "kind": KIND[cov["status"]],
                                    "hedged": cov["status"] == "possible", "evidence": cov["evidence"], "where": cov.get("where", ""), "pos": pos})
        cols = [e for e in c["instructors"] if e["topics"]]
        keyof = {e["name"]: i for i, e in enumerate(cols)}
        rows = []
        for pos, tp in enumerate(t["topics"]):
            cells = {}
            for name, cov in tp["coverage"].items():
                if name in keyof:
                    cells[keyof[name]] = {"kind": cov["status"], "topic": cov.get("as_written") or tp["label"], "evidence": cov["evidence"], "where": cov.get("where", ""), "also": []}
            if cells:
                rows.append({"label": tp["label"], "cells": cells, "n": len(cells), "pos": pos})
        rows.sort(key=lambda r: (-r["n"], r["pos"]))
        c["matrix"] = {"columns": [{"name": e["name"], "term": e.get("syllabus_term"), "url": e.get("syllabus_url")} for e in cols], "rows": rows}
        stats["courses_with_matrix"] += 1
        for e in cols:
            for tp in e["topics"]:
                index.append({"id": len(index), "course": c["code"], "title": c["title"], "instructor": e["name"], "term": e.get("syllabus_term"),
                              "topic": tp["topic"], "kind": "possible" if tp["hedged"] else tp["kind"], "evidence": tp["evidence"],
                              "aliases": alias_for(tp["topic"]), "url": "__BASE__course/" + num.lower() + "/"})
    else:
        c.pop("matrix", None)

(ROOT / "site/src/data").mkdir(parents=True, exist_ok=True)
json.dump(ds, open(ROOT / "site/src/data/dataset.json", "w", encoding="utf8"))
json.dump(index, open(ROOT / "site/public/search-index.json", "w", encoding="utf8"))
json.dump(removed_links, open(ROOT / "data/removed_links.json", "w", encoding="utf8"), indent=1)
print(dict(stats), "| index entries:", len(index), "| links removed:", len(removed_links))
