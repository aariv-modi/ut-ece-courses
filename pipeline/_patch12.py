p = "12_catalog_text.py"
s = open(p, encoding="utf8").read()


def r(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b)


r('for i in (1, 2, 3):\n    for line in open(ROOT / f"data/registrar/math_details_{i}.tsv", encoding="utf8"):',
  'for i in (1, 2, 3, 4):\n    for line in open(ROOT / f"data/registrar/ece_details_{i}.tsv", encoding="utf8"):')
r(r'''def key_of(head):
    m = re.match(r"M (\d{3}[A-Z]*) (.*)", head)
    code, title = m.group(1), m.group(2).strip()
    if code in SPLIT:
        return f"{code}-{slug(ov['registrar_title_topics'][title])}", True
    return code, bool(re.search(r"(:|-)\s*(HON|AP: HON|HONORS)\b|HONORS|: HON", title))''',
  r'''ALIAS = dict(ov.get("code_aliases", {}))
for k_, v_ in courses.items():
    for o_ in v_.get("also_numbers", []):
        ALIAS[o_] = k_


def key_of(head):
    m = re.match(r"ECE (\d{3}[A-Z]*) (.*)", head)
    code, title = ALIAS.get(m.group(1), m.group(1)), m.group(2).strip()
    if code in SPLIT:
        return f"{code}-{slug(ov['registrar_title_topics'][title])}", False
    return code, False''')
r(r'''            if m2: rec["prerequisites"] = "Upper-division standing; additional prerequisites vary with the topic. Additional prerequisite: " + tidy(m2.group(1))''',
  r'''            if m2 and reg_pre: rec["prerequisites"] = reg_pre.rstrip(".") + ". Additional prerequisite: " + tidy(m2.group(1))''')
r('rec["prerequisites"] = reg_pre or ("Upper-division standing; additional prerequisites vary with the topic" if c.get("base_number") else "None listed")',
  'rec["prerequisites"] = reg_pre or "None listed"')
open(p, "w", encoding="utf8").write(s)
print("patched")
