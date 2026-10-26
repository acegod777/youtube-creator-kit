# Research: what is working in a niche

Two steps. Step 1 goes online, so **ask first**: say which channels and how many videos each.

```
python outliers.py --collect @ChannelOne @ChannelTwo https://www.youtube.com/@Three --limit 60 --out niche.json
python outliers.py niche.json --min 2
python outliers.py niche.json --kind shorts --min 3
```

`--collect` uses yt-dlp to read public channel lists (title, views, length). No login, no
cookies, no downloads of videos. Save `niche.json` in the project the research is for.

## Picking channels

Choose 5-10 channels the user's viewers also watch, small and big ones mixed. The method ranks
each video against its OWN channel, so a small channel's 5x hit counts as much as a big one's.
Channels with fewer than 5 videos of a kind are skipped.

## Reading it

- The **multiple** is the signal. 2x is interesting, 5x+ is worth studying.
- Look at the top outliers yourself: subject, title wording, length, thumbnail style (the user can
  open the URLs). What do several of them share?
- "What the outliers' titles have" compares simple title features (numbers, questions, Hindi
  script, emoji, length...) between outliers and the rest. A small sample: say "pattern", not "cause".
- View counts in flat lists can be rounded, and very new videos have not finished growing.

## Hand back

The top five with multiples and one line each on what they did. The ONE thing several share.
Then the practical line: which of these the user could make this week with what they have
(their own footage, music, skills and tools) - and which they should not chase.
