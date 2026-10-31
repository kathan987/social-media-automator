"""Offline checks: python -B -m unittest discover -s dashboard -v."""
import copy
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import uuid
import unittest
from unittest.mock import patch, MagicMock

import app
import workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / ("workflow-test-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self.cleanup)
        for name in ("projects", "footage", "docs"):
            (self.root / name).mkdir()
        config = json.loads(w.config_file().read_text("utf-8"))
        config["launch_date"] = "2026-11-19"  # the countdown badge is optional; the layered render test checks it
        config["limits_per_video"]["min_seconds"] = 0  # test renders are 1-2 s; the 20 s floor is checked separately
        config.pop("sfx", None)  # test roots have no assets folder; the layered render test adds its own tones
        config.pop("library_check", None)  # checked in test_library_checklist_blocks_gta_renders
        config.pop("logo", None)  # test roots have no assets/official
        config["limits_per_video"]["higgsfield_broll_clips"] = 1  # the live channel allows 0 (owner: no Higgsfield video); tests keep the reservation logic covered
        w.write(self.root / "config.json", config)
        for name, value in (("ROOT", self.root), ("VIDEOS", self.root / "projects"), ("CLIPS", self.root / "footage"), ("DOCS", self.root / "docs")):
            p = patch.object(app, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(w, "ROOT", self.root); p.start(); self.addCleanup(p.stop)
        p = patch.object(app.activity, "ROOT", self.root); p.start(); self.addCleanup(p.stop)
        app.jobs.clear()
        self.client = app.app.test_client()
        self.slug = self.client.post("/api/videos", json={"topic": "Illustrated gaming idea", "type": "gameplay", "game": "GTA 5"}).get_json()["slug"]
        self.path = w.project(self.slug)
        self.plan = {"title": "A gaming illustration", "description": "Concept art", "tags": ["gaming"], "claims": [],
                     "shots": [{"kind": "higgsfield_image", "prompt": "A stylized city, no logos or text", "narration": "Hello world", "seconds": 1, "file": "still.png"}]}
        w.save_plan(self.path, self.plan)

    def cleanup(self):
        assert self.root.parent == Path(__file__).resolve().parent and self.root.name.startswith("workflow-test-")
        shutil.rmtree(self.root)

    def test_http_boundaries_and_empty_project(self):
        self.assertEqual(self.client.get("/api/status").status_code, 200)
        self.assertEqual(self.client.get("/api/status", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/videos", json={}, headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/videos", json=[]).status_code, 400)
        self.assertEqual(self.client.post(f"/api/videos/{self.slug}/approve").status_code, 400)
        self.assertEqual(sum(self.client.get("/api/status").get_json()["done"].values()), 0)

    def test_news_sources_and_higgsfield_limit(self):
        meta = {"type": "news"}
        with self.assertRaises(ValueError): w.validate(self.plan, meta)
        news = copy.deepcopy(self.plan)
        news["claims"] = [{"text": "Verified statement", "sources": ["https://one.example/a", "https://two.example/b"]}]
        with self.assertRaises(ValueError): w.validate(news, meta)
        news["shots"][0]["kind"] = "official_image"
        news.update(mood="good", background={"file": "rdr2-a.mp4", "offset": 0}, ending={"file": "bf6-b.mp4", "offset": 271, "seconds": 3})
        w.validate(news, meta)
        news["claims"][0]["sources"] *= 0
        with self.assertRaises(ValueError): w.validate(news, meta)
        too_many = copy.deepcopy(self.plan)
        too_many["shots"] *= 7
        with self.assertRaises(ValueError): w.validate(too_many, {"type": "gameplay"})

    def test_queue_idempotence_and_job_attachment(self):
        queue = w.higgsfield_requests(self.path)
        self.assertEqual(queue, w.higgsfield_requests(self.path))
        rid = queue["requests"][0]["id"]
        with self.assertRaises(ValueError): w.record_higgsfield(self.path, rid, {"status": "completed"})
        w.record_higgsfield(self.path, rid, {"status": "submitting"})
        w.record_higgsfield(self.path, rid, {"status": "submitted", "job_id": "job-123"})
        (self.path / "assets/still.png").write_bytes(b"image")
        with self.assertRaises(ValueError): w.record_higgsfield(self.path, rid, {"status": "completed", "file": "still.png"})
        item = w.record_higgsfield(self.path, rid, {"status": "completed", "file": "still.png", "watermark_free": True})
        self.assertEqual(item["job_id"], "job-123")
        self.assertEqual(w.read(self.path / "project.json")["shots"][0]["file"], "still.png")

    def test_weekly_broll_reserved_across_projects(self):
        self.plan["shots"][0]["kind"] = "higgsfield_broll"
        w.save_plan(self.path, self.plan)
        w.higgsfield_requests(self.path)
        second = self.client.post("/api/videos", json={"topic": "Another idea", "type": "gameplay", "game": "GTA 5"}).get_json()["slug"]
        w.save_plan(w.project(second), self.plan)
        with self.assertRaises(ValueError): w.higgsfield_requests(w.project(second))
        self.assertEqual(self.client.get("/api/status").get_json()["broll_used"]["GTA 5"], 1)

    def test_path_escape_and_asset_overwrite(self):
        with self.assertRaises(ValueError): w.local_file(self.path / "assets", "../../meta.json")
        with self.assertRaises(ValueError): w.project("..")
        result = self.client.post(f"/api/videos/{self.slug}/assets", data={"file": (io.BytesIO(b"image"), "still.png")})
        self.assertEqual(result.status_code, 200)
        result = self.client.post(f"/api/videos/{self.slug}/assets", data={"file": (io.BytesIO(b"new"), "still.png")})
        self.assertEqual(result.status_code, 400)

    def test_timestamp_word_conversion(self):
        words = w.alignment_words({"characters": list("Hi all"), "character_start_times_seconds": [0, .1, .2, .3, .4, .5], "character_end_times_seconds": [.1, .2, .3, .4, .5, .6]})
        self.assertEqual(words, [{"text": "Hi", "start": 0, "end": .2}, {"text": "all", "start": .3, "end": .6}])
        with self.assertRaises(ValueError): w.alignment_words({"characters": ["x"], "character_start_times_seconds": [], "character_end_times_seconds": []})

    def prepare_render_receipt(self):
        (self.path / "assets/still.png").write_bytes(b"image")
        (self.path / "vo.mp3").write_bytes(b"audio")
        w.write(self.path / "captions.json", {})
        (self.path / "final.mp4").write_bytes(b"render")
        w.write(self.path / "render.json", {"inputs": w.render_inputs(self.path)})
        return w.digest(self.path)

    def test_agents_board_shows_who_is_working(self):
        import time
        app.activity.log("channel", 1, "Firecrawl", "running", "viral search")
        board = self.client.get("/api/activity").get_json()
        self.assertEqual(len(board["pipeline"]), 11)
        self.assertEqual([e["agent"] for e in board["now"]], ["Firecrawl"])
        app.activity.log("channel", 1, "Firecrawl", "done", "6 credits")
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "", "ELEVENLABS_VOICE_ID": ""}):
            self.assertEqual(self.client.post(f"/api/videos/{self.slug}/run/voice", json={}).status_code, 202)
            for _ in range(100):  # the step runs in a worker thread
                if app.jobs[self.slug]["status"] != "running": break
                time.sleep(.05)
        board = self.client.get("/api/activity").get_json()
        self.assertEqual(board["now"], [])
        voice = [e for e in board["latest"] if e["video"] == self.slug]
        self.assertEqual([(e["step"], e["agent"], e["status"]) for e in voice], [(6, "ElevenLabs", "failed")])
        with self.assertRaises(ValueError): app.activity.log("channel", 42, "Gemini", "running")

    def test_library_matches_assets_and_merges_reference_analysis(self):
        lib = self.root / "assets"
        for f in ("sfx/whoosh-1.mp3", "memes/wasted-abc.mp4", "official/new.jpg"):
            (lib / f).parent.mkdir(parents=True, exist_ok=True); (lib / f).write_bytes(b"x")
        (self.root / "docs" / "assets.md").write_text(
            "| File | Kind | What it shows | Tags | Source | Credits | Used in |\n|---|---|---|---|---|---|---|\n"
            "| `sfx/whoosh-1.mp3` (0.6 s) | sfx | Whoosh | whoosh | pixabay | 1 | all |\n"
            "| `memes/<reaction>-<id>.mp4` (28 files) | meme | GIPHY reactions | x | giphy | 8 | both |\n", "utf-8")
        info = {a["file"]: (a["info"] or {}).get("shows") for a in self.client.get("/api/library").get_json()}
        self.assertEqual(info, {"sfx/whoosh-1.mp3": "Whoosh", "memes/wasted-abc.mp4": "GIPHY reactions", "official/new.jpg": None})
        self.assertEqual(self.client.get("/library/sfx/whoosh-1.mp3").data, b"x")
        refs = self.root / "research" / "opus-videos"
        (refs / "media").mkdir(parents=True)
        w.write(refs / "videos.json", [{"slug": "a-1", "prompt": "p"}, {"slug": "b-2", "prompt": "q"}])
        (refs / "media" / "b-2.mp4").write_bytes(b"v")
        (refs / "watched.jsonl").write_text('{"slug":"b-2","wow_factor":9}\n{"slug":"a-1","error":"503"}\nnot json\n', "utf-8")
        out = self.client.get("/api/references").get_json()
        self.assertEqual([(r["slug"], r["video"], (r["analysis"] or {}).get("wow_factor")) for r in out], [("b-2", True, 9), ("a-1", False, None)])
        skills = self.root / "skills"
        for name, head in (("hook-generator", "description: >\n  Six hooks\n  per topic."), ("remotion-render", "description: Render"), ("post-writer", "description: LinkedIn"), ("gemini-carousel", "description: Slides")):
            (skills / name).mkdir(parents=True); (skills / name / "SKILL.md").write_text(f"---\nname: {name}\n{head}\n---\nbody", "utf-8")
        with patch.object(app, "SKILLS", skills):
            got = {s["name"]: (s["description"], s["steps"]) for s in self.client.get("/api/skills").get_json()}
        self.assertEqual(got["hook-generator"], ("Six hooks per topic.", ["3. Script"]))
        self.assertEqual(got["remotion-render"][1], ["5. Motion graphics"])
        self.assertEqual(got["post-writer"][1], [])  # LinkedIn-only: not in the Shorts pipeline
        self.assertEqual(got["gemini-carousel"][1], [])  # the "Gemini" agent is the model, not this skill

    def test_gameplay_index_assets_and_tools(self):
        (self.root / "footage" / "clips").mkdir()
        for f in ("clips/gta5-crash.mp4", "rdr2-ride.mp4"):
            (self.root / "footage" / f).write_bytes(b"v")
        (self.root / "docs" / "footage.md").write_text(
            "## Entries\n\n### clips/gta5-crash.mp4\n- Game: gta5\n- What happens: Car hits a taco truck.\n"
            "- Kind: crash · Mood: funny\n- Ending: bad\n- Used in:\n", "utf-8")
        got = {c["file"]: c for c in self.client.get("/api/clips").get_json()}
        self.assertEqual(got["clips/gta5-crash.mp4"]["info"], {"game": "gta5", "what happens": "Car hits a taco truck.", "kind": "crash", "mood": "funny", "ending": "bad"})
        self.assertFalse(got["rdr2-ride.mp4"]["indexed"])
        self.assertEqual(self.client.get("/clips/clips/gta5-crash.mp4").data, b"v")
        (w.project(self.slug) / "assets" / "a.jpg").write_bytes(b"i")
        self.assertEqual(self.client.get(f"/api/videos/{self.slug}/assets").get_json(), ["a.jpg"])
        self.assertIn("sfx", self.client.get("/api/status").get_json()["options"])
        self.assertEqual(self.client.post("/api/tools/rm", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/tools/stock", json={"query": "", "n": 3}).status_code, 400)
        self.assertEqual(self.client.post("/api/tools/stock", json={"query": "beach", "n": 99}).status_code, 400)

    def test_approval_changes_and_schedule_receipts(self):
        self.prepare_render_receipt()
        self.assertEqual(self.client.post(f"/api/videos/{self.slug}/approve").status_code, 200)
        self.client.put(f"/api/videos/{self.slug}/project", json=self.plan)
        self.assertTrue(w.read(self.path / "meta.json")["approved"])
        self.plan["title"] = "Updated title"
        self.client.put(f"/api/videos/{self.slug}/project", json=self.plan)
        self.assertFalse(w.read(self.path / "meta.json")["approved"])
        self.assertEqual(self.client.post(f"/api/videos/{self.slug}/approve").status_code, 400)

    def test_publish_private_scheduled_and_duplicate_guard(self):
        fingerprint = self.prepare_render_receipt()
        meta = w.read(self.path / "meta.json")
        meta.update(approved=True, approval_digest=fingerprint)
        w.write(self.path / "meta.json", meta)
        when = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat()
        with patch("uploader.youtube.upload_to_youtube", return_value="https://www.youtube.com/watch?v=test") as upload:
            w.publish(self.path, when)
            self.assertEqual(upload.call_args.kwargs, {"privacy": "private", "publish_at": when, "synthetic": True})
            with self.assertRaises(ValueError): w.publish(self.path, when)
            self.assertEqual(upload.call_count, 1)
        self.assertEqual(w.read(self.path / "publish.json")["status"], "scheduled")

    def test_shared_uploader_schedule_payload(self):
        from uploader import youtube
        service = MagicMock()
        service.videos.return_value.insert.return_value.next_chunk.return_value = (None, {"id": "test"})
        with patch.object(youtube, "_get_service", return_value=service), patch.object(youtube, "MediaFileUpload"):
            youtube.upload_to_youtube(self.plan, "final.mp4", privacy="private", publish_at="2030-01-01T00:00:00Z", synthetic=True)
        status = service.videos.return_value.insert.call_args.kwargs["body"]["status"]
        self.assertEqual(status["privacyStatus"], "private")
        self.assertTrue(status["containsSyntheticMedia"])
        self.assertEqual(status["publishAt"], "2030-01-01T00:00:00Z")

    def test_real_vertical_render_with_timed_caption(self):
        import wave
        from PIL import Image
        from moviepy.editor import VideoFileClip
        self.plan["shots"][0]["narration"] = "Hello"
        self.plan["shots"][0]["kind"] = "official_image"
        self.plan["shots"][0]["source_url"] = "https://publisher.example/image"
        w.save_plan(self.path, self.plan)
        Image.new("RGB", (120, 80), (20, 70, 130)).save(self.path / "assets/still.png")
        with wave.open(str(self.path / "vo.mp3"), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 6615)
        w.write(self.path / "captions.json", {"text": "Hello", "words": [{"text": "Hello", "start": 0, "end": .3}]})
        w.render(self.path)
        with VideoFileClip(str(self.path / "final.mp4")) as video:
            self.assertEqual(video.size, [1080, 1920])
            self.assertLess(video.duration, 1)
            self.assertIsNotNone(video.audio)
            frame = video.get_frame(.1)
            self.assertGreater(int(frame[1240:1370].max()), 180)
        self.assertTrue(w.digest(self.path))

    def test_motion_scene_fills_screen_and_holds_last_frame(self):
        import wave
        from moviepy.editor import ColorClip, VideoFileClip
        self.plan["shots"][0] = {"kind": "motion", "narration": "Hello", "seconds": 1, "file": "title.mp4"}
        w.save_plan(self.path, self.plan)
        ColorClip((540, 960), (240, 120, 0), duration=.3).write_videofile(str(self.path / "assets/title.mp4"), fps=10, logger=None)
        with wave.open(str(self.path / "vo.mp3"), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 17640)  # 0.8 s of voice, longer than the 0.3 s animation
        w.write(self.path / "captions.json", {"text": "Hello", "words": [{"text": "Hello", "start": 0, "end": .3}]})
        w.render(self.path)
        with VideoFileClip(str(self.path / "final.mp4")) as video:
            self.assertEqual(video.size, [1080, 1920])
            self.assertAlmostEqual(video.duration, .8, delta=.1)
            held = video.get_frame(.7)  # past the animation's end: still its last frame, edge to edge
            self.assertGreater(int(held[100, 100, 0]), 200)
            self.assertGreater(int(held[1800, 1000, 0]), 200)

    def test_mood_tags_are_spoken_not_captioned(self):
        text = "[excited] Hi [laughs]all"
        words = w.alignment_words({"characters": list(text), "character_start_times_seconds": [i / 10 for i in range(len(text))],
                                   "character_end_times_seconds": [i / 10 + .1 for i in range(len(text))]})
        self.assertEqual([x["text"] for x in words], ["Hi", "all"])
        self.assertEqual(w.spoken(text), "Hi all")

    def test_gta6_projects_need_mood_background_and_ending(self):
        plan = copy.deepcopy(self.plan)
        with self.assertRaises(ValueError): w.validate(plan, {"type": "whatif"})
        plan.update(mood="bad", background={"file": "rdr2-a.mp4", "offset": 0}, ending={"file": "rdr2-b.mp4", "offset": 23, "seconds": 3})
        w.validate(plan, {"type": "whatif"})
        plan["ending"]["seconds"] = 9
        with self.assertRaises(ValueError): w.validate(plan, {"type": "whatif"})
        plan["ending"]["seconds"], plan["mood"] = 3, "sad"
        with self.assertRaises(ValueError): w.validate(plan, {"type": "whatif"})
        plan["mood"], plan["shots"][0]["stamp"] = "bad", "MAYBE"
        with self.assertRaises(ValueError): w.validate(plan, {"type": "whatif"})
        plan["shots"][0]["stamp"], plan["shots"][0]["sfx"] = "", "airhorn"  # sound names come from config.json
        with self.assertRaisesRegex(ValueError, "sfx"): w.validate(plan, {"type": "whatif"})
        config = w.read(self.root / "config.json"); config["sfx"] = {"wasted": "w.mp3"}; w.write(self.root / "config.json", config)
        plan["shots"][0]["sfx"] = "wasted"
        w.validate(plan, {"type": "whatif"})

    def test_library_checklist_blocks_gta_renders(self):
        config = w.read(self.root / "config.json"); config["library_check"] = {"motion": "x", "handdrawn": "y"}; w.write(self.root / "config.json", config)
        plan = copy.deepcopy(self.plan)
        plan.update(mood="good", background={"file": "rdr2-a.mp4", "offset": 0}, ending={"file": "bf6-b.mp4", "offset": 1, "seconds": 3})
        meta = {"type": "whatif", "slug": self.slug}
        w.validate(plan, meta)  # drafts and saves are not blocked, only the render
        with self.assertRaisesRegex(ValueError, "motion, handdrawn"): w.validate(plan, meta, media=True)
        plan["library_used"] = {"motion": "newspaper scene from the prompt library", "handdrawn": "skipped: no mechanic to explain"}
        with self.assertRaises(ValueError) as e: w.validate(plan, meta, media=True)  # passes the checklist, fails later on missing files
        self.assertNotIn("checklist", str(e.exception))

    def test_weekly_reuse_of_clips_memes_and_techniques(self):
        mk = lambda topic, kind: self.client.post("/api/videos", json={"topic": topic, "type": kind, "game": "GTA 5"}).get_json()["slug"]
        base = {"shots": [{"kind": "meme", "file": "doubt-1.mp4"}], "background": [{"file": "clips/a.mp4", "offset": 0}],
                "ending": {"file": "clips/end.mp4", "offset": 0, "seconds": 3}, "technique": "risograph"}
        first, second = mk("One", "news"), mk("Two", "news")
        w.write(w.project(first) / "project.json", base)
        meta = {**w.read(w.project(second) / "meta.json"), "slug": second}
        clash = w.weekly_reuse({**base, "background": [{"file": "clips/b.mp4", "offset": 0}], "ending": {"file": "clips/end2.mp4"}}, meta)
        self.assertEqual(clash, [f"meme doubt-1.mp4 ({first})", f"technique risograph ({first})"])
        fresh = {"shots": [{"kind": "meme", "file": "new.mp4"}], "background": [{"file": "clips/a.mp4", "offset": 0}], "technique": "pixel-art"}
        self.assertEqual(w.weekly_reuse(fresh, meta), [f"clip clips/a.mp4 ({first})"])

    def test_explainer_is_factual_with_its_own_checklist_and_no_gta_only_rules(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["kind"] = "motion"
        meta = {"type": "explainer_a", "slug": self.slug}
        with self.assertRaisesRegex(ValueError, "source-backed"): w.validate(plan, meta)
        plan["claims"] = [{"text": "Fact A", "sources": ["https://a.example/x", "https://b.example/y"]}]
        w.validate(plan, meta)  # no mood, background or ending clip needed
        config = w.read(self.root / "config.json"); config["explainer_check"] = {"stickers": "x", "three_d": "y"}; w.write(self.root / "config.json", config)
        with self.assertRaisesRegex(ValueError, "stickers, three_d"): w.validate(plan, meta, media=True)  # its own checklist, not library_check
        plan["shots"][0]["kind"] = "higgsfield_broll"
        with self.assertRaisesRegex(ValueError, "no Higgsfield video"): w.validate(plan, meta)

    def test_explainers_run_30_to_45_seconds_other_formats_stay_at_30(self):
        self.assertEqual((w.limits_for({"type": "explainer_b"})["min_seconds"], w.limits_for({"type": "explainer_b"})["max_seconds"]), (30, 45))
        self.assertEqual(w.limits_for({"type": "news"})["max_seconds"], 30)
        plan = copy.deepcopy(self.plan)
        plan["claims"] = [{"text": "Fact A", "sources": ["https://a.example/x", "https://b.example/y"]}]
        plan["shots"][0].update(kind="motion", seconds=40, narration="word " * 100)
        w.validate(plan, {"type": "explainer_b", "slug": self.slug})  # 40 s and 100 words fit an explainer
        with self.assertRaisesRegex(ValueError, "fit 30 seconds"): w.validate(plan, {"type": "gameplay", "slug": self.slug})
        plan["shots"][0]["seconds"] = 46
        with self.assertRaisesRegex(ValueError, "fit 45 seconds"): w.validate(plan, {"type": "explainer_b", "slug": self.slug})

    def test_did_you_know_is_factual_like_news(self):
        plan = copy.deepcopy(self.plan)
        plan.update(mood="good", background={"file": "rdr2-a.mp4", "offset": 0}, ending={"file": "bf6-b.mp4", "offset": 1, "seconds": 3})
        with self.assertRaisesRegex(ValueError, "source-backed"): w.validate(plan, {"type": "didyouknow"})
        plan["claims"] = [{"text": "Leonida is based on Florida", "sources": ["https://a.example/x", "https://b.example/y"]}]
        w.validate(plan, {"type": "didyouknow"})  # Higgsfield images are allowed (owner 2026-10-26)
        plan["shots"][0]["stamp"] = "REAL"
        with self.assertRaisesRegex(ValueError, "never carry a REAL"): w.validate(plan, {"type": "didyouknow"})
        plan["shots"][0].update(kind="higgsfield_broll", stamp="")
        with self.assertRaisesRegex(ValueError, "no Higgsfield video"): w.validate(plan, {"type": "didyouknow"})
        plan["shots"][0]["kind"] = "gameplay"
        w.validate(plan, {"type": "didyouknow"})
        plan["shots"][0].update(kind="stock", source_url="https://pixabay.com/videos/id-1/")  # real-world comparison clip
        w.validate(plan, {"type": "didyouknow"})

    def test_split_layout_puts_proof_on_top_and_gameplay_below(self):
        import wave
        from moviepy.editor import ColorClip, VideoFileClip
        for name, colour, seconds in (("rdr2-under.mp4", (0, 0, 200), 3), ("rdr2-end.mp4", (220, 0, 0), 2)):
            ColorClip((320, 180), colour, duration=seconds).write_videofile(str(self.root / "footage" / name), fps=10, logger=None)
        slug = self.client.post("/api/videos", json={"topic": "Split", "type": "news", "game": "GTA 5"}).get_json()["slug"]
        path = w.project(slug)
        plan = {"title": "Split news", "layout": "split", "mood": "good", "publish_date": "2026-10-26",
                "topic_badge": "GTA 6", "caption_words": 1,
                "claims": [{"text": "Verified", "sources": ["https://one.example/a", "https://two.example/b"]}],
                "background": [{"file": "rdr2-under.mp4", "offset": 0}], "ending": {"file": "rdr2-end.mp4", "offset": 0, "seconds": 1},
                "shots": [{"kind": "official_clip", "file": "trailer.mp4", "narration": "Hello", "seconds": 1, "stamp": "REPORTED",
                           "source_url": "https://www.youtube.com/watch?v=x", "arrow": [540, 640], "inset": {"file": "meme.mp4"}},
                          {"kind": "meme", "file": "meme.mp4", "narration": "there", "seconds": 1, "source_url": "https://giphy.com/gifs/x"}]}
        w.save_plan(path, plan)
        ColorClip((640, 360), (240, 120, 0), duration=.2).write_videofile(str(path / "assets/trailer.mp4"), fps=10, logger=None)
        ColorClip((120, 120), (220, 0, 220), duration=.5).write_videofile(str(path / "assets/meme.mp4"), fps=10, logger=None)
        with wave.open(str(path / "vo.mp3"), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 22050)
        w.write(path / "captions.json", {"text": "Hello there", "words": [{"text": "Hello", "start": 0, "end": .4}, {"text": "there", "start": .5, "end": .8}]})
        w.render(path)
        with VideoFileClip(str(path / "final.mp4")) as video:
            f = video.get_frame(.35)                           # past the 0.2 s trailer clip: it holds its last frame
            self.assertGreater(int(f[300, 540, 0]), 200)       # orange proof fills the top...
            self.assertGreater(int(f[1700, 540, 2]), 150)      # ...blue gameplay runs below (owner rule 2)
            self.assertLess(int(f[1700, 540, 0]), 60)
            stamp = f[w.TOP_H - 110, 56]                       # amber REPORTED stamp (its padding, left of the lettering)
            self.assertGreater(int(stamp[0]), 200)
            self.assertTrue(120 < int(stamp[1]) < 200)
            self.assertGreater(int(f[1240:1370].max()), 180)   # caption on the seam
            pip = f[w.TOP_H - 40 - 169, 1080 - 36 - 300]       # centre of the picture-in-picture: the magenta proof clip
            self.assertGreater(int(pip[0]), 150) and self.assertLess(int(pip[1]), 80)
            self.assertLess(int(pip[1]), 80)
            self.assertGreater(int(f[480, 540, 1]), 180)       # green arrow shaft above the point it marks
            self.assertLess(int(f[480, 540, 0]), 120)
            self.assertGreater(int(f[70, 400:680, 0].max()), 200)  # pink GTA 6 topic badge, top centre
            meme = video.get_frame(.75)
            self.assertGreater(int(meme[590, 540, 0]), 150)    # meme shown whole, centred on its blurred copy
            self.assertLess(int(meme[590, 540, 1]), 80)
        plan["shots"][0].update(kind="ai_clip", stamp="REAL")
        with self.assertRaisesRegex(ValueError, "never carry a REAL"): w.validate(plan, {"type": "news"})

    def test_silent_pov_beat_after_the_voice(self):
        import wave
        from PIL import Image
        from moviepy.editor import ColorClip, VideoFileClip
        for name, colour, seconds in (("gta5-under.mp4", (0, 0, 200), 3), ("gta5-end.mp4", (220, 0, 0), 2)):
            ColorClip((320, 180), colour, duration=seconds).write_videofile(str(self.root / "footage" / name), fps=10, logger=None)
        slug = self.client.post("/api/videos", json={"topic": "POV", "type": "news", "game": "GTA 5"}).get_json()["slug"]
        path = w.project(slug)
        meta = {**w.read(path / "meta.json"), "slug": slug}
        pov = {"kind": "meme", "silent": True, "seconds": 1, "text": "POV: me", "file": "meme.mp4", "source_url": "https://giphy.com/gifs/x"}
        plan = {"title": "POV beat", "claims": [{"text": "Verified", "sources": ["https://one.example/a", "https://two.example/b"]}],
                "mood": "bad", "background": [{"file": "gta5-under.mp4", "offset": 0}],
                "ending": {"file": "gta5-end.mp4", "offset": 0, "seconds": 1},
                "shots": [{"kind": "official_image", "narration": "[excited] Hello there", "seconds": 1, "file": "card.png",
                           "source_url": "https://www.rockstargames.com/newswire"}, pov]}
        self.assertEqual(w.voice_text(plan), "[excited] Hello there")  # the POV beat is never read aloud
        with self.assertRaisesRegex(ValueError, "after every spoken shot"):
            w.validate({**plan, "shots": [pov, plan["shots"][0]]}, meta)
        with self.assertRaisesRegex(ValueError, "1-5 seconds"):
            w.validate({**plan, "shots": [plan["shots"][0], {**pov, "seconds": 9}]}, meta)
        w.save_plan(path, plan)
        Image.new("RGB", (160, 90), (0, 200, 0)).save(path / "assets/card.png")
        ColorClip((120, 120), (220, 0, 220), duration=.5).write_videofile(str(path / "assets/meme.mp4"), fps=10, logger=None)
        with wave.open(str(path / "vo.mp3"), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 22050)
        w.write(path / "captions.json", {"text": "Hello there", "words": [{"text": "Hello", "start": 0, "end": .4}, {"text": "there", "start": .4, "end": .8}]})
        w.render(path)
        with VideoFileClip(str(path / "final.mp4")) as video:
            self.assertAlmostEqual(video.duration, 3, delta=.15)     # 1 s voice + 1 s silent POV beat + 1 s ending
            beat = video.get_frame(1.5)
            self.assertGreater(int(beat[700, 540, 0]), 150)          # the meme card plays after the voice...
            self.assertGreater(int(beat[1240:1370].max()), 200)      # ...with the POV line where captions sit
            self.assertGreater(int(video.get_frame(2.5)[960, 540, 0]), 150)  # then the red ending clip

    def test_layered_render_gameplay_under_card_then_mood_ending(self):
        import wave
        from PIL import Image
        from moviepy.editor import ColorClip, VideoFileClip
        for name, colour, seconds in (("rdr2-background.mp4", (0, 0, 200), 3), ("rdr2-second.mp4", (0, 200, 200), 3),
                                      ("rdr2-ending.mp4", (220, 0, 0), 2)):
            ColorClip((320, 180), colour, duration=seconds).write_videofile(str(self.root / "footage" / name), fps=10, logger=None)
        slug = self.client.post("/api/videos", json={"topic": "News", "type": "news", "game": "GTA 5"}).get_json()["slug"]
        path = w.project(slug)
        plan = {"title": "Layered news", "claims": [{"text": "Verified", "sources": ["https://one.example/a", "https://two.example/b"]}],
                "mood": "bad", "publish_date": "2026-10-24",
                "background": [{"file": "rdr2-background.mp4", "offset": .5}, {"file": "rdr2-second.mp4", "offset": 0}],
                "ending": {"file": "rdr2-ending.mp4", "offset": 0, "seconds": 1},
                "shots": [{"kind": "official_image", "narration": "[excited] Hello", "seconds": 1, "file": "card.png",
                           "source_url": "https://www.rockstargames.com/newswire", "stamp": "RUMOUR"},
                          {"kind": "meme", "narration": "there", "seconds": 1, "file": "meme.mp4", "source_url": "https://giphy.com/gifs/x"}]}
        w.save_plan(path, plan)
        Image.new("RGB", (160, 90), (0, 200, 0)).save(path / "assets/card.png")
        ColorClip((120, 120), (220, 0, 220), duration=.5).write_videofile(str(path / "assets/meme.mp4"), fps=10, logger=None)
        with wave.open(str(path / "vo.mp3"), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 22050)
        w.write(path / "captions.json", {"text": "Hello there", "words": [{"text": "Hello", "start": 0, "end": .4}, {"text": "there", "start": .4, "end": .8}]})
        import math as m
        (self.root / "assets" / "sfx").mkdir(parents=True)
        for name in ("whoosh", "hit", "boom"):  # short tones stand in for the Pixabay sounds
            with wave.open(str(self.root / "assets" / "sfx" / f"{name}.wav"), "wb") as tone:
                tone.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
                tone.writeframes(b"".join(int(12000 * m.sin(2 * m.pi * 440 * i / 22050)).to_bytes(2, "little", signed=True) for i in range(4410)))
        config = w.read(self.root / "config.json")
        config["sfx"] = {"whoosh": "whoosh.wav", "hit": "hit.wav", "boom": "boom.wav"}
        w.write(self.root / "config.json", config)
        w.render(path)
        with VideoFileClip(str(path / "final.mp4")) as video:
            self.assertEqual(video.size, [1080, 1920])
            self.assertAlmostEqual(video.duration, 2, delta=.15)  # 1 s voice + 1 s ending
            self.assertGreater(video.audio.subclip(.42, .55).max_volume(), .05)  # impact hit on the meme (the voice is silent)
            self.assertLess(video.audio.subclip(.25, .38).max_volume(), .05)     # quiet between cues
            during = video.get_frame(.2)
            self.assertGreater(int(during[600, 540, 1]), 150)            # big green card in the middle
            self.assertTrue(60 < int(during[1700, 540, 2]) < 150)        # darkened blue gameplay underneath
            self.assertLess(int(during[1700, 540, 1]), 40)
            self.assertGreater(int(during[92, 1030, 0]), 200)            # yellow "26 DAYS" badge, top right
            self.assertGreater(int(during[1240:1370].max()), 180)        # caption
            meme = video.get_frame(.75)                                  # second scene: looping meme card...
            self.assertGreater(int(meme[600, 540, 0]), 150)
            self.assertLess(int(meme[600, 540, 1]), 80)
            self.assertTrue(60 < int(meme[1700, 540, 1]) < 150)          # ...over the second (cyan) gameplay clip
            after = video.get_frame(1.6)
            self.assertGreater(int(after[960, 540, 0]), 150)             # red mood-ending clip, full screen
            self.assertLess(int(after[960, 540, 2]), 80)


if __name__ == "__main__":
    unittest.main()
