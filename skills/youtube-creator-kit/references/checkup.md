# Channel check-up

```
python studio_report.py "Table data.csv"
python studio_report.py "Table data.csv" --kind shorts
```

The user downloads the file (see SKILL.md). Use a date range of at least 90 days. Shorts and long
videos are reported separately, because they live in different feeds and their numbers do not mix.

## Reading it

- **Top and bottom five as multiples of the median.** What do the top ones share that the bottom
  ones do not: subject, title shape, length, Hindi vs English, day? Say a pattern only when it holds
  for most of them, and call it a pattern, not a cause.
- **Best click-through.** Only videos with 500+ impressions count; small numbers are noise.
  A high CTR with low views means the idea gets clicked but is not shown much: more like it.
- **Best average % viewed.** The videos that hold people. If they also have low CTR, the
  packaging is the problem, not the video.
- **Publish days.** Only days with 3+ videos are shown. A difference smaller than about 1.5x is
  not a real difference with this few videos; say so.
- **Rhythm.** Long gaps then bursts usually hurt more than a slower steady pace.

## Hand back

1. The ONE biggest fix, with what to do this week.
2. Three things that are working, specific enough not to break by accident.
3. One thing NOT to do yet, and why.

Never a list of twenty problems. Never a number the file did not contain.
