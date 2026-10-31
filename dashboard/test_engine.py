"""Offline checks for the built-in engine: python -m unittest discover -s dashboard."""
import os
import tempfile
import unittest
from pathlib import Path

import engine


class EngineTests(unittest.TestCase):
    def test_extract_json_handles_fences_prose_trailing_commas_and_cut_off_replies(self):
        self.assertEqual(engine.extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(engine.extract_json('Sure! Here it is: {"a": [1, 2,], "b": "x",} Hope that helps.'), {"a": [1, 2], "b": "x"})
        self.assertEqual(engine.extract_json('{"title": "Hi", "shots": [{"kind": "motion", "text": "cut of'),
                         {"title": "Hi", "shots": [{"kind": "motion", "text": "cut of"}]})
        self.assertEqual(engine.extract_json('{"q": "a } inside a string"}'), {"q": "a } inside a string"})
        with self.assertRaisesRegex(ValueError, "no JSON"):
            engine.extract_json("no object here", "Gemini")

    def test_load_env_never_overrides_the_real_environment(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text('# comment\nSMA_TEST_A="from-file"\nSMA_TEST_B=from-file\nSMA_TEST_EMPTY=\n', "utf-8")
            os.environ["SMA_TEST_B"] = "real"
            try:
                engine.load_env(env)
                self.assertEqual(os.environ["SMA_TEST_A"], "from-file")
                self.assertEqual(os.environ["SMA_TEST_B"], "real")
                self.assertNotIn("SMA_TEST_EMPTY", os.environ)
            finally:
                for k in ("SMA_TEST_A", "SMA_TEST_B"):
                    os.environ.pop(k, None)

    def test_font_falls_back_without_font_files(self):
        old = engine.FONTS
        engine.FONTS, engine._fonts = Path(tempfile.gettempdir()) / "no-fonts-here", {}
        try:
            self.assertIsNotNone(engine.font(40).getbbox("A"))
        finally:
            engine.FONTS, engine._fonts = old, {}


if __name__ == "__main__":
    unittest.main()
