"""Merge repository sections (with syllabi) and registrar sections into data/sections.json.

Offered rule (project owner's): a syllabus in the repository => the section was offered (even if the registrar shows it cancelled);
otherwise the registrar must show >=1 non-cancelled section for that course/topic in that term.
Spring 2027 = registrar only (a plan; no syllabi yet). Conflicts are written to data/offered_conflicts.json.
"""
import json, re, collections
from common import ROOT

repo = json.load(open(ROOT / "data/sections_repo.json", encoding="utf8"))
ov = json.load(open(ROOT / "data/overrides.json", encoding="utf8"))
courses = json.load(open(ROOT / "data/courses.json", encoding="utf8"))
SPLIT, DROP = set(ov["split_courses"]), set(ov["not_in_catalog_dropped"])
ALIAS_CODE = dict(ov.get("code_aliases", {}))
for k, v in courses.items():
    for o in v.get("also_numbers", []):
        ALIAS_CODE[o] = k
norm_code = lambda c: ALIAS_CODE.get(c, c)
TERMS = {"Fall 2025": "20259", "Spring 2026": "20262", "Fall 2026": "20269", "Spring 2027": "20272"}
slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def key_for(code, topic):
    return f"{code}-{slug(topic)}" if code in SPLIT else code


def name_tokens(n):
    return re.findall(r"[a-z]+", n.lower())


def same_person(reg_name, repo_name):
    last, first = [p.strip() for p in reg_name.split(",", 1)] if "," in reg_name else (reg_name.split()[-1], " ".join(reg_name.split()[:-1]))
    lt, ft, rt = name_tokens(last), name_tokens(first), name_tokens(repo_name)
    if not lt or not ft or not rt:
        return False
    return (all(t in rt for t in lt) or rt[-1] in lt) and rt[0][:1] == ft[0][:1]


def pretty(reg_name):
    last, first = [p.strip() for p in reg_name.split(",", 1)]
    last_t = re.sub(r"(?<![A-Za-z])Mc(\w)", lambda m: "Mc" + m.group(1).upper(), last.title())
    toks = first.split()
    given = toks[1] if len(toks[0]) == 1 and len(toks) > 1 else toks[0]
    return f"{given.title()} {last_t}"


# ---- repository sections -> course keys (variable-topic numbers get one key per topic)
merged, conflicts = [], collections.defaultdict(list)
for s in repo:
    code = norm_code(s["course"])
    if code in DROP:
        conflicts["dropped_not_in_catalog"].append([s["term"], code]); continue
    if code in SPLIT:
        topic = ov["repo_title_topics"].get(s["title"].strip())
        if not topic and s["instructors"]:
            topic = ov["instructor_term_topic"].get(f'{s["instructors"][0]}|{s["term"]}')
        if not topic:
            raise SystemExit(f"no topic for {code} {s['term']} {s['instructors']} {s['title']}")
        s = dict(s, topic=topic, course=key_for(code, topic), base=code)
    else:
        s = dict(s, course=code, base=code, topic=None)
    merged.append(s)
cover = collections.defaultdict(list)
for s in merged:
    cover[(s["course"], s["term"])] += s["instructors"]

# ---- registrar aggregates
reg = collections.defaultdict(lambda: {"live": 0, "cancelled": 0, "instr": [], "titles": set()})
for term, tid in TERMS.items():
    for line in open(ROOT / f"data/registrar/ece_{tid}_agg.tsv", encoding="utf8"):
        head, uniq, st, ins = line.rstrip("\n").split("|")
        m = re.match(r"ECE (\d{3}[A-Z]*) (.*)", head)
        code, title = norm_code(m.group(1)), m.group(2)
        if code in DROP:
            continue
        if code not in courses and code not in SPLIT:
            conflicts["registrar_number_not_in_course_list"].append([term, head]); continue
        if code in SPLIT:
            topic = ov["registrar_title_topics"].get(title.strip())
            if not topic:
                raise SystemExit(f"unmapped registrar topic title: {term} {head}")
            key = key_for(code, topic)
        else:
            key, topic = code, None
        r = reg[(key, term)]
        r.update(base=code, topic=topic)
        for kv in st.split(","):
            k, n = kv.rsplit(":", 1)
            r["cancelled" if k == "cancelled" else "live"] += int(n)
        r["instr"] += [x.strip() for x in ins.split(";") if x.strip()]
        r["titles"].add(title)

for (key, term), r in sorted(reg.items()):
    if r["live"] <= 0:
        if key not in [s["course"] for s in merged if s["term"] == term]:
            conflicts["registrar_all_cancelled_no_syllabus"].append([term, key])
        continue
    have = cover.get((key, term), [])
    missing = [n for n in dict.fromkeys(r["instr"]) if not any(same_person(n, h) for h in have)]
    if not r["instr"] and not have:
        missing = [None]
    for n in missing:
        if r["cancelled"] and n is not None and have:
            conflicts["ambiguous_cancelled_mix"].append([term, key, n, f"{r['live']} live, {r['cancelled']} cancelled sections"])
        merged.append({"term": term, "course": key, "base": r["base"], "topic": r["topic"], "unique": "", "title": sorted(r["titles"])[0],
                       "instructors": [pretty(n)] if n else [], "syllabus_path": None, "cvs": [], "source": "registrar", "_reg": n})
        conflicts["registrar_only_added"].append([term, key, n])
        cover[(key, term)] += [pretty(n)] if n else []
live_keys = {(k, t) for (k, t), r in reg.items() if r["live"] > 0}
for s in merged:
    if s.get("source") != "registrar" and (s["course"], s["term"]) not in live_keys:
        conflicts["syllabus_but_registrar_cancelled_or_absent"].append([s["term"], s["course"], s["instructors"]])
for k in list(conflicts):
    seen = {json.dumps(x): x for x in conflicts[k]}
    conflicts[k] = list(seen.values())

# ---- upgrade initial-only repo names / unify registrar-added names with repo names
reg_names = {x for v in reg.values() for x in v["instr"]}
repo_names = {n for s in merged if s.get("source") != "registrar" for n in s["instructors"]}


def upgrade(n):
    if len(n.split()[0]) > 1:
        return n
    m = [r for r in reg_names if same_person(r, n)]
    return (pretty(m[0]).split()[0] + " " + " ".join(n.split()[1:])) if len({pretty(x) for x in m}) == 1 else n


for s in merged:
    if s.get("source") == "registrar" and s["instructors"]:
        m = [x for x in repo_names if same_person(s["_reg"], x)]
        up = {upgrade(x) for x in m}
        s["instructors"] = [next(iter(up))] if len(up) == 1 else s["instructors"]
    else:
        s["instructors"] = [upgrade(n) for n in s["instructors"]]
    s["instructors"] = sorted({ov.get("instructor_aliases", {}).get(x, x) for x in s["instructors"]})
    s.pop("_reg", None)

json.dump(merged, open(ROOT / "data/sections.json", "w", encoding="utf8"), indent=1)
json.dump(conflicts, open(ROOT / "data/offered_conflicts.json", "w", encoding="utf8"), indent=1)
print(len(repo), "repo sections +", len(conflicts["registrar_only_added"]), "registrar-only =", len(merged))
for k, v in conflicts.items():
    print(" ", k, len(v))
