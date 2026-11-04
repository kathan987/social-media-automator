"""Mix a silent motion render with overlays (memes, AI clips), a music bed and timed SFX -> final.mp4.
Put the voiceover in as the first "sfx" entry (vol 1.0). Output is loudness-normalised to -14 LUFS (YouTube's level).

  python mix.py spec.json
spec: {"video": "...mp4", "out": "...mp4", "music": "...wav", "music_vol": 0.5, "fade_out": 1.5,
       "overlays": [{"file": "...mp4", "x": 60, "y": 700, "w": 960, "h": 880, "start": 29, "end": 33}],
       "sfx": [{"file": "...mp3", "at": 2.4, "vol": 0.9, "dur": 2.5, "fx": "<ffmpeg audio filters>"}],
       "pre": 1.0}   (seconds of intro prepended to the video, e.g. a 1 s logo sting: every sound shifts with it)
"""
import json
import subprocess
import sys


def main(spec):
    s = json.load(open(spec, encoding="utf8"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", s["video"]],
                               capture_output=True, text=True).stdout)
    args, graph, v = ["ffmpeg", "-v", "error", "-y", "-i", s["video"]], [], "[0:v]"
    for i, o in enumerate(s.get("overlays", []), 1):
        args += ["-stream_loop", "-1", "-i", o["file"]]  # memes are short: loop them over their window
        graph.append(f"[{i}:v]scale={o['w']}:{o['h']}:force_original_aspect_ratio=increase,crop={o['w']}:{o['h']},"
                     f"setpts=PTS-STARTPTS+{o['start']}/TB[o{i}]")
        graph.append(f"{v}[o{i}]overlay={o['x']}:{o['y']}:enable='between(t,{o['start']},{o['end']})':eof_action=pass[v{i}]")
        v = f"[v{i}]"
    n = len(s.get("overlays", [])) + 1
    args += (["-stream_loop", "-1"] if s.get("music_loop") else []) + ["-i", s["music"]]  # short themes loop under long videos
    fade = s.get("fade_out", 1.5)
    graph.append(f"[{n}:a]atrim=0:{dur},volume={s.get('music_vol', 0.5)},afade=t=in:d=0.3,afade=t=out:st={dur - fade}:d={fade}[mus]")
    mix = ["[mus]"]
    for j, c in enumerate(s.get("sfx", []), n + 1):
        args += ["-i", c["file"]]
        trim = f"atrim=0:{c['dur']}," if c.get("dur") else ""
        trim += f"{c['fx']}," if c.get("fx") else ""  # e.g. the voice boost (EQ + compression), a phone filter + echo
        if c.get("dur") and c.get("fade"):  # soft tail instead of a hard cut (theme stings)
            trim += f"afade=t=out:st={c['dur'] - c['fade']}:d={c['fade']},"
        ms = int((c["at"] + s.get("pre", 0)) * 1000)  # "pre": seconds of intro prepended to the video (sounds shift with it)
        graph.append(f"[{j}:a]{trim}volume={c.get('vol', 0.9)},adelay={ms}|{ms}[s{j}]")
        mix.append(f"[s{j}]")
    graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0,atrim=0:{dur},loudnorm=I=-14:TP=-1.5:LRA=11[aout]")  # YouTube plays at -14 LUFS
    args += ["-filter_complex", ";".join(graph), "-map", v if v != "[0:v]" else "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", str(dur), s["out"]]
    subprocess.run(args, check=True)
    print("mixed ->", s["out"])


if __name__ == "__main__":
    main(sys.argv[1])
