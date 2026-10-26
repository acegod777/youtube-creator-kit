# Shorts out of a long video or a song

A good Short is a moment that works with no video around it. That is a smaller set than "the best
moments".

## Finding the moments

- **Songs and music videos:** the chorus or hook line, the drop, the most striking visual. Start ON
  the line or the beat, not in the build-up before it. If there is a retention export, a REWATCH
  moment (`references/retention.md`) is the first candidate.
- **Stories:** a span of 20-55 s that opens on a complete thought (no "and then he..."), has a turn
  in it, and ends on a line, not a trail-off. Read the .srt; `chapters.py --transcript` helps find
  the natural breaks.
- **ASMR / lofi:** the most distinct sound or the most beautiful shot, 15-30 s, plus on-screen text
  saying what the full video is for.

Show the user the top five as: start - end, the first line or what is on screen, and why it stands
alone. Let them reject ones before writing anything for them.

## For each chosen Short

- **The first 1-2 seconds** must show or say the thing. No logo, no fade-in.
- **On-screen text** for the opening seconds, in different words from the title.
- **A loop:** the last moment should lead back into the first, so it replays smoothly.
- **Vertical framing:** say what a 9:16 crop of the 16:9 frame loses (faces at the edge, text).
  Any 16:9-to-9:16 cropping tool does the rest.
- **Metadata:** each Short its own title, description, hashtags and tags - run `metalint.py` on
  the whole batch (rule 4 in SKILL.md).

## Hand back

A table: number, start - end, the moment, on-screen text, title. Then the metalint line.
