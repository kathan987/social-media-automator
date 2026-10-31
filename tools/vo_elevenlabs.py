"""ElevenLabs voiceover with word timings. Keys come from .env and are never printed.
  python tools/vo_elevenlabs.py <project-slug> <script.txt> [speed]
-> projects/<slug>/vo.mp3 + words.json + script.md. Mood tags like [excited] are performed by the voice, not captioned.
Speed defaults to 1.1 (faster reads hold Shorts viewers better). Free fallback: tools/vo_edge.py."""
import base64
import json
import math
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
env = ROOT / ".env"
if env.exists():
    for line in env.read_text("utf8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def words_from(alignment):
    """Character timings -> [{text, start, end}] per spoken word; [audio tags] are skipped."""
    chars = alignment["characters"]
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    words, text, begin, finish, in_tag = [], "", 0, 0, False
    for char, start, end in zip(chars, starts, ends):
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("Invalid character timing")
        if char == "[" or in_tag:
            in_tag = char != "]"
            char = " "
        if char.isspace():
            if text:
                words.append({"text": text, "start": begin, "end": finish})
                text = ""
        else:
            if not text:
                begin = start
            text += char
            finish = end
    if text:
        words.append({"text": text, "start": begin, "end": finish})
    if not words:
        raise ValueError("Voiceover has no timed words")
    return words


slug, script_file = sys.argv[1], Path(sys.argv[2])
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
out = ROOT / "projects" / slug
out.mkdir(parents=True, exist_ok=True)
text = " ".join(script_file.read_text("utf8").split())
config = ROOT / "config.json"
model = json.loads(config.read_text("utf8")).get("elevenlabs_model", "eleven_v4") if config.exists() else "eleven_v4"
r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{os.environ['ELEVENLABS_VOICE_ID']}/with-timestamps",
                  headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                  json={"text": text, "model_id": model, "voice_settings": {"speed": speed}}, timeout=180)
if not r.ok:
    sys.exit(f"ElevenLabs HTTP {r.status_code}: {r.text[:200]}")
data = r.json()
words = words_from(data.get("alignment") or data["normalized_alignment"])
(out / "vo.mp3").write_bytes(base64.b64decode(data["audio_base64"]))
(out / "words.json").write_text(json.dumps(words, indent=1), "utf8")
(out / "script.md").write_text(text + "\n", "utf8")
print(" ".join(f"{w['text']}@{w['start']:.1f}" for w in words))
