#!/usr/bin/env python3
"""studio_report.py - a channel check-up from YouTube Studio's own export, with real numbers only.

    python studio_report.py "Table data.csv"
    python studio_report.py "Table data.csv" --kind shorts --json

Get the file: Studio -> Analytics -> Advanced mode -> Content tab -> pick the date range ->
download icon -> Comma-separated values. Unzip; the file is "Table data.csv". Add the columns you
want first with the + button: Impressions, Impressions click-through rate, Average percentage viewed.

Reports, separately for Shorts (<= 3 min) and long videos:
  - how many, median views, the top and bottom five as a multiple of that median
  - best click-through rate (only videos with 500+ impressions) and best average % viewed
  - views by publish weekday (only days with 3+ videos) and the upload rhythm (gaps between uploads)
Columns are matched by name, so any language order works as long as the names are English.
Reads files only; never writes, never goes online.
"""
import os, statistics, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytcommon import read_csv, parse_time, emit  # noqa: E402

COLS = {"title": ("video title", "title"), "published": ("publish time", "published", "publish date"),
        "duration": ("duration",), "views": ("views",), "impressions": ("impressions",),
        "ctr": ("click-through", "ctr"), "avg_pct": ("average percentage viewed", "avg % viewed"),
        "avg_dur": ("average view duration",), "subs": ("subscribers",)}
DATE_FORMATS = ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%B %d, %Y")
SHORT_MAX, MIN_IMPRESSIONS, MIN_DAY = 180, 500, 3


def num(s):
    s = (s or "").replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        return parse_time(s) if ":" in s else float(s)
    except ValueError:
        return None


def date(s):
    s = (s or "").strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def load(path):
    rows = read_csv(path)
    head = [h.lower() for h in rows[0]]
    idx = {}
    for key, names in COLS.items():
        # "impressions" must not grab the click-through column, so prefer the shortest matching header
        hits = [i for i, h in enumerate(head) if any(n in h for n in names) and i not in idx.values()]
        if key == "impressions":
            hits = [i for i in hits if "click" not in head[i]]
        if hits:
            idx[key] = min(hits, key=lambda i: len(head[i]))
    if "views" not in idx or "title" not in idx:
        sys.exit("could not find 'Video title' and 'Views' columns - is this the Advanced mode Content export?")
    vids = []
    for r in rows[1:]:
        r = r + [""] * (len(head) - len(r))
        title = r[idx["title"]]
        if not title or r[0].strip().lower() == "total":
            continue
        v = {"title": title}
        for k in ("duration", "views", "impressions", "ctr", "avg_pct", "avg_dur", "subs"):
            v[k] = num(r[idx[k]]) if k in idx else None
        v["published"] = date(r[idx["published"]]) if "published" in idx else None
        if v["views"] is None:
            continue
        v["kind"] = "shorts" if v["duration"] is not None and v["duration"] <= SHORT_MAX else (
            "long" if v["duration"] is not None else "all")
        vids.append(v)
    return vids, sorted(idx)


def section(vids):
    med = statistics.median(v["views"] for v in vids) or 1
    for v in vids:
        v["multiple"] = round(v["views"] / med, 2)
    by_views = sorted(vids, key=lambda v: -v["views"])
    # bottom five: leave out the newest week, which has not had time to collect views
    newest = max((v["published"] for v in vids if v["published"]), default=None)
    settled = [v for v in vids if not (newest and v["published"] and (newest - v["published"]).days < 7)]
    ctr = sorted((v for v in vids if v["ctr"] is not None and (v["impressions"] or 0) >= MIN_IMPRESSIONS),
                 key=lambda v: -v["ctr"])
    pct = sorted((v for v in vids if v["avg_pct"] is not None), key=lambda v: -v["avg_pct"])
    days = {}
    for v in vids:
        if v["published"]:
            days.setdefault(v["published"].strftime("%A"), []).append(v["views"])
    weekday = sorted(({"day": d, "videos": len(x), "median_views": int(statistics.median(x))}
                      for d, x in days.items() if len(x) >= MIN_DAY), key=lambda d: -d["median_views"])
    dates = sorted(v["published"] for v in vids if v["published"])
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    rhythm = None
    if len(gaps) >= 3:
        rhythm = {"first": dates[0].strftime("%d %b %Y"), "last": dates[-1].strftime("%d %b %Y"),
                  "median_gap_days": statistics.median(gaps), "longest_gap_days": max(gaps),
                  "per_week": round(len(dates) / max(1, (dates[-1] - dates[0]).days / 7), 1)}

    def brief(v):
        return {"title": v["title"], "views": int(v["views"]), "multiple": v["multiple"],
                "ctr": v["ctr"], "avg_pct": v["avg_pct"],
                "published": v["published"].strftime("%d %b %Y") if v["published"] else None}

    return {"videos": len(vids), "median_views": int(med), "total_views": int(sum(v["views"] for v in vids)),
            "top": [brief(v) for v in by_views[:5]],
            "bottom": [brief(v) for v in sorted(settled, key=lambda v: v["views"])[:5]],
            "best_ctr": [brief(v) for v in ctr[:3]], "best_avg_pct": [brief(v) for v in pct[:3]],
            "weekday": weekday, "rhythm": rhythm}


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    kind = None
    if "--kind" in a:
        i = a.index("--kind")
        kind = a[i + 1]
        del a[i:i + 2]
    if not a or not os.path.exists(a[0]):
        print(__doc__)
        sys.exit(2)
    vids, found = load(a[0])
    report = {}
    for k in ("shorts", "long", "all"):
        group = [v for v in vids if v["kind"] == k]
        if group and (not kind or kind == k):
            report[k] = section(group)
    if as_json:
        emit({"columns_found": found, "sections": report})
        return
    print(f"\n  {a[0]}  {len(vids)} videos   columns found: {', '.join(found)}")
    names = {"shorts": "SHORTS", "long": "LONG VIDEOS", "all": "VIDEOS (no duration column)"}
    for k, s in report.items():
        print(f"\n  == {names[k]}: {s['videos']} videos, median {s['median_views']:,} views, "
              f"total {s['total_views']:,}")
        print("  top five")
        for v in s["top"]:
            print(f"    {v['multiple']:6.1f}x  {v['views']:>10,}  {v['title'][:70]}")
        print("  bottom five (newest week left out)")
        for v in s["bottom"]:
            print(f"    {v['multiple']:6.2f}x  {v['views']:>10,}  {v['title'][:70]}")
        if s["best_ctr"]:
            print(f"  best click-through ({MIN_IMPRESSIONS}+ impressions)")
            for v in s["best_ctr"]:
                print(f"    {v['ctr']:5.1f}%  {v['title'][:70]}")
        if s["best_avg_pct"]:
            print("  best average % viewed")
            for v in s["best_avg_pct"]:
                print(f"    {v['avg_pct']:5.1f}%  {v['title'][:70]}")
        if s["weekday"]:
            print(f"  median views by publish day (days with {MIN_DAY}+ videos)")
            for d in s["weekday"]:
                print(f"    {d['day']:<10} {d['median_views']:>9,}  ({d['videos']} videos)")
        if s["rhythm"]:
            r = s["rhythm"]
            print(f"  rhythm {r['first']} -> {r['last']}: {r['per_week']} a week, usual gap "
                  f"{r['median_gap_days']} days, longest gap {r['longest_gap_days']} days")
    print()


if __name__ == "__main__":
    main()
