# Chapters

```
python chapters.py --tracks tracklist.txt               # a mix: one song per line, "3:25 Name" or "Name | 3:25"
python chapters.py --folder ./songs --crossfade 4   # songs in name order, lengths read by ffprobe
python chapters.py --transcript story.srt --target 8    # a spoken video
python chapters.py --check description.txt              # check chapters already written
```

YouTube shows chapters only when: the first is 0:00, there are at least 3, each is at least
10 seconds, and the times go up. The script checks all of these; an INVALID line means fix it.

## Mixes (lofi, DJ sets, albums, 8-hour loops)

- `--folder` must point at the exact files in the exact order used in the video. If the video
  loops a playlist, chapter one pass and say so, or list each pass.
- `--crossfade` is the overlap in seconds between songs, if the mix used one.
- Keep the song names as the user named them; strip only file numbering.
- For an 8-hour loop, a chapter every song is too many: group by hour or by mood if the user wants.

## Spoken videos (stories, talks, lessons)

The script finds the boundaries well (pauses + a change of words). The names it prints are topic
words, a draft. Rewrite each as what that part gives the viewer, 2-5 words, in the user's style.
If a part cannot be named in five words it is probably two parts.

## Hand back

The block ready to paste into the description, starting with `0:00`, then the `valid` line.
