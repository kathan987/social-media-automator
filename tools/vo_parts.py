"""Voiceover built from parts: Edge TTS lines and real character lines cut from official trailers / footage, joined into
one projects/<slug>/vo.mp3 + words.json (same format as vo_edge.py, so sticker_short.py captions the character lines too).
Owner, 2026-11-03: explainers open on the real trailer moment, then the voice explains it.
  python tools/vo_parts.py <project-slug> parts.json [voice] [rate]
parts.json: [{"tts": "text"}, {"clip": "<path>", "in": s, "out": s, "words": [["Lucia,", 6.9, 7.6], ...], "vol": 1.0}, ...]
Clip word times are in the clip's own seconds (from faster-whisper); a short gap ("gap", default 0.15 s) separates parts."""
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
slug, parts = sys.argv[1], json.loads(Path(sys.argv[2]).read_text("utf8"))
voice = sys.argv[3] if len(sys.argv) > 3 else "en-US-ChristopherNeural"
rate = sys.argv[4] if len(sys.argv) > 4 else "+12%"
out = ROOT / "projects" / slug
TMP = Path(tempfile.mkdtemp())


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout)


async def tts(text, f):
    words, audio = [], bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary").stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":  # offsets are in 100-nanosecond ticks
            s = chunk["offset"] / 1e7
            words.append({"text": chunk["text"], "start": s, "end": s + chunk["duration"] / 1e7})
    f.write_bytes(audio)
    return words


async def main():
    words, files, t = [], [], 0.0
    for i, p in enumerate(parts):
        f = TMP / f"p{i}.wav"
        if "tts" in p:
            mp3 = TMP / f"p{i}.mp3"
            ws = await tts(p["tts"], mp3)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ac", "2", "-ar", "48000", str(f)], check=True)
            shift = 0.0
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(p["in"]), "-t", str(p["out"] - p["in"]), "-i", p["clip"], "-vn",
                            "-ac", "2", "-ar", "48000", "-af", f"volume={p.get('vol', 1.0)},afade=t=in:d=0.05,afade=t=out:st={p['out'] - p['in'] - 0.08:.3f}:d=0.08",
                            str(f)], check=True)
            ws, shift = [{"text": w, "start": a, "end": b} for w, a, b in p["words"]], -p["in"]
        words += [{"text": w["text"], "start": round(t + w["start"] + shift, 3), "end": round(t + w["end"] + shift, 3)} for w in ws]
        files.append(f)
        t += dur(f) + p.get("gap", 0.15)
        gap = TMP / f"g{i}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(p.get("gap", 0.15)), str(gap)], check=True)
        files.append(gap)
    (TMP / "list.txt").write_text("".join(f"file '{f.as_posix()}'\n" for f in files))
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(TMP / "list.txt"), "-c:a", "libmp3lame", "-b:a", "192k",
                    str(out / "vo.mp3")], check=True)
    (out / "words.json").write_text(json.dumps(words, indent=1), "utf8")
    (out / "script.md").write_text("\n\n".join(p.get("tts") or "[" + " ".join(w[0] for w in p["words"]) + "]" for p in parts) + "\n", "utf8")
    print(f"{t:.2f}s  " + " ".join(f"{w['text']}@{w['start']:.1f}" for w in words))


asyncio.run(main())
