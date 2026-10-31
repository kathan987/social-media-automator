import unittest

import research


class WatchUrl(unittest.TestCase):
    def test_share_links_become_watch_urls(self):
        want = "https://www.youtube.com/watch?v=7-heUMQhVko"
        for url in ("https://youtube.com/shorts/7-heUMQhVko?si=Xj_Yc7vosI2_vOWp",
                    "https://youtu.be/7-heUMQhVko",
                    "https://www.youtube.com/watch?v=7-heUMQhVko&t=3"):
            self.assertEqual(research.watch_url(url), want)

    def test_rejects_non_video_links(self):
        with self.assertRaises(ValueError):
            research.watch_url("https://heistnotes.com/viral")

    def test_score_reads_youtube_urls_without_upload(self):
        part = research.video_part("https://youtube.com/shorts/7-heUMQhVko")
        self.assertEqual(part.file_data.file_uri, "https://www.youtube.com/watch?v=7-heUMQhVko")


class Viral(unittest.TestCase):
    def test_reads_trending_list_from_page_structured_data(self):
        page = """<script type="application/ld+json">[{"@type": "WebSite"}, {"@type": "ItemList", "itemListElement": [
            {"item": {"name": "GTA 6 WILL COST ECONOMY $1 BILLION", "url": "https://www.youtube.com/watch?v=gT9W5cgqDeA",
             "uploadDate": "2026-10-22T23:01:50.000Z", "author": {"name": "jacobweeby"},
             "interactionStatistic": {"userInteractionCount": 1312349}}}]}]</script>"""
        self.assertEqual(research.viral_list(page), [{"title": "GTA 6 WILL COST ECONOMY $1 BILLION",
            "url": "https://www.youtube.com/watch?v=gT9W5cgqDeA", "channel": "jacobweeby",
            "views": 1312349, "uploaded": "2026-10-22"}])

    def test_layout_change_is_an_error_not_an_empty_list(self):
        with self.assertRaises(ValueError):
            research.viral_list("<html>redesigned</html>")


class Incidents(unittest.TestCase):
    def test_cuts_one_clip_per_incident_skipping_blocked_and_duplicate_moments(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from moviepy.editor import ColorClip
        with tempfile.TemporaryDirectory() as tmp:
            clips, index = Path(tmp), Path(tmp) / "index.md"
            ColorClip((160, 90), (200, 0, 0), duration=20).write_videofile(str(clips / "gta5-x-LONG.mp4"), fps=10, logger=None)
            found = {"game": "GTA 5", "every": 2, "never_use": [{"from": "0:14", "to": "0:16", "what": "pause menu"}],
                     "incidents": [{"start": "0:03", "end": "0:05", "slug": "gta5-car-flips", "ending": "bad"},
                                   {"start": "0:04", "end": "0:06", "slug": "gta5-same-crash"},   # mostly the same moment
                                   {"start": "0:14", "end": "0:15", "slug": "gta5-menu"},         # inside a never-use range
                                   {"start": "0:09", "end": "0:30", "slug": "gta5 Long Chase!"}]}  # clamped to 14 s / clip end
            with patch.object(research, "CLIPS", clips), patch.object(research, "INDEX", index):
                made = research.cut_incidents(clips / "gta5-x-LONG.mp4", found)
            self.assertEqual([m["file"] for m in made], ["clips/gta5-car-flips.mp4", "clips/gta5-long-chase.mp4"])
            self.assertTrue((clips / "clips" / "gta5-long-chase.mp4").exists())
            self.assertIn("### clips/gta5-car-flips.mp4\n- Game: GTA 5\n- From: gta5-x-LONG.mp4 0:02-0:07", index.read_text("utf-8"))


class ClipIndex(unittest.TestCase):
    def test_slug_is_safe_and_never_overwrites(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(research, "CLIPS", Path(tmp)):
            (Path(tmp) / "bf6-tank-ambush.mp4").touch()
            self.assertEqual(research.clip_slug("BF6 Tank Ambush!", ".mp4").name, "bf6-tank-ambush-2.mp4")
            self.assertEqual(research.clip_slug("../../etc", ".mp4").name, "etc.mp4")
            self.assertEqual(research.clip_slug("", ".mp4").name, "clip.mp4")

    def test_entry_matches_dashboard_heading_and_flags_never_use(self):
        entry = research.clip_entry("bf6-x.mp4", 451, True, {"game": "Battlefield 6",
            "never_use": [{"from": "6:35", "to": "7:16", "what": "desktop"}]}, 24)
        self.assertTrue(entry.startswith("### bf6-x.mp4\n"))
        self.assertIn("**NEVER USE 6:35-7:16 desktop.**", entry)
        self.assertIn("- Length: 7:31", entry)


if __name__ == "__main__":
    unittest.main()
