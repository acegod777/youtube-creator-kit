# Retention: where people stop watching

```
python retention.py retention.csv --duration 3:25 --transcript video.srt
python retention.py retention.csv --duration 0:45 --shorts
```

Always give `--duration` when the export uses percent positions, or the times come out as percent.
`--transcript` (a Whisper or Studio .srt, or a lyrics .srt) prints what was playing at each drop,
which is what makes the report useful.

## Reading it

- **OPENING.** Long videos: under 25 % lost in the first 30 s is healthy; over 40 % is the first
  thing to fix, and it is always the opening seconds, not the middle. For a music video that means
  a long silent intro, a logo, or a slow fade-in before anything happens.
- **DROPS.** A single moment people left. Look at what was on screen and being said: a scene that
  goes nowhere, a long instrumental gap in a story, an intro card, the same shot held too long.
- **REWATCH.** People went back. This is the best moment in the video: use it for the thumbnail,
  for a Short, or move it earlier.
- **MIDDLE.** A steady slide is pace, not one bad moment. The fix is cutting, not rewriting.
- **ENDING.** A big loss in the last 20 % is normal for an end card. If the video has a long
  outro, it can be shortened.
- **Shorts.** The export starts after the swipe, so the real hook rate is Studio's
  "Viewed vs swiped away". Over 100 % means people watched it more than once, which is good.

## Hand back

The single biggest problem, the time it happens, what was playing, and one change for it.
Then any REWATCH moment as a gift: "this is your Short / thumbnail". Only list the rest if asked.
If the opening is healthy and there are no drops, say the video holds people and the problem is
getting the click: go to packaging.
