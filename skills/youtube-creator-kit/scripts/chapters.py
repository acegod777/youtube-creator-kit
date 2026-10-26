#!/usr/bin/env python3
"""chapters.py - YouTube chapters that actually show up, from a transcript, a tracklist or a music folder.

    python chapters.py --transcript story.srt --target 8        # spoken videos (stories, talks)
    python chapters.py --tracks tracklist.txt                  # mixes: "3:25 Song name" or "Song | 3:25" per line
    python chapters.py --folder ./songs --crossfade 4   # lofi / DJ sets: song files in play order
    python chapters.py --check description.txt                 # is an existing chapter list valid?
    add --json for machine-readable output

YouTube only turns the list into chapters when ALL of these hold - otherwise it stays plain text:
  first entry 0:00, at least 3 entries, every chapter at least 10 seconds, times in order.
Every output is checked against those rules before it is printed.

--tracks: a line with ONE time is that song's LENGTH unless times only ever go up and the first is
0:00, in which case they are START times (a pasted chapter list). --folder needs ffprobe on PATH
and reads songs in name order. --crossfade subtracts the overlap between songs.
Transcript titles are the topic words of each part - a draft to rewrite, not the final names.
Reads files only; never writes, never goes online.
"""
import json, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytcommon import read_text, parse_time, fmt_time, load_transcript, words, emit  # noqa: E402

MIN_LEN = 10.0
AUDIO = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus")
TIME = re.compile(r"(?<![\d:])(\d{1,2}(?::\d{2}){1,2})(?![\d:])")
STOP = set("""the a an of for to in on and or is are was were be been with this that it as at by from you your
i my we our they them he she his her but so if then than there here what which who how when where why not no
yes do does did just really very like about into over out up down can could will would should have has had get
got make made go going went one two said says say also all its their there's it's that's
है हैं था थी थे और का की के को में से पर ने भी तो यह वह जो एक कि नहीं हो ही""".split())


def validate(chapters, total=None):
    """Problems that stop YouTube showing chapters. chapters = [(start_seconds, title)]."""
    probs = []
    if len(chapters) < 3:
        probs.append(f"only {len(chapters)} chapters - YouTube needs at least 3")
    if chapters and chapters[0][0] != 0:
        probs.append("the first chapter must start at 0:00")
    for i, (t, name) in enumerate(chapters):
        end = chapters[i + 1][0] if i + 1 < len(chapters) else total
        if i + 1 < len(chapters) and chapters[i + 1][0] <= t:
            probs.append(f"{fmt_time(chapters[i + 1][0])} is not after {fmt_time(t)} - times must go up")
        elif end is not None and end - t < MIN_LEN:
            probs.append(f'"{name}" at {fmt_time(t)} is {end - t:.0f}s long - every chapter needs 10s')
        if not name.strip():
            probs.append(f"chapter at {fmt_time(t)} has no name")
    return probs


def from_transcript(path, target):
    cues = load_transcript(path)
    if len(cues) < 6:
        sys.exit("too few subtitle lines to split into chapters")
    total = cues[-1][1]

    def kw(text):
        return {w for w in words(text) if len(w) >= 3 and w not in STOP}

    cand = []
    for i in range(1, len(cues)):
        gap = max(0.0, cues[i][0] - cues[i - 1][1])
        before, after = kw(" ".join(c[2] for c in cues[max(0, i - 10):i])), kw(" ".join(c[2] for c in cues[i:i + 10]))
        shift = 1 - len(before & after) / len(before | after) if before | after else 0
        sentence_end = 1.0 if re.search(r"[.!?।]\s*$", cues[i - 1][2]) else 0.0
        cand.append((gap * 1.5 + shift * 3 + sentence_end, cues[i][0]))
    # spread: never two boundaries closer than a fraction of the even spacing
    spacing = max(MIN_LEN, total / max(target, 1) * 0.5)
    picked = [0.0]
    for _, t in sorted(cand, reverse=True):
        if len(picked) >= target:
            break
        if all(abs(t - p) >= spacing for p in picked) and total - t >= MIN_LEN:
            picked.append(t)
    picked.sort()
    out = []
    for i, t in enumerate(picked):
        end = picked[i + 1] if i + 1 < len(picked) else total
        text = " ".join(c[2] for c in cues if c[0] >= t and c[1] <= end + 0.01)
        counts = {}
        for w in words(text):
            if len(w) >= 3 and w not in STOP:
                counts[w] = counts.get(w, 0) + 1
        top = sorted(counts, key=lambda w: -counts[w])[:3]
        out.append((round(t, 2), " ".join(w.capitalize() for w in top) or "Part"))
    return out, total


def from_tracks(path):
    entries = []
    for line in read_text(path).splitlines():
        m = TIME.search(line)
        if not m:
            continue
        name = (line[:m.start()] + line[m.end():]).strip(" \t-|–—.:")
        name = re.sub(r"^\d+[.)]\s+", "", name)  # "01. Song" numbering
        entries.append((parse_time(m.group(1)), name or "Track"))
    if not entries:
        sys.exit("no times found - write one song per line like '3:25 Song name'")
    starts = [e[0] for e in entries]
    if starts[0] == 0 and all(b > a for a, b in zip(starts, starts[1:])):
        return entries, None
    out, t = [], 0.0
    for length, name in entries:
        out.append((t, name))
        t += length
    return out, t


def from_folder(folder, crossfade):
    probe = shutil.which("ffprobe")
    if not probe:
        sys.exit("ffprobe is not on PATH")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(AUDIO))
    if not files:
        sys.exit("no audio files in that folder")
    out, t = [], 0.0
    for i, f in enumerate(files):
        p = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "json",
                            os.path.join(folder, f)], capture_output=True, text=True, encoding="utf-8")
        dur = float(json.loads(p.stdout)["format"]["duration"])
        name = re.sub(r"^\d+[\s._-]+", "", os.path.splitext(f)[0]).replace("_", " ").strip()
        out.append((t, name))
        t += dur - (crossfade if i + 1 < len(files) else 0)
    return out, t


def from_check(path):
    out = []
    for line in read_text(path).splitlines():
        m = TIME.match(line.strip())
        if m:
            out.append((parse_time(m.group(1)), line.strip()[m.end():].strip(" -–—|:")))
    return out, None


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

    tr, tracks, folder, check = opt("--transcript"), opt("--tracks"), opt("--folder"), opt("--check")
    target, cross = int(opt("--target", "7")), float(opt("--crossfade", "0"))
    if tr:
        chapters, total = from_transcript(tr, target)
        mode = "transcript"
    elif tracks:
        chapters, total = from_tracks(tracks)
        mode = "tracks"
    elif folder:
        chapters, total = from_folder(folder, cross)
        mode = "folder"
    elif check:
        chapters, total = from_check(check)
        mode = "check"
    else:
        print(__doc__)
        sys.exit(2)
    probs = validate(chapters, total)
    if as_json:
        emit({"mode": mode, "valid": not probs, "problems": probs, "total": total,
              "chapters": [{"start": t, "label": fmt_time(t), "title": n} for t, n in chapters]})
        sys.exit(1 if probs else 0)
    print()
    for t, n in chapters:
        print(f"{fmt_time(t)} {n}")
    print()
    if total:
        print(f"  total running time {fmt_time(total)}")
    for p in probs:
        print(f"  INVALID  {p}")
    if not probs:
        print(f"  valid: {len(chapters)} chapters")
    if mode == "transcript":
        print("  The names are topic words - rewrite each as what that part gives the viewer.")
    print()
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
