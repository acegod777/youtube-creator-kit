"""Tests for youtube-creator-kit. Run from the repo folder:  python3 tests/test_tools.py  (Windows: python)
Builds its own sample files in a temp folder; never goes online (yt-dlp collecting is not tested)."""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "youtube-creator-kit", "scripts")
sys.path.insert(0, SCRIPTS)
import ytcommon, metalint, retention, outliers, chapters, studio_report  # noqa: E402

TMP = tempfile.mkdtemp(prefix="ytagent_test_")


def write(name, text, enc="utf-8"):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding=enc, newline="") as fh:
        fh.write(text)
    return p


def run(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True,
                       text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout + p.stderr


def levels(v):
    return [(l, f) for l, f, _ in metalint.check(metalint.normalise(v))]


class Common(unittest.TestCase):
    def test_hindi_words_stay_whole(self):
        self.assertEqual(ytcommon.words("नारायण नारायण भजन"), ["नारायण", "नारायण", "भजन"])

    def test_visual_len_counts_hindi_letters_not_marks(self):
        s = "नारायण"
        self.assertLess(ytcommon.visual_len(s), len(s))

    def test_times(self):
        self.assertEqual(ytcommon.parse_time("1:02:03,5"), 3723.5)
        self.assertEqual(ytcommon.fmt_time(3723), "1:02:03")

    def test_reads_utf16_and_bom(self):
        self.assertEqual(ytcommon.read_text(write("u16.txt", "नमस्ते", "utf-16")), "नमस्ते")
        self.assertEqual(ytcommon.read_text(write("bom.txt", "hi", "utf-8-sig")), "hi")


class Metalint(unittest.TestCase):
    def test_hard_limits_are_errors(self):
        self.assertIn(("ERROR", "title"), levels({"title": "x" * 101}))
        self.assertIn(("ERROR", "title"), levels({"title": "a <b> title"}))
        tags = ", ".join(f"tag number {i}" for i in range(60))
        self.assertIn(("ERROR", "tags"), levels({"title": "t", "tags": tags}))

    def test_sixteen_hashtags_kill_all(self):
        v = {"title": "Song #one", "description": " ".join(f"#h{i}" for i in range(15))}
        self.assertIn(("ERROR", "hashtags"), levels(v))
        v = {"title": "Song", "description": " ".join(f"#h{i}" for i in range(15))}
        self.assertNotIn(("ERROR", "hashtags"), levels(v))

    def test_bad_hashtag_field(self):
        self.assertIn(("ERROR", "hashtags"), levels({"title": "t", "hashtags": ["#good", "#bad-one"]}))
        self.assertNotIn(("ERROR", "hashtags"), levels({"title": "t", "hashtags": "#नमस्ते, #raga"}))

    def test_hindi_description_counts_bytes(self):
        d = "नारायण " * 300   # ~2100 characters, ~6300 bytes
        self.assertLess(len(d), 5000)
        self.assertIn(("ERROR", "description"), levels({"title": "t", "description": d}))

    def test_thumbnail_repeating_title(self):
        self.assertIn(("WARN", "thumb"), levels({"title": "Morning Raga live", "thumb": "RAGA"}))
        self.assertNotIn(("WARN", "thumb"), levels({"title": "Morning Raga live", "thumb": "OM"}))

    def test_clean_title_has_no_errors(self):
        self.assertEqual([l for l, _ in levels({"title": "Morning Raga | Example Artist"}) if l != "TIP"], [])

    def test_batch_duplicates_and_against(self):
        rows = [{"title": "Morning Raga Shorts part 1", "description": "Same words here #x", "hashtags": "#a #b"},
                {"title": "Morning Raga Shorts part 2", "description": "Same words here #y", "hashtags": "#b #a"},
                {"title": "Flute by the river", "description": "Different", "hashtags": "#c"}]
        p = write("batch.json", json.dumps({"videos": rows}, ensure_ascii=False))
        prev = write("prev.txt", "Flute by the River\n")
        code, out = run("metalint.py", p, "--against", prev, "--json")
        res = json.loads(out)["videos"]
        dup = lambda i: {(x["field"]) for x in res[i]["problems"] if x["level"] == "DUP"}
        self.assertEqual(code, 0)
        self.assertEqual(dup(1), {"title", "description", "hashtags"})
        self.assertEqual(dup(2), {"title"})
        self.assertEqual(dup(0), set())

    def test_csv_and_exit_code(self):
        p = write("b.csv", "Title,Tags\n" + "x" * 120 + ",a\nfine title,b\n")
        code, out = run("metalint.py", p)
        self.assertEqual(code, 1)
        self.assertIn("1 ERROR", out)

    def test_cli_prints_hindi(self):
        code, out = run("metalint.py", "--title", "नमस्ते दुनिया | Example Artist")
        self.assertEqual(code, 0)
        self.assertIn("नमस्ते", out)


def retention_csv(name, pts, head="Video position (%),Absolute audience retention (%)"):
    return write(name, head + "\n" + "\n".join(f"{x},{y}" for x, y in pts))


class Retention(unittest.TestCase):
    def test_finds_cliff_and_times_it(self):
        pts = [(x, 100 - x * 0.2 - (15 if x >= 50 else 0) - (20 if x < 5 and x > 0 else 0) * 0)
               for x in range(0, 101, 2)]
        p = retention_csv("r1.csv", pts)
        rows, timed = retention.load(p)
        r = retention.analyse(rows, timed, duration=200)
        self.assertEqual(r["unit"], "s")
        self.assertEqual(r["drops"][0]["label"], "1:36")      # 48 % of 200 s
        self.assertAlmostEqual(r["drops"][0]["change"], -15.4, places=1)

    def test_percent_axis_without_duration(self):
        pts = [(x, 100 - x * 0.5) for x in range(0, 101, 5)]
        rows, timed = retention.load(retention_csv("r2.csv", pts))
        r = retention.analyse(rows, timed)
        self.assertEqual(r["unit"], "%")
        self.assertEqual(r["drops"], [])

    def test_shorts_ratio_looping_and_time_strings(self):
        pts = [(f"0:{s:02d}", round(1.3 - s * 0.01, 3)) for s in range(0, 40, 2)]
        p = retention_csv("r3.csv", pts, "Moment,Audience watch ratio")
        rows, timed = retention.load(p)
        self.assertTrue(timed)
        r = retention.analyse(rows, timed, shorts=True)
        self.assertEqual(r["start"], 130.0)
        self.assertEqual(r["opening_window"], 3.0)

    def test_rewatch_bump_and_transcript(self):
        pts = [(s, 80 - s * 0.05 + (6 if 120 <= s < 130 else 0)) for s in range(0, 300, 5)]
        p = retention_csv("r4.csv", pts, "Time (seconds),Audience retention")
        srt = write("r4.srt", "1\n00:01:55,000 --> 00:02:05,000\nthe big reveal\n\n2\n00:04:00,000 --> 00:04:10,000\nend\n")
        code, out = run("retention.py", p, "--transcript", srt)
        self.assertEqual(code, 0)
        self.assertIn("REWATCH", out)
        self.assertIn("the big reveal", out)

    def test_headerless(self):
        p = write("r5.csv", "\n".join(f"{x},{100 - x / 3}" for x in range(0, 101, 4)))
        rows, timed = retention.load(p)
        self.assertEqual(len(rows), 26)


class Outliers(unittest.TestCase):
    def rows(self):
        rows = [{"channel": "A", "title": f"Lofi beats {i}", "views": 1000, "url": f"u{i}", "duration": 600}
                for i in range(6)]
        rows.append({"channel": "A", "title": "Rain lofi 8 HOURS?", "views": 9000, "url": "x", "duration": 600})
        rows += [{"channel": "A", "title": f"short {i}", "views": 50000, "url": f"https://youtube.com/shorts/{i}",
                  "duration": 30} for i in range(5)]
        rows += [{"channel": "B", "title": "b", "views": 99, "url": "b", "duration": 300}] * 3
        return rows

    def test_shorts_ranked_apart_and_thin_channels_skipped(self):
        out, skipped, shared, n = outliers.rank(outliers.load(write("o.json", json.dumps(self.rows()))), 2)
        self.assertEqual([o["title"] for o in out], ["Rain lofi 8 HOURS?"])
        self.assertEqual(out[0]["multiple"], 9.0)
        self.assertEqual(skipped, [{"channel": "B", "kind": "long", "videos": 3}])
        self.assertEqual(n, 12)

    def test_reads_raw_ytdlp(self):
        d = {"channel": "Chan", "entries": [{"id": f"v{i}", "title": "t", "view_count": 10 * (i + 1),
                                             "duration": 400} for i in range(5)]}
        rows = outliers.load(write("y.json", json.dumps(d)))
        self.assertEqual(rows[0]["channel"], "Chan")
        self.assertEqual(rows[0]["url"], "https://www.youtube.com/watch?v=v0")
        self.assertEqual(rows[0]["kind"], "long")

    def test_shared_features(self):
        rows = [{"channel": "C", "title": f"plain title {i}", "views": 100, "url": str(i), "duration": 500}
                for i in range(10)]
        rows += [{"channel": "C", "title": f"Top {i} songs?", "views": 1000, "url": f"h{i}", "duration": 500}
                 for i in range(4)]
        out, _, shared, _ = outliers.rank(rows, 2)
        feats = {s["feature"] for s in shared}
        self.assertIn("a question", feats)


class Chapters(unittest.TestCase):
    def test_tracks_as_lengths(self):
        p = write("t.txt", "01. Rain on glass 3:00\nNight bus | 2:30\n4:05 Last light\n")
        ch, total = chapters.from_tracks(p)
        self.assertEqual(ch, [(0.0, "Rain on glass"), (180.0, "Night bus"), (330.0, "Last light")])
        self.assertEqual(total, 575.0)
        self.assertEqual(chapters.validate(ch, total), [])

    def test_tracks_as_starts(self):
        ch, total = chapters.from_tracks(write("s.txt", "0:00 Intro\n1:10 Verse\n1:00:05 Outro\n"))
        self.assertEqual([c[0] for c in ch], [0.0, 70.0, 3605.0])
        self.assertIsNone(total)

    def test_validation_rules(self):
        self.assertTrue(chapters.validate([(0, "a"), (5, "b")], 100))
        probs = chapters.validate([(5, "a"), (20, "b"), (25, "c")], 100)
        self.assertTrue(any("0:00" in p for p in probs))
        self.assertTrue(any("10s" in p for p in probs))

    def test_check_mode_cli(self):
        p = write("d.txt", "My song\n\n0:00 Intro\n0:45 Chorus\n1:30 End\nmore text\n")
        code, out = run("chapters.py", "--check", p)
        self.assertEqual(code, 0, out)
        self.assertIn("valid: 3 chapters", out)

    def test_transcript_finds_topic_change(self):
        def ts(t):
            return f"00:{t // 60:02d}:{t % 60:02d},000"
        lines, t = [], 0
        for i in range(30):
            text = "the river flows past the village temple." if i < 15 else "the warrior lifts his golden sword."
            lines.append(f"{i + 1}\n{ts(t)} --> {ts(t + 3)}\n{text}\n")
            t += 3 + (4 if i == 14 else 0)
        ch, total = chapters.from_transcript(write("tr.srt", "\n".join(lines)), 3)
        starts = [c[0] for c in ch]
        self.assertIn(49.0, starts)                           # the pause + new topic at line 16
        self.assertTrue(any("River" in c[1] for c in ch))


STUDIO = """Content,Video title,Video publish time,Duration,Views,Impressions,Impressions click-through rate (%),Average percentage viewed (%)
Total,,,,99999,,,
a1,Raga Short 1,"Oct 1, 2026",40,1000,800,5.0,90
a2,Raga Short 2,"Oct 2, 2026",40,1000,300,12.0,95
a3,Raga Short 3,"Oct 8, 2026",40,4000,900,7.5,120
a4,Raga Short 4,"Oct 9, 2026",40,500,700,3.0,70
a5,Raga Short 5,"Oct 15, 2026",40,1500,1000,6.0,99
b1,Full song video,"Sep 1, 2026",245,200,2000,2.0,40
b2,Second song video,"Sep 20, 2026",300,400,1500,4.0,45
"""


class Studio(unittest.TestCase):
    def test_report(self):
        vids, found = studio_report.load(write("Table data.csv", STUDIO))
        self.assertEqual(len(vids), 7)                        # Total row dropped
        self.assertIn("impressions", found)
        shorts = studio_report.section([v for v in vids if v["kind"] == "shorts"])
        self.assertEqual(shorts["median_views"], 1000)
        self.assertEqual(shorts["top"][0]["multiple"], 4.0)
        self.assertEqual(shorts["best_ctr"][0]["title"], "Raga Short 3")  # 12 % one has < 500 impressions
        self.assertNotIn("Raga Short 5", [b["title"] for b in shorts["bottom"]])  # newest week left out
        self.assertEqual(shorts["rhythm"]["longest_gap_days"], 6)

    def test_cli(self):
        code, out = run("studio_report.py", write("Table data2.csv", STUDIO))
        self.assertEqual(code, 0, out)
        self.assertIn("SHORTS: 5 videos", out)
        self.assertIn("LONG VIDEOS: 2 videos", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
