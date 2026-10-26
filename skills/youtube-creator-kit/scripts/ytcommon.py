"""Shared helpers for the youtube-agent-skill scripts. Standard library only.

Everything here is UTF-8 first (Hindi titles and subtitles must not crash on Windows) and never
touches the network or writes files unless a script is told to with --out.
"""
import csv, io, json, re, sys, unicodedata

# Windows consoles default to cp1252; Devanagari would raise UnicodeEncodeError on print.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def read_text(path):
    """Read a text file whatever Windows tool wrote it (UTF-8 with or without BOM, UTF-16, ANSI)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def read_csv(path):
    """Rows as lists of stripped strings. Sniffs comma / semicolon / tab."""
    text = read_text(path)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [[c.strip() for c in row] for row in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in row)]


def visual_len(s):
    """Characters as a viewer sees them: Devanagari vowel signs and joiners do not take a slot."""
    return sum(1 for ch in s if unicodedata.category(ch) not in ("Mn", "Mc", "Me", "Cf"))


def parse_time(s):
    """'1:02:03.5', '02:03,250', '75', '75.5s' -> seconds. Raises ValueError."""
    s = str(s).strip().lower().rstrip("s").replace(",", ".")
    parts = s.split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(s)
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def fmt_time(t):
    t = int(round(t))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def load_transcript(path):
    """SRT, VTT or Whisper JSON -> [(start, end, text)]."""
    text = read_text(path)
    if path.lower().endswith(".json"):
        d = json.loads(text)
        segs = d.get("segments", []) if isinstance(d, dict) else d
        return [(float(x["start"]), float(x["end"]), (x.get("text") or "").strip()) for x in segs]
    cues, cur = [], None
    for line in text.splitlines():
        m = re.match(r"\s*(\d[\d:.,]*)\s*-->\s*(\d[\d:.,]*)", line)
        if m:
            cur = [parse_time(m.group(1)), parse_time(m.group(2)), []]
            cues.append(cur)
        elif cur is not None and line.strip() and not line.strip().isdigit() and line.strip() != "WEBVTT":
            cur[2].append(re.sub(r"<[^>]+>", "", line.strip()))
    return [(a, b, " ".join(t)) for a, b, t in cues if t]


def words(s):
    """Lower-case word tokens in any script. Devanagari vowel signs are not \\w in Python, so the
    block is listed explicitly (minus the danda punctuation) or Hindi words split at every matra."""
    return re.findall(r"(?:[^\W_]|[ऀ-ॣ०-ॿ])+(?:'[^\W_]+)?", s.lower())


def is_devanagari(s):
    return any("ऀ" <= ch <= "ॿ" for ch in s)


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
