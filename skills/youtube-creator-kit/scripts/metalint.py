#!/usr/bin/env python3
"""metalint.py - check YouTube titles, descriptions, hashtags, tags and thumbnail text BEFORE upload.

    python metalint.py --title "Rain on the Window | Example Artist" --thumb "8 HOURS"
    python metalint.py titles.txt                  # one title per line
    python metalint.py batch.csv                   # columns: title, description, hashtags, tags, thumb
    python metalint.py batch.json --against published_titles.txt
    python metalint.py batch.json --json

Levels, most serious first:
  ERROR  YouTube will refuse it or silently ignore it (100-char title, 5000-byte description,
         < or >, more than 15 hashtags = ALL hashtags ignored, tags over 500 characters)
  DUP    same or nearly the same as another video in the batch or in --against (useful for Shorts:
         every Short gets its own title, description, hashtags and tags)
  WARN   likely to cost clicks (cut off in search, shouting, thumbnail repeats the title)
  TIP    worth a look, not a problem

No score out of 100: a number would pretend to know which title gets clicked, and nothing here can.
Exit code 1 when any ERROR is found. Reads files only; never writes, never goes online.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytcommon import read_text, read_csv, visual_len, words, is_devanagari, emit  # noqa: E402

TITLE_MAX, DESC_MAX_BYTES, TAGS_MAX, HASHTAGS_MAX = 100, 5000, 500, 15
DESKTOP_CUT, MOBILE_CUT, FIRST_LINE = 60, 40, 110
NEAR = 0.85
VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "ultimate", "best", "powerful",
         "secret", "revolutionary", "mindblowing", "epic", "perfect", "unbelievable", "shocking"}
STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with", "your", "you",
        "my", "i", "this", "that", "it", "by", "|", "-"}
HASHTAG = re.compile(r"(?<![\w&])#((?:[^\W_]|[ऀ-ॿ_])+)")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")
FIELDS = {"title": ("title", "video title", "name"),
          "description": ("description", "desc"),
          "hashtags": ("hashtags", "hashtag"),
          "tags": ("tags", "tag", "keywords"),
          "thumb": ("thumb", "thumbnail", "thumbnail text", "thumb text")}


def as_list(v, sep=r"[,\n]"):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(sep, str(v)) if x.strip()]


def normalise(row):
    out = {}
    low = {str(k).strip().lower(): v for k, v in row.items()}
    for field, names in FIELDS.items():
        out[field] = next((low[n] for n in names if n in low and low[n] not in (None, "")), None)
    out["title"] = str(out["title"] or "")
    out["description"] = str(out["description"] or "")
    out["hashtags"] = [h if h.startswith("#") else "#" + h for h in as_list(out["hashtags"], r"[,\s]+")]
    out["tags"] = as_list(out["tags"])
    return out


def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        d = json.loads(read_text(path))
        if isinstance(d, dict):
            d = d.get("videos") or d.get("items") or d.get("shorts") or [d]
        return [normalise(r) for r in d]
    if ext == ".csv":
        rows = read_csv(path)
        head = [h.lower() for h in rows[0]]
        return [normalise(dict(zip(head, r))) for r in rows[1:]]
    return [normalise({"title": line}) for line in read_text(path).splitlines() if line.strip()]


def trigrams(s):
    s = " ".join(words(s))
    return {s[i:i + 3] for i in range(max(1, len(s) - 2))}


def similar(a, b):
    ta, tb = trigrams(a), trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def check(v):
    """Problems for one video as (level, field, message)."""
    out = []
    t, d = v["title"], v["description"]
    n = len(t)
    if not t.strip():
        out.append(("ERROR", "title", "empty title"))
    if n > TITLE_MAX:
        out.append(("ERROR", "title", f"{n} characters - YouTube's limit is {TITLE_MAX}"))
    for field, text in (("title", t), ("description", d)):
        if "<" in text or ">" in text:
            out.append(("ERROR", field, "contains < or > - YouTube rejects these characters"))
    vl = visual_len(t)
    if vl > DESKTOP_CUT:
        out.append(("WARN", "title", f"{vl} visible characters - search results cut near {DESKTOP_CUT}"))
    if vl > MOBILE_CUT:
        shown = t[:MOBILE_CUT].rsplit(" ", 1)[0] if " " in t[:MOBILE_CUT] else t[:MOBILE_CUT]
        out.append(("TIP", "title", f'phones may show only "{shown}..." - the key words should be in there'))
    caps = [w for w in t.split() if len(w) > 2 and w.isupper() and w.isalpha()]
    if len(caps) > 2:
        out.append(("WARN", "title", f"{len(caps)} ALL-CAPS words - more than two reads as spam"))
    vague = sorted({w for w in words(t) if w in VAGUE})
    if vague:
        out.append(("TIP", "title", f"vague word(s): {', '.join(vague)} - a name, number or place says more"))
    if len(EMOJI.findall(t)) > 2:
        out.append(("TIP", "title", "more than two emoji"))
    if t != t.strip() or "  " in t:
        out.append(("TIP", "title", "extra spaces"))

    size = len(d.encode("utf-8"))
    if size > DESC_MAX_BYTES:
        extra = " (Hindi letters take 3 bytes each)" if is_devanagari(d) else ""
        out.append(("ERROR", "description", f"{size} bytes - YouTube's limit is {DESC_MAX_BYTES} bytes{extra}"))
    if d:
        first = d.strip().splitlines()[0] if d.strip() else ""
        if visual_len(first) > FIRST_LINE:
            out.append(("TIP", "description", f"first line is {visual_len(first)} characters - only about "
                                              f"{FIRST_LINE} show above '...more'"))

    tags_in_text = ["#" + h for h in HASHTAG.findall(t + "\n" + d)]
    all_tags = {h.lower() for h in v["hashtags"] + tags_in_text}
    if len(all_tags) > HASHTAGS_MAX:
        out.append(("ERROR", "hashtags", f"{len(all_tags)} different hashtags in title + description + "
                                         f"hashtags - over {HASHTAGS_MAX} and YouTube ignores ALL of them"))
    for h in v["hashtags"]:
        if not re.fullmatch(HASHTAG.pattern.replace("(?<![\\w&])", ""), h):
            out.append(("ERROR", "hashtags", f"'{h}' is not a working hashtag (no spaces or punctuation)"))

    if v["tags"]:
        total = sum(len(x) + (2 if " " in x else 0) for x in v["tags"]) + len(v["tags"]) - 1
        if total > TAGS_MAX:
            out.append(("ERROR", "tags", f"tags add up to {total} characters (spaces in a tag cost 2 more) - "
                                         f"limit {TAGS_MAX}"))
        seen = {}
        for x in v["tags"]:
            seen[x.lower()] = seen.get(x.lower(), 0) + 1
        dup = [k for k, c in seen.items() if c > 1]
        if dup:
            out.append(("TIP", "tags", f"repeated tag(s): {', '.join(dup)}"))
        if any("<" in x or ">" in x for x in v["tags"]):
            out.append(("ERROR", "tags", "a tag contains < or >"))

    if v["thumb"]:
        thumb = str(v["thumb"])
        shared = (set(words(t)) - STOP) & (set(words(thumb)) - STOP)
        if shared:
            out.append(("WARN", "thumb", f"thumbnail repeats the title ({', '.join(sorted(shared))}) - it "
                                         "should add what the title does not say"))
        if len(words(thumb)) > 4:
            out.append(("WARN", "thumb", f"{len(words(thumb))} words on the thumbnail - more than 4 is "
                                         "unreadable at phone size"))
    return out


def duplicates(videos, previous):
    """DUP problems across the batch and against already-published titles."""
    found = {i: [] for i in range(len(videos))}
    keys = (("title", lambda v: v["title"]),
            ("description", lambda v: HASHTAG.sub("", v["description"]).strip()),
            ("hashtags", lambda v: " ".join(sorted(h.lower() for h in v["hashtags"]))),
            ("tags", lambda v: ", ".join(sorted(x.lower() for x in v["tags"]))))
    for field, get in keys:
        vals = [get(v) for v in videos]
        for i in range(len(videos)):
            for j in range(i):
                if not vals[i] or not vals[j]:
                    continue
                if vals[i].lower() == vals[j].lower():
                    found[i].append(("DUP", field, f"same {field} as #{j + 1}"))
                elif field in ("title", "description") and similar(vals[i], vals[j]) >= NEAR:
                    found[i].append(("DUP", field, f"{field} nearly the same as #{j + 1}"))
    for i, v in enumerate(videos):
        for p in previous:
            if v["title"] and (v["title"].lower() == p.lower() or similar(v["title"], p) >= NEAR):
                found[i].append(("DUP", "title", f'already published: "{p}"'))
                break
    return found


ORDER = {"ERROR": 0, "DUP": 1, "WARN": 2, "TIP": 3}


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]

    def opt(name):
        if name in a:
            i = a.index(name)
            val = a[i + 1] if i + 1 < len(a) else ""
            del a[i:i + 2]
            return val
        return None

    title, thumb, against = opt("--title"), opt("--thumb"), opt("--against")
    if title is not None:
        videos = [normalise({"title": title, "thumb": thumb})]
    elif a and os.path.exists(a[0]):
        videos = load(a[0])
        if thumb:
            for v in videos:
                v["thumb"] = v["thumb"] or thumb
    else:
        print(__doc__)
        sys.exit(2)
    previous = []
    if against:
        previous = [v["title"] for v in load(against) if v["title"]]

    dups = duplicates(videos, previous)
    results = []
    for i, v in enumerate(videos):
        probs = sorted(check(v) + dups[i], key=lambda p: ORDER[p[0]])
        results.append({"n": i + 1, "title": v["title"], "visible_chars": visual_len(v["title"]),
                        "problems": [{"level": l, "field": f, "message": m} for l, f, m in probs]})
    counts = {k: sum(1 for r in results for p in r["problems"] if p["level"] == k) for k in ORDER}
    if as_json:
        emit({"videos": results, "counts": counts})
    else:
        for r in results:
            print(f'\n  #{r["n"]}  "{r["title"]}"  ({r["visible_chars"]} visible chars)')
            if not r["problems"]:
                print("      ok")
            for p in r["problems"]:
                print(f'      {p["level"]:<5} {p["field"]:<11} {p["message"]}')
        print(f"\n  {len(results)} video(s): " + ", ".join(f"{counts[k]} {k}" for k in ORDER) + "\n")
    sys.exit(1 if counts["ERROR"] else 0)


if __name__ == "__main__":
    main()
