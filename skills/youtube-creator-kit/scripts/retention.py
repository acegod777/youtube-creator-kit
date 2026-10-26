#!/usr/bin/env python3
"""retention.py - read a YouTube Studio audience-retention export and find where people leave.

    python retention.py retention.csv --duration 3:25
    python retention.py retention.csv --duration 58 --shorts
    python retention.py retention.csv --transcript video.srt      # says what was playing at each drop
    python retention.py retention.csv --json

Get the file: Studio -> the video -> Analytics -> Engagement -> audience retention chart ->
download icon. Any two-column export works: a position (time like 0:15, seconds, percent, or a 0-1
ratio) and the share still watching (percent or a ratio). Column names are matched loosely.

Reports five things, because they need different fixes:
  OPENING    lost in the first 30 s (first 3 s for --shorts, where swiping away happens)
  DROPS      the steepest single moments people left at
  REWATCH    bumps where the line goes UP - people went back to see something again
  MIDDLE     the steady loss per minute between the opening and the last 20 %
  ENDING     what the last 20 % lost - a big number here is the end screen or a slow fade-out
For Shorts, values above 100 % mean people watched more than once (looping) - that is good.
Reads files only; never writes, never goes online.
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytcommon import read_csv, parse_time, fmt_time, load_transcript, emit  # noqa: E402

X_NAMES = ("position", "time", "elapsed", "moment", "progress")
Y_NAMES = ("absolute", "retention", "watching", "audience", "ratio")


def number(cell):
    c = cell.replace("%", "").replace(",", ".").strip()
    if ":" in c:
        return parse_time(c), True
    return float(c), False


def load(path):
    rows = read_csv(path)
    head = [h.lower() for h in rows[0]]
    has_head = not all(re.fullmatch(r"[\d.,:%\s-]*", h) for h in head)
    xi = yi = None
    if has_head:
        xi = next((i for i, h in enumerate(head) if any(n in h for n in X_NAMES)), None)
        yi = next((i for i, h in enumerate(head) if i != xi and "relative" not in h
                   and any(n in h for n in Y_NAMES)), None)
        rows = rows[1:]
    pts, timed = [], False
    for r in rows:
        nums = []
        for i, c in enumerate(r):
            try:
                nums.append((i,) + number(c))
            except ValueError:
                pass
        if len(nums) < 2:
            continue
        by = {i: (v, t) for i, v, t in nums}
        if xi in by and yi in by:
            x, y = by[xi], by[yi]
        else:                               # no usable headers: first two numeric columns
            x, y = nums[0][1:], nums[1][1:]
        pts.append((x[0], y[0]))
        timed = timed or x[1]
    pts.sort()
    # plain numbers are seconds when the header says so, or when they run past 100 (not a percent)
    if has_head and xi is not None and "sec" in head[xi]:
        timed = True
    if pts and pts[-1][0] > 100.5:
        timed = True
    return pts, timed


def analyse(pts, timed, duration=None, shorts=False, cues=None):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if max(ys) <= 3:                      # ratios (1.0 = 100 %), Shorts loops can pass 1.0
        ys = [y * 100 for y in ys]
    if timed:
        secs = xs
        duration = duration or xs[-1]
    else:
        frac = [x / 100 if max(xs) > 1.0001 else x for x in xs]
        if not duration and cues:
            duration = cues[-1][1]
        secs = [f * duration for f in frac] if duration else None
    # positions in seconds when we can, else in percent of the video
    pos = secs if secs else [x if max(xs) > 1.0001 else x * 100 for x in xs]
    unit = "s" if secs else "%"
    start = ys[0]
    open_end = (3.0 if shorts else 30.0) if secs else (5.0 if shorts else 10.0)
    opening = start - min((y for p, y in zip(pos, ys) if p <= open_end), default=start)
    total = pos[-1] - pos[0] or 1

    steps = []
    for i in range(1, len(ys)):
        span = (pos[i] - pos[i - 1]) or 1e-9
        steps.append({"at": pos[i - 1], "to": pos[i], "change": ys[i] - ys[i - 1], "rate": (ys[i] - ys[i - 1]) / span})

    def pick(cands, key, limit, gap):
        chosen = []
        for s in sorted(cands, key=key):
            if all(abs(s["at"] - c["at"]) >= gap for c in chosen):
                chosen.append(s)
            if len(chosen) == limit:
                break
        return sorted(chosen, key=lambda s: s["at"])

    gap = total * 0.04
    after_open = [s for s in steps if s["at"] >= open_end]
    # a DROP is a step at least 3x steeper than the video's usual loss, not just part of the slide
    usual = sorted(s["rate"] for s in after_open)[len(after_open) // 2] if after_open else 0
    steep = 3 * usual if usual < 0 else 0
    drops = pick([s for s in after_open if s["change"] <= -1.0 and s["rate"] < steep], lambda s: s["rate"], 5, gap)
    rewatch = pick([s for s in after_open if s["change"] >= 1.0], lambda s: -s["rate"], 3, gap)

    end_from = pos[0] + total * 0.8
    middle = [s for s in steps if open_end <= s["at"] < end_from]
    mid_loss = -sum(s["change"] for s in middle)
    mid_span = sum(s["to"] - s["at"] for s in middle) or 1
    per = 60 if secs else 10
    middle_rate = mid_loss / mid_span * per
    end_y = next((y for p, y in zip(pos, ys) if p >= end_from), ys[-1])
    ending = end_y - ys[-1]

    def said(t):
        if not cues or unit != "s":
            return None
        near = [c[2] for c in cues if c[0] <= t + 3 and c[1] >= t - 3]
        return " ".join(near)[:160] or None

    def row(s):
        return {"at": round(s["at"], 1), "label": fmt_time(s["at"]) if unit == "s" else f"{s['at']:.0f}%",
                "change": round(s["change"], 1), "said": said(s["at"])}

    return {"points": len(pts), "unit": unit, "duration": duration, "shorts": shorts,
            "start": round(start, 1), "end": round(ys[-1], 1), "peak": round(max(ys), 1),
            "opening_window": open_end, "opening_loss": round(opening, 1),
            "drops": [row(s) for s in drops], "rewatch": [row(s) for s in rewatch],
            "middle_loss_per": f"{'minute' if unit == 's' else '10% of the video'}",
            "middle_loss": round(middle_rate, 2), "ending_loss": round(ending, 1)}


def verdict_opening(r):
    if r["shorts"]:
        return "watch the swipe-away rate in Studio too; this line starts after the swipe"
    o = r["opening_loss"]
    return "healthy" if o < 25 else "leaking" if o < 40 else "severe - fix the first seconds before anything else"


def main():
    a = sys.argv[1:]
    as_json, shorts = "--json" in a, "--shorts" in a
    a = [x for x in a if x not in ("--json", "--shorts")]

    def opt(name):
        if name in a:
            i = a.index(name)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return None

    dur, tr = opt("--duration"), opt("--transcript")
    if not a or not os.path.exists(a[0]):
        print(__doc__)
        sys.exit(2)
    pts, timed = load(a[0])
    if len(pts) < 8:
        print("could not read at least 8 data points from that file - is it the retention export?")
        sys.exit(1)
    cues = load_transcript(tr) if tr and os.path.exists(tr) else None
    r = analyse(pts, timed, parse_time(dur) if dur else None, shorts, cues)
    if as_json:
        emit(r)
        return
    u = r["unit"]
    print(f"\n  {a[0]}  {r['points']} points  {r['start']}% -> {r['end']}%  (peak {r['peak']}%)")
    if u == "%":
        print("  no duration given - positions are % of the video. Add --duration 3:25 for times.")
    w = f"{r['opening_window']:.0f}{u}"
    print(f"\n  OPENING   -{r['opening_loss']}% in the first {w}   [{verdict_opening(r)}]")
    print("  DROPS     the moments people left")
    for d in r["drops"]:
        print(f"    {d['change']:6.1f}%  at {d['label']:>7}" + (f'   "{d["said"]}"' if d["said"] else ""))
    if not r["drops"]:
        print("    no sharp drops - the loss is a steady slide")
    if r["rewatch"]:
        print("  REWATCH   people went back to see these again")
        for d in r["rewatch"]:
            print(f"    +{d['change']:5.1f}%  at {d['label']:>7}" + (f'   "{d["said"]}"' if d["said"] else ""))
    print(f"  MIDDLE    -{r['middle_loss']}% per {r['middle_loss_per']}")
    print(f"  ENDING    -{r['ending_loss']}% in the last 20%")
    if r["shorts"] and r["peak"] > 100:
        print(f"  LOOPING   peaks at {r['peak']}% - people watched it more than once")
    print()


if __name__ == "__main__":
    main()
