"""Download the selected syllabus PDFs and extract text (pdftotext; flags scanned/empty files)."""
import json, re, subprocess, pathlib
from common import fetch, ROOT

ds = json.load(open(ROOT / "data/dataset.json", encoding="utf8"))
out = ROOT / "data/syllabi"; out.mkdir(exist_ok=True)
seen, stats = {}, {"pdf": 0, "empty": 0}
for num, c in ds["courses"].items():
    for e in c["instructors"]:
        u = e["pdf_url"]          # topics are extracted from the newest *PDF* syllabus; web-only ones are flagged
        e["syllabus_is_web_only"] = bool(e["syllabus_url"]) and "/download/" not in e["syllabus_url"]
        if not u: continue
        sid = re.search(r"/download/(\d+)/", u).group(1)
        e["syllabus_id"] = sid
        if sid in seen: continue
        pdf = out / f"{sid}.pdf"
        if not pdf.exists(): pdf.write_bytes(fetch(u, binary=True))
        txt = out / f"{sid}.txt"
        if not (txt.exists() and txt.read_text(encoding="utf8", errors="ignore").startswith("[Transcribed")):   # hand transcriptions of scanned PDFs are kept
            subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=False)
        n = len(txt.read_text(encoding="utf8", errors="ignore")) if txt.exists() else 0
        seen[sid] = n; stats["pdf"] += 1; stats["empty"] += n < 1500
json.dump(ds, open(ROOT / "data/dataset.json", "w", encoding="utf8"), indent=1)
print(stats, "distinct syllabi")
print("empty/scanned:", [k for k, v in seen.items() if v < 1500])
