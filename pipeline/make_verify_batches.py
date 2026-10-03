"""Split topic_out courses (except 360C, re-analysed separately) into 8 balanced verification buckets -> data/topic_verify/_v1..8.json"""
import json, glob, os
from common import ROOT

ks = sorted(os.path.basename(f)[:-5] for f in glob.glob(str(ROOT / "data/topic_in/*.json")) if "_batch" not in f)
ks = [k for k in ks if k != "360C"]
w = {k: len(json.load(open(ROOT / f"data/topic_in/{k}.json", encoding="utf8"))["instructors"]) for k in ks}
ks.sort(key=lambda k: -w[k])
buckets, load = [[] for _ in range(8)], [0] * 8
for k in ks:
    i = load.index(min(load))
    buckets[i].append(k); load[i] += w[k] + 1
(ROOT / "data/topic_verify").mkdir(exist_ok=True)
for i, b in enumerate(buckets):
    json.dump(b, open(ROOT / f"data/topic_verify/_v{i+1}.json", "w"))
print(load, [len(b) for b in buckets], len(ks))
