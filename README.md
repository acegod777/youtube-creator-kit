# youtube-creator-kit

[![tests](https://github.com/acegod777/youtube-creator-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/acegod777/youtube-creator-kit/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A free YouTube skill for [Claude Code](https://claude.com/claude-code).** It checks your titles,
descriptions, hashtags and tags against YouTube's real limits, reads your YouTube Studio exports,
finds what is working in your niche, makes chapters, and picks Shorts out of long videos.

Made by **acegod777**. Free for everyone to use, change and share (MIT licence).

> **It never uploads anything.** No YouTube login, no API key, no account access. It writes and
> checks; you publish.

---

## What it does

| Ask Claude... | What happens |
|---|---|
| "Give me titles for this video" / "check these titles" | Writes options, then `metalint.py` checks them against YouTube's real limits |
| "Are these 30 Shorts all unique?" | Flags any Shorts whose title, description, hashtags or tags are the same or nearly the same, in the batch or against already-published titles |
| "Why do people stop watching?" | `retention.py` reads the Studio retention export: opening loss, drop moments, **rewatch moments**, middle slide, ending |
| "How is my channel doing?" | `studio_report.py` reads the Studio Advanced-mode export: Shorts and long videos apart, top/bottom vs your median, best CTR, best % viewed, publish days, upload rhythm |
| "What's working in my niche?" | `outliers.py` ranks videos by how far they beat **their own channel's** median, so small channels count too |
| "Make chapters" | `chapters.py` from subtitles, a tracklist, or a **folder of songs** (lofi / DJ mixes), checked against YouTube's chapter rules |
| "Cut this into Shorts" | Picks moments that work on their own, with on-screen text, loop point and crop notes |
| "Reply to these comments" | Sorts them, then drafts short replies in your voice |

### Real limits, not made-up scores

`metalint.py` reports what YouTube actually does:

- Title over **100 characters** → refused
- Description over **5000 bytes** → refused (a Hindi, Arabic or Chinese letter takes 2-4 bytes, so these fill up much faster)
- `<` or `>` anywhere → refused
- More than **15 hashtags** → YouTube ignores **all** of them
- Tags over **500 characters** (a tag with a space costs 2 more) → refused
- Plus warnings: cut off in search (~60) or on phones (~40), too many CAPS, thumbnail text repeating the title

There is no "score out of 100". Nothing can honestly tell you which title will get clicked.

### Works with any language

Visible length is counted the way people see it (vowel signs in Devanagari and similar scripts don't
count as extra characters), and every file is read as UTF-8, so non-English titles and subtitles work.

---

## Install

You need **Claude Code** and **Python 3.9+**. Nothing else to install.
Optional: [yt-dlp](https://github.com/yt-dlp/yt-dlp) for niche research, `ffprobe` (part of
[FFmpeg](https://ffmpeg.org)) for chapters from a music folder.

**Option 1 - as a Claude Code plugin** (inside Claude Code):

```
/plugin marketplace add acegod777/youtube-creator-kit
/plugin install youtube-creator-kit@youtube-creator-kit
```

**Option 2 - installer script** (runs the tests first, then copies the skill):

```bash
git clone https://github.com/acegod777/youtube-creator-kit.git
cd youtube-creator-kit
./install.sh          # macOS / Linux
install.bat           # Windows
```

**Option 3 - by hand:** copy `skills/youtube-creator-kit` into `~/.claude/skills/`.

Then start a new Claude Code session and either just ask ("check my titles") or type
`/youtube-creator-kit`.

### Your channel profile

Copy `skills/youtube-creator-kit/channels.template.md` to `~/.claude/youtube/channels.md` (the
installers do this for you) and fill it in: your name as it appears in titles, title patterns,
fixed description lines, hashtags you always use. It stays on your computer.

---

## Using the scripts on their own

They work without Claude too. Each one prints help when run with no arguments, and takes `--json`.

```bash
cd skills/youtube-creator-kit/scripts

python3 metalint.py --title "Rain on the Window | 8 Hours" --thumb "SLEEP NOW"
python3 metalint.py batch.json --against published.txt     # .json, .csv, or .txt (one title per line)

python3 retention.py retention.csv --duration 3:25 --transcript video.srt
python3 retention.py retention.csv --duration 0:45 --shorts

python3 studio_report.py "Table data.csv"

python3 outliers.py --collect @SomeChannel @AnotherChannel --limit 60 --out niche.json   # goes online
python3 outliers.py niche.json --min 2

python3 chapters.py --tracks tracklist.txt
python3 chapters.py --folder ./songs --crossfade 4
python3 chapters.py --transcript video.srt --target 8
python3 chapters.py --check description.txt
```

Batch files for `metalint.py` use the fields `title`, `description`, `hashtags`, `tags`, `thumb`
(JSON list of objects, or CSV with those column names).

### Getting the files from YouTube Studio

- **Retention:** Studio → the video → Analytics → Engagement → retention chart → download icon.
- **Channel export:** Studio → Analytics → Advanced mode → Content → pick dates → download → CSV.
  Use `Table data.csv` from the zip. Add Impressions, CTR and Average percentage viewed first.
- **Subtitles:** Studio → Subtitles → download `.srt`, or any Whisper `.srt` / `.json`.

---

## Safety

- Standard-library Python only. No packages to install, nothing hidden.
- The scripts only **read** the files you give them and print a report. The one exception:
  `outliers.py --collect` runs yt-dlp to read **public** channel pages and saves the list to the
  `--out` file you name. The skill tells Claude to ask you before running it.
- No YouTube login, no cookies, no API keys, no uploads, no changes to your channel.

## Tests

```bash
python3 tests/test_tools.py
```

They run automatically on Windows, macOS and Linux on every push.

## Licence

MIT - free for everyone, including commercial use. See [LICENSE](LICENSE).
Made by acegod777. Idea inspired by
[youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill); all code here was
written from scratch.
