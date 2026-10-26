#!/usr/bin/env python3
"""outliers.py - find videos that beat their OWN channel, and what those videos have in common.

  Step 1, collect (goes online - ask the user first; reads public channel pages through yt-dlp):
    python outliers.py --collect https://www.youtube.com/@SomeChannel @Other --limit 60 --out niche.json
  Step 2, rank (offline):
    python outliers.py niche.json
    python outliers.py niche.json --min 3 --kind shorts --json

A channel URL with no tab collects both /videos and /shorts. Shorts and long videos are ranked
SEPARATELY, against their own channel's median - mixing them makes every Short look like a flop or
every long video look like a hit.

Raw views rank channel size, not ideas. A video at 5x its channel's median is the one worth
studying, whether the channel is big or small. Channels with fewer than 5 videos of a kind are
skipped (a median of 2 is not a median).

The "what they share" section compares title features of the outliers against everything else.
It is a pattern in a small sample, not a cause - say so when presenting it.
Input also accepts a plain list [{"channel","title","views","url","duration"}] or raw `yt-dlp -J`.
"""
import json, os, re, shutil, statistics, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytcommon import read_text, visual_len, is_devanagari, emit  # noqa: E402

MIN_PER_CHANNEL = 5
SHORT_MAX = 180


def kind_of(url, duration, tab=""):
    if "/shorts" in (url or "") or tab == "shorts":
        return "shorts"
    if duration:
        return "shorts" if duration <= SHORT_MAX and tab != "videos" else "long"
    return "long" if tab == "videos" else "unknown"


def from_ytdlp(d, tab=""):
    ch = d.get("channel") or d.get("uploader") or re.sub(r"\s*-\s*(Videos|Shorts)$", "", d.get("title") or "?")
    out = []
    for e in d.get("entries") or []:
        if not e or e.get("view_count") is None:
            continue
        if e.get("_type") == "playlist":
            out += from_ytdlp(e, tab)
            continue
        url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
        out.append({"channel": e.get("channel") or ch, "title": e.get("title") or "",
                    "views": int(e["view_count"]), "url": url, "duration": e.get("duration"),
                    "kind": kind_of(url, e.get("duration"), tab)})
    return out


def collect(urls, limit, out_path):
    exe = shutil.which("yt-dlp")
    if not exe:
        print("yt-dlp is not installed or not on PATH (pip install yt-dlp)")
        sys.exit(2)
    rows = []
    for u in urls:
        if u.startswith("@"):
            u = "https://www.youtube.com/" + u
        u = u.rstrip("/")
        tabs = [u] if re.search(r"/(videos|shorts|streams)$", u) else [u + "/videos", u + "/shorts"]
        for t in tabs:
            tab = t.rsplit("/", 1)[-1]
            print(f"  reading {t} ...", flush=True)
            p = subprocess.run([exe, "--flat-playlist", "-J", "--no-warnings", "--playlist-end", str(limit), t],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if p.returncode != 0 or not p.stdout.strip():
                print(f"    skipped: {(p.stderr or 'no output').strip().splitlines()[-1][:150]}")
                continue
            got = from_ytdlp(json.loads(p.stdout), tab)
            print(f"    {len(got)} videos")
            rows += got
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"\n  saved {len(rows)} videos to {out_path}\n  next: python outliers.py {out_path}\n")


def load(path):
    d = json.loads(read_text(path))
    if isinstance(d, dict):
        return from_ytdlp(d) if "entries" in d else d.get("videos", [])
    rows = []
    for r in d:
        url, dur = r.get("url", ""), r.get("duration")
        rows.append({"channel": r.get("channel", "?"), "title": r.get("title", ""),
                     "views": int(r.get("views", r.get("view_count", 0)) or 0), "url": url, "duration": dur,
                     "kind": r.get("kind") or kind_of(url, dur)})
    return rows


FEATURES = {
    "a number in the title": lambda t: bool(re.search(r"\d", t)),
    "a question": lambda t: "?" in t,
    "Hindi script": is_devanagari,
    "emoji": lambda t: bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿]", t)),
    "an ALL-CAPS word": lambda t: any(len(w) > 2 and w.isupper() and w.isalpha() for w in t.split()),
    "a | or ( ) or [ ]": lambda t: bool(re.search(r"[|()\[\]]", t)),
    "a hashtag in the title": lambda t: "#" in t,
    "a short title (under 40 chars)": lambda t: visual_len(t) < 40,
    "a long title (over 70 chars)": lambda t: visual_len(t) > 70,
}


def rank(rows, lo, kind_filter=None):
    groups = {}
    for r in rows:
        r.setdefault("kind", kind_of(r.get("url", ""), r.get("duration")))
        if r["kind"] == "unknown" or (kind_filter and r["kind"] != kind_filter):
            continue
        groups.setdefault((r["channel"], r["kind"]), []).append(r)
    scored, skipped = [], []
    for (ch, kind), vids in groups.items():
        if len(vids) < MIN_PER_CHANNEL:
            skipped.append({"channel": ch, "kind": kind, "videos": len(vids)})
            continue
        med = statistics.median(v["views"] for v in vids) or 1
        for v in vids:
            scored.append(dict(v, median=int(med), multiple=round(v["views"] / med, 2)))
    out = sorted((s for s in scored if s["multiple"] >= lo), key=lambda s: -s["multiple"])
    rest = [s for s in scored if s["multiple"] < lo]
    shared = []
    if len(out) >= 3 and rest:
        for name, f in FEATURES.items():
            a = sum(1 for s in out if f(s["title"])) / len(out)
            b = sum(1 for s in rest if f(s["title"])) / len(rest)
            if abs(a - b) >= 0.15 and sum(1 for s in out if f(s["title"])) >= 2 or (a == 0 and b >= 0.3):
                shared.append({"feature": name, "outliers": round(a * 100), "others": round(b * 100)})
        shared.sort(key=lambda x: -abs(x["outliers"] - x["others"]))
    return out, skipped, shared, len(scored)


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return default

    if "--collect" in a:
        a.remove("--collect")
        limit, out_path = int(opt("--limit", "60")), opt("--out", "collected.json")
        if not a:
            print(__doc__)
            sys.exit(2)
        collect(a, limit, out_path)
        return
    lo, kind = float(opt("--min", "2")), opt("--kind")
    top = int(opt("--top", "15"))
    if not a or not os.path.exists(a[0]):
        print(__doc__)
        sys.exit(2)
    rows = load(a[0])
    out, skipped, shared, n = rank(rows, lo, kind)
    if as_json:
        emit({"outliers": out[:top], "count": len(out), "ranked": n, "skipped": skipped, "shared": shared})
        return
    print(f"\n  {len(rows)} videos, {n} ranked, {len(out)} at {lo}x their channel's median or better\n")
    for s in out[:top]:
        print(f"  {s['multiple']:6.1f}x  {s['views']:>11,}  median {s['median']:>9,}  {s['kind']:<6} "
              f"{s['channel'][:20]:<20}  {s['title'][:60]}")
    if not out:
        print("  nothing cleared the bar - lower --min or collect more videos per channel")
    if shared:
        print("\n  what the outliers' titles have, compared with the rest (a pattern, not a cause):")
        for x in shared:
            print(f"    {x['feature']:<32} outliers {x['outliers']:3d}%   others {x['others']:3d}%")
    if skipped:
        print("\n  skipped (under 5 videos of that kind): " +
              ", ".join(f"{s['channel']} {s['kind']} ({s['videos']})" for s in skipped[:8]))
    print()


if __name__ == "__main__":
    main()
