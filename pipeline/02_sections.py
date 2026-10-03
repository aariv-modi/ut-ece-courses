"""Syllabi & CVs repository sections for dept ECE, undergraduate, Fall 2025 / Spring 2026 / Fall 2026 -> data/sections_repo.json
(the repository lists only sections that have a syllabus; the registrar supplies the rest in 02b)."""
import re, json, html
from bs4 import BeautifulSoup
from common import fetch, ROOT

REPO = "https://utdirect.utexas.edu/apps/student/coursedocs/nlogon/"
PAST = [(2025, "Fall", 9), (2026, "Spring", 2), (2026, "Fall", 9)]
txt = lambda el: re.sub(r"\s+", " ", html.unescape(el.get_text(" "))).strip()


def past_term(year, name, code, dept="ECE"):
    soup = BeautifulSoup(fetch(REPO, params={"year": year, "semester": code, "department": dept, "course_type": "In Residence", "search": "Search"}), "html.parser")
    rows = []
    for tr in soup.select("#results_table tbody tr"):
        td = tr.find_all("td")
        if len(td) < 7:
            continue
        num = txt(td[1]).replace(f"{dept} ", "")
        if not re.fullmatch(r"\d{3}[A-Z]*", num) or int(num[1:3]) >= 80:
            continue
        instr = [s.strip() for s in td[4].get_text("\n").split("\n") if s.strip()]
        syl = td[6].find("a", href=True)
        cv = [{"name": a.get_text(strip=True).replace(" CV", ""), "url": a["href"]} for a in td[5].find_all("a", href=True)]
        rows.append({"term": f"{name} {year}", "course": num, "unique": txt(td[2]), "title": txt(td[3]),
                     "instructors": instr, "syllabus_path": syl["href"] if syl else None, "cvs": cv})
    return rows


if __name__ == "__main__":
    sections = []
    for y, n, c in PAST:
        r = past_term(y, n, c); sections += r
        print(f"{n} {y}: {len(r)} undergrad sections, {len({x['course'] for x in r})} courses, {sum(1 for x in r if x['syllabus_path'])} with syllabus")
    json.dump(sections, open(ROOT / "data/sections_repo.json", "w", encoding="utf8"), indent=1)
