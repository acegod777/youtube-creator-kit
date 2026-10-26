---
name: youtube-creator-kit
description: >-
  YouTube helper for creators - music, ASMR, lofi, stories, tutorials and Shorts. Checks titles,
  descriptions, hashtags and tags against YouTube's real limits and for duplicates; reads Studio
  retention and channel exports; finds outlier videos in a niche; makes chapters from subtitles,
  tracklists or music folders; picks Shorts from long videos; drafts comment replies. Use for
  "title for this video", "check my titles", "write the description", "hashtags", "tags", "are
  these unique", "why do people stop watching", "retention", "how is my channel doing", "what's
  working in my niche", "find viral videos", "chapters", "timestamps", "tracklist", "cut this into
  Shorts", "reply to comments". It writes and checks only - it never uploads, logs in or changes
  anything on YouTube.
---

# youtube-creator-kit

Scripts are in `scripts/` next to this file. Run them with `python3` (on Windows: `python` or `py`).
Every script prints its own help when run with no arguments, and takes `--json`. They use only the
Python standard library.

## Rules that always apply

1. **Nothing gets published by this skill.** No uploads, no logins, no API calls, no edits on
   YouTube. The user uploads with their own tools or by hand.
2. **Never invent a number** - views, CTR, retention, "videos like this get 2x". Numbers come from
   a file the user gave, or they are not said. No fake scores out of 100.
3. **Going online needs a yes first.** Only `outliers.py --collect` does it (public pages through
   yt-dlp). Say which channels and how many videos, then wait.
4. **Check before handing over.** Run `metalint.py` on every title set and every batch, with
   `--against` a list of already-published titles when there is one. Fix every ERROR. Fix every
   DUP too, unless the channel profile says repeats are fine.
5. **Hand metadata over field by field**: Title / Description / Hashtags / Tags / Thumbnail text,
   in the order the channel profile asks for if it sets one. End with: **use it, or change it?**
6. **Keep the user's own spelling** of names and words in any language. Do not translate a title
   unless asked; for two-language titles keep the user's order.
7. **Read the channel profile first**: `~/.claude/youtube/channels.md`. If it is missing, copy
   `channels.template.md` there and ask the user to fill in the gaps - do not guess them.

## What to do for each job

| The user wants | Read | Script |
|---|---|---|
| titles, descriptions, hashtags, tags, thumbnail text, "are these unique" | `references/packaging.md` | `metalint.py` |
| why people stop watching, retention | `references/retention.md` | `retention.py` |
| how the channel is doing, what to fix first | `references/checkup.md` | `studio_report.py` |
| what is working in a niche, viral videos, competitors | `references/research.md` | `outliers.py` |
| chapters, timestamps, tracklist for a mix | `references/chapters.md` | `chapters.py` |
| Shorts out of a long video or song | `references/shorts.md` | `chapters.py` (transcript), `metalint.py` |
| replies to comments | `references/comments.md` | - |

Read only the reference for the job in hand. Each one says what to hand back.

## Getting files from YouTube Studio (the user does this; tell them how)

- Retention: Studio -> the video -> Analytics -> Engagement -> retention chart -> download icon.
- Channel export: Studio -> Analytics -> Advanced mode -> Content -> date range -> download -> CSV.
  Unzip; use `Table data.csv`. Add Impressions, CTR and Average percentage viewed columns first.
- Subtitles: Studio -> Subtitles -> download .srt, or any Whisper .srt/.json.
