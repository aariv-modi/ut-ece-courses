"""Shared helpers: polite cached HTTP fetching."""
import hashlib, time, pathlib, requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
UA = "ut-ece-course-explorer/0.1 (student project)"
_last = [0.0]


def fetch(url, params=None, binary=False, delay=0.7):
    """GET with on-disk cache and throttling. Returns text or bytes."""
    key = hashlib.sha1((url + repr(sorted((params or {}).items()))).encode()).hexdigest()
    p = CACHE / key
    if p.exists():
        return p.read_bytes() if binary else p.read_text(encoding="utf8")
    wait = delay - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=60)
    _last[0] = time.time()
    r.raise_for_status()
    if binary:
        p.write_bytes(r.content)
        return r.content
    p.write_text(r.text, encoding="utf8")
    return r.text
