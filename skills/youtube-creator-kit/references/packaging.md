# Packaging: title, thumbnail text, description, hashtags, tags

The title and the thumbnail are one unit seen together in the feed. The thumbnail should add what
the title does not say, never repeat it.

## Write, then check

1. Read the channel profile. Know which channel this is for: music, music video, ASMR, stories, lofi.
2. Write 6-8 title options. Run them all: `python metalint.py titles.txt` (one per line).
3. Show the user the best three, each with any WARN from the tool and one line on why it fits.
4. For the chosen title, write the description, hashtags, tags and a thumbnail brief.
5. Put the full set in a JSON or CSV and run `metalint.py` again. Fix every ERROR and DUP.

## What works, by kind of video

- **Devotional / bhajan / mantra songs.** Lead with the name people search for (the deity, the
  mantra, the bhajan's first words), then the artist: `Om Shanti Mantra 108 Times | Example Artist`.
  Hindi + English in one title is normal here; keep the user's order. Mood words such as calm,
  peaceful or morning help, but say how long when it is long (`1 Hour`, `108 times`).
- **Music video / original song.** Song name first, then artist, then what kind of video it is
  (`Official Video`, `Lyric Video`, `3D`). A fake "SHOCKING" hook on a song breaks trust.
- **ASMR / sleep / lofi long videos.** The search is for the use, not the art: what it is, how
  long, what it is for (`Airplane Cabin Sound 8 Hours for Sleep`). No vague praise words.
- **Stories (myths, anime, drama series).** Name the character or the moment, plus the feeling or
  the turn: who, what happens, why care. For a series keep one fixed pattern
  (`EP03 | ...`), but every title still needs its own words after the pattern.
- **Shorts.** Under 40 visible characters if possible; the title is not seen much in the Shorts
  feed, but it is used for search and on the channel page. `#shorts` is not needed.

## Hard limits (metalint reports these as ERROR)

- Title at most 100 characters. No `<` or `>` in the title, description or tags.
- Description at most 5000 **bytes**. A Hindi letter is 3 bytes, so a Hindi description fills up
  about three times faster.
- More than 15 different hashtags across title + description = YouTube ignores **all** of them.
  The first three hashtags show above the title. 3-5 good ones beat 15.
- Tags at most 500 characters in total (a tag with a space costs 2 more for the quotes). Tags
  matter little; use them for other spellings (Shanti / Shanthi / शांति), names, and the kind
  of video, and stop at about 10-15.

## The description

- The first line is the only one most people see (about 110 characters above "...more"). Say what
  the video is, using the words someone would search for.
- Then the credits the user wants (song, music, lyrics, the AI notice if the channel uses one),
  links if any, and chapters for long videos (`references/chapters.md`).
- No keyword lists. Repeating the same words over and over is against YouTube's rules.

## Batches of Shorts: every one unique

Each Short gets its own title, description, hashtags and tags. A fixed series pattern is fine, but
the words after it must differ. Before showing a batch, run
`python metalint.py batch.json --against published.txt` and fix every DUP. `published.txt` can be
one title per line, or a Studio export CSV.

## The thumbnail brief (when the user makes the thumbnail)

- At most 3-4 words, different from the title. Must be readable at phone size.
- One subject, a face if there is one, strong contrast against the background.
- Say what the background must do (plain or blurred behind the words).

## Hand back

For each video, in this order, each field on its own:

```
Title:
Description:
Hashtags:
Tags:
Thumbnail text:   (and a one-line brief)
```

Then the metalint result line (`0 ERROR, 0 DUP, ...`) and: **use it, or change it?**
