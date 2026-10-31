"""Free voiceover fallback (Microsoft Edge TTS, no key) with word timings, same outputs as vo.py.
  python vo_edge.py <video-slug> <script.txt> [voice] [rate]
-> videos/<slug>/vo.mp3 + words.json + script.md. ElevenLabs mood tags like [serious] are stripped (Edge can't act them).
Use it when the ElevenLabs quota runs out, or when you want a voice that costs nothing."""
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
slug, script_file = sys.argv[1], Path(sys.argv[2])
voice = sys.argv[3] if len(sys.argv) > 3 else "en-US-ChristopherNeural"
rate = sys.argv[4] if len(sys.argv) > 4 else "+12%"
out = ROOT / "projects" / slug
out.mkdir(parents=True, exist_ok=True)
text = " ".join(re.sub(r"\[[^\]]*\]", " ", script_file.read_text("utf8")).split())


async def main():
    words, audio = [], bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary").stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":  # offsets are in 100-nanosecond ticks
            start = chunk["offset"] / 1e7
            words.append({"text": chunk["text"], "start": round(start, 3), "end": round(start + chunk["duration"] / 1e7, 3)})
    if not words:
        sys.exit("Edge TTS returned no word timings")
    (out / "vo.mp3").write_bytes(audio)
    (out / "words.json").write_text(json.dumps(words, indent=1), "utf8")
    (out / "script.md").write_text(text + "\n", "utf8")
    print(" ".join(f"{w['text']}@{w['start']:.1f}" for w in words))


asyncio.run(main())
