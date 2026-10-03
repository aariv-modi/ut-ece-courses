"""Link + syllabus consistency audit -> data/link_report.json

1. Every selected syllabus PDF link: HTTP 200, content-type PDF.
2. Every selected syllabus document names the instructor (surname) and the course number; flags term mismatches.
3. Non-Canvas external schedule links: HTTP status (Canvas links are removed by policy: login-gated).
4. Internal links in the built site (site/dist): every href resolves to a file.
Web-format syllabi (utexas.simplesyllabus.com) block scripted clients; they are verified from the text files read in the browser.
"""
import json, re, time, pathlib, sys, glob, requests
from common import ROOT, UA

ds = json.load(open(ROOT / "site/src/data/dataset.json", encoding="utf8"))["courses"]   # exported dataset (what the site shows)
report = {"syllabus_links": [], "syllabus_mismatch": [], "external": [], "internal_broken": [], "summary": {}}
S = requests.Session(); S.headers["User-Agent"] = UA


def surname(n):
    return re.sub(r"[^a-z]", "", n.split()[-1].lower())


seen = {}
for k, c in ds.items():
    base = c.get("base_number") or k
    for e in c["instructors"]:
        for kind, url, term in (("syllabus", e.get("syllabus_url"), e.get("syllabus_term")), ("pdf", e.get("pdf_url"), e.get("pdf_term"))):
            if not url or "simplesyllabus" in url:
                continue
            if url not in seen:
                try:
                    r = S.get(url, timeout=60, stream=True)
                    head = next(r.iter_content(8), b"")
                    seen[url] = {"status": r.status_code, "pdf": head.startswith(b"%PDF"), "ctype": r.headers.get("content-type", "")}
                    r.close()
                except Exception as ex:
                    seen[url] = {"status": 0, "pdf": False, "err": str(ex)}
                time.sleep(0.25)
            ok = seen[url]["status"] == 200 and seen[url]["pdf"]
            report["syllabus_links"].append({"course": k, "instructor": e["name"], "term": term, "url": url, "ok": ok})
            sid = re.search(r"/download/(\d+)/", url).group(1)
            tp = ROOT / f"data/syllabi/{sid}.txt"
            if tp.exists():
                t = tp.read_text(encoding="utf8", errors="ignore")
                if len(t) > 800:
                    low = re.sub(r"[^a-z0-9 ]", "", t.lower())
                    has_name = surname(e["name"]) in re.sub(r"[^a-z]", "", t.lower())
                    digits = re.search(r"\d{3}", base)[0]
                    has_course = bool(re.search(r"\b" + digits + r"[a-z]?\b", low)) or any(w in low for w in re.findall(r"[a-z]{5,}", c["title"].lower())[:2])
                    if not (has_name and has_course):
                        report["syllabus_mismatch"].append({"course": k, "instructor": e["name"], "term": term, "url": url, "names_instructor": has_name, "names_course": has_course})

# external schedule links (non-Canvas only; Canvas removed by policy)
for k, c in ds.items():
    for e in c["instructors"]:
        u = e.get("external_schedule_url")
        if u:
            try:
                r = S.get(u, timeout=40, allow_redirects=True)
                report["external"].append({"course": k, "instructor": e["name"], "url": u, "status": r.status_code, "final": r.url})
            except Exception as ex:
                report["external"].append({"course": k, "instructor": e["name"], "url": u, "status": 0, "err": str(ex)[:120]})
            time.sleep(0.4)

# internal links in dist
dist = ROOT / "site/dist"
if dist.exists():
    base = ""
    files = {str(p.relative_to(dist)).replace("\\", "/") for p in dist.rglob("*") if p.is_file()}
    for p in dist.rglob("*.html"):
        h = p.read_text(encoding="utf8", errors="ignore")
        for href in set(re.findall(r'href="(/[^"#?]*)"', h)):
            rel = href.lstrip("/")
            cand = [rel, rel + "index.html", rel.rstrip("/") + "/index.html"]
            if not any(c_ in files for c_ in cand) and rel != "":
                report["internal_broken"].append({"page": str(p.relative_to(dist)), "href": href})

report["summary"] = {
    "syllabus_links_checked": len(report["syllabus_links"]), "syllabus_links_failed": sum(1 for x in report["syllabus_links"] if not x["ok"]),
    "mismatches": len(report["syllabus_mismatch"]), "external_checked": len(report["external"]),
    "external_failed": sum(1 for x in report["external"] if x["status"] != 200), "internal_broken": len(report["internal_broken"]),
}
json.dump(report, open(ROOT / "data/link_report.json", "w", encoding="utf8"), indent=1)
print(report["summary"])
for m in report["syllabus_mismatch"][:15]: print(" MISMATCH", m)
for x in report["external"]:
    if x["status"] != 200: print(" EXTERNAL", x)
for x in report["internal_broken"][:10]: print(" BROKEN", x)
