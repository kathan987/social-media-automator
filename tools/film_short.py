"""Film-style Short builder (owner, 2026-11-02: "romantic filmstyle and aesthetic and subtle", NPC voices, little voiceover):
the owner's gameplay in a square film window (bloom, warm grade, grain, black lift), serif subtitles keyed to SOURCE
timestamps, chapter lines and a call log in the bars, a black end card, then mix.py (music, game audio, voice, sfx).
  python tools/film_short.py projects/<slug>/film.json
spec: {"slug", "src": "<file in footage/>", "window": 1080 (square side), "y": 400, "logo": "<path in assets/>",
       "cuts": [{"in": s, "out": s, "focus": 0-1, "speed": 1, "zoom": 0.05, "gvol": 1, "fin": 0, "fout": 0}],
       "subs": [{"src": s, "dur": s, "who": "JIMMY", "text": "..."}],          shown while that source moment plays
       "vo": [{"cut": i, "at": s, "file": "vo/v1.mp3", "text": "..."}],          at seconds into cut i
       "titles": [{"cut": i, "at": s, "dur": s, "text": "..."}],                 top bar chapter lines
       "calls": [{"cut": i, "name": "jimmy", "ok": false}],                      call log under the window
       "music": [{"file", "at", "dur", "vol", "fin", "fout"}], "sfx": [{"file" | "src_in"+"src_out", "cut", "at", "vol", "fx"}],
       "endcard": {"seconds": 4.5, "lines": [{"at": s, "dur": s, "text": "...", "style": "End|EndBig|Cta"}]}}
"cut": "end" means the end card. Writes projects/<slug>/build/ (clips, picture.mp4, film.ass, game.wav, music.wav),
<slug>/mix.json and <slug>/final.mp4; "version": "b" -> build-b/, mix-b.json, final-b.mp4 (keeps the other cut).
A music entry may start "from" a second into its file."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads(Path(sys.argv[1]).read_text("utf8"))
SLUG = ROOT / "projects" / spec["slug"]
V = f"-{spec['version']}" if spec.get("version") else ""
B = SLUG / f"build{V}"
shutil.rmtree(B / "fonts", ignore_errors=True)
(B / "fonts").mkdir(parents=True)
SRC = ROOT / "footage" / spec["src"]
W, Y = spec.get("window", 1080), spec.get("y", 400)
VOICE_FX = "highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=90,equalizer=f=3200:t=q:w=1.2:g=3"
for f in ("Medium", "MediumItalic", "SemiBold", "SemiBoldItalic"):  # static weights: libass can't match the variable font by name
    f = f"CormorantGaramond-{f}.ttf"
    shutil.copy(ROOT / "assets/fonts" / f, B / "fonts")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True, cwd=B)


# 1. clips: square crop, slow push-in (scale per frame, then centre crop), speed, dips to black; game audio per clip
starts, t = [], 0.0
for i, c in enumerate(spec["cuts"]):
    sp = c.get("speed", 1)
    d = (c["out"] - c["in"]) / sp
    vf = (f"crop=ih:ih:(iw-ow)*{c.get('focus', .5)}:0,scale={W}:{W},setpts=(PTS-STARTPTS)/{sp},"
          f"scale=w='trunc({W}*(1+{c.get('zoom', .05)}*t/{d:.3f})/2)*2':h=-2:eval=frame,crop={W}:{W},fps=30")
    if c.get("fin"):
        vf += f",fade=t=in:st=0:d={c['fin']}"
    if c.get("fout"):
        vf += f",fade=t=out:st={d - c['fout']:.3f}:d={c['fout']}"
    ff("-ss", c["in"], "-t", c["out"] - c["in"], "-i", SRC, "-an", "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "16",
       "-pix_fmt", "yuv420p", f"c{i}.mp4")
    af = (f"atempo={sp}," if sp != 1 else "") + f"volume={c.get('gvol', 1)},afade=t=in:d=0.04,afade=t=out:st={max(d - 0.06, 0):.3f}:d=0.06"
    ff("-ss", c["in"], "-t", c["out"] - c["in"], "-i", SRC, "-vn", "-ac", "2", "-ar", "48000", "-af", af, f"a{i}.wav")
    starts.append(round(t, 3))
    t += d
TALK = round(t, 3)
END = round(TALK + spec["endcard"]["seconds"], 3)
(B / "list.txt").write_text("".join(f"file 'c{i}.mp4'\n" for i in range(len(starts))))
ff("-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "cuts.mp4")


def out_t(src):
    """Source second -> output second (the cut that plays it)."""
    for s, c in zip(starts, spec["cuts"]):
        if c["in"] <= src < c["out"]:
            return s + (src - c["in"]) / c.get("speed", 1)
    raise ValueError(f"source {src}s is in no cut")


def cut_t(ref):
    return (TALK if ref["cut"] == "end" else starts[ref["cut"]]) + ref.get("at", 0)


# 2. picture: bloom + warm grade + lifted blacks + grain inside the window, black end card, bars, logo, subtitles
def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def ev(a, b, style, text, fade=(350, 350), mr=0):
    return f"Dialogue: 0,{ts(a)},{ts(b)},{style},,0,{mr},0,,{{\\fad({fade[0]},{fade[1]})}}{text}\n"


def cut_mr(a):
    """Right margin of the cut on screen at output second a (cut "mr": keeps subtitles off the in-game phone)."""
    i = max(k for k, s in enumerate(starts) if s <= a + 0.01)
    return spec["cuts"][i].get("mr", 0)


SUB_Y = 1920 - (Y + W) + 70  # subtitles sit inside the bottom of the picture
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Npc,Cormorant Garamond SemiBold,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,1,0,0,100,100,0,0,1,0,2.5,2,90,90,{SUB_Y},1
Style: Vo,Cormorant Garamond SemiBold,58,&H00F2F2F2,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,1,0,1,0,2.5,2,90,90,{SUB_Y},1
Style: Title,Cormorant Garamond Medium,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,1,0,0,100,100,1,0,1,0,0,2,80,80,{1920 - Y + 40},1
Style: Log,Cormorant Garamond SemiBold,40,&H00C8C8C8,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,1,0,1,0,0,8,30,30,{Y + W + 34},1
Style: End,Cormorant Garamond Medium,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,1,0,0,100,100,1,0,1,0,0,5,90,90,0,1
Style: EndBig,Cormorant Garamond SemiBold,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,0,0,5,80,80,0,1
Style: Cta,Cormorant Garamond Medium,44,&H00C8C8C8,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,3,0,1,0,0,2,80,80,{1920 - Y - W + 40},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for s in spec.get("subs", []):
    a = out_t(s["src"])
    who = f"{{\\i0\\fs32\\c&HB4B4B4&}}{s['who']}  {{\\r}}" if s.get("who") else ""
    ass += ev(a, a + s["dur"], "Npc", who + s["text"], (120, 200), cut_mr(a))
for v in spec.get("vo", []):
    a = cut_t(v)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(SLUG / v["file"])],
                               capture_output=True, text=True).stdout)
    ass += ev(a, a + dur + 0.2, "Vo", v["text"], (150, 250), cut_mr(a))
for x in spec.get("titles", []):
    a = cut_t(x)
    ass += ev(a, a + x["dur"], "Title", x["text"], (600, 600))
calls = spec.get("calls", [])
for k, c in enumerate(calls):  # the log grows one name per call; earlier names are struck through
    a, b = cut_t(c), (cut_t(calls[k + 1]) if k + 1 < len(calls) else TALK)
    names = [(f"{{\\c&H3A3AE0&\\b1}}{n['name']} ♥{{\\r}}" if n.get("ok") else
              (f"{{\\s1\\alpha&H70&}}{n['name']}{{\\r}}" if j < k else n["name"])) for j, n in enumerate(calls[:k + 1])]
    ass += ev(a, b, "Log", "{\\q2}" + "  ·  ".join(names), (250 if k == 0 else 0, 250 if k == len(calls) - 1 else 0))
for x in spec["endcard"]["lines"]:
    a = TALK + x["at"]
    ass += ev(a, min(a + x["dur"], END), x.get("style", "End"), x["text"], (500, 400))
(B / "film.ass").write_text(ass, "utf8")

look = ("split[a][b];[b]gblur=sigma=22,eq=brightness=-0.12[g];[a][g]blend=all_mode=screen:all_opacity=0.12,"
        "eq=contrast=1.08:saturation=0.95,colorbalance=rs=0.02:gs=0.01:bs=-0.03:rm=0.03:gm=0.01:bm=-0.04:rh=0.03:gh=0.01:bh=-0.05,"
        "curves=all='0/0.02 0.5/0.49 1/0.97',vignette=PI/5,noise=alls=6:allf=t+u")
graph = (f"[0:v]{look},tpad=stop_mode=add:stop_duration={END - TALK}:color=black,pad=1080:1920:0:{Y}:black,format=yuv420p[p];"
         f"[1:v]scale=-2:{spec.get('logo_h', 92)},format=rgba,colorchannelmixer=aa={spec.get('logo_alpha', 0.6)}[l];"
         f"[p][l]overlay=(W-w)/2:{spec.get('logo_y', 120)},ass=film.ass:fontsdir=fonts[v]")
ff("-i", "cuts.mp4", "-i", ROOT / "assets" / spec["logo"], "-filter_complex", graph, "-map", "[v]",
   "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "picture.mp4")

# 3. audio: game track, music bed, extra sfx (incl. replays of source moments), voice -> mix.json -> mix.py
n = len(starts)
ff(*sum((["-i", f"a{i}.wav"] for i in range(n)), []), "-filter_complex",
   "".join(f"[{i}:a]adelay={int(s * 1000)}:all=1[g{i}];" for i, s in enumerate(starts))
   + "".join(f"[g{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{END}[o]", "-map", "[o]", "game.wav")
mus = spec["music"]
ff(*sum((["-i", ROOT / m["file"]] for m in mus), []), "-filter_complex",
   "".join(f"[{i}:a]atrim={m.get('from', 0)}:{m.get('from', 0) + m['dur']},asetpts=PTS-STARTPTS,volume={m['vol']},afade=t=in:d={m.get('fin', .3)},"
           f"afade=t=out:st={m['dur'] - m.get('fout', 1)}:d={m.get('fout', 1)},adelay={int(m['at'] * 1000)}:all=1[m{i}];"
           for i, m in enumerate(mus))
   + "".join(f"[m{i}]" for i in range(len(mus))) + f"amix=inputs={len(mus)}:normalize=0,apad,atrim=0:{END}[o]", "-map", "[o]", "music.wav")
sfx = [{"file": str(B / "game.wav"), "at": 0, "vol": 1.0}]
for k, x in enumerate(spec.get("sfx", [])):
    if x.get("file"):
        f = str(ROOT / x["file"])
    else:  # a replay of a source moment (an echo of a line)
        f = str(B / f"x{k}.wav")
        ff("-ss", x["src_in"], "-t", x["src_out"] - x["src_in"], "-i", SRC, "-vn", "-ac", "2", "-ar", "48000", f)
    sfx.append({"file": f, "at": round(cut_t(x), 3), "vol": x.get("vol", 0.8), **({"fx": x["fx"]} if x.get("fx") else {})})
sfx += [{"file": str(SLUG / v["file"]), "at": round(cut_t(v), 3), "vol": v.get("vol", 1.0), "fx": VOICE_FX} for v in spec.get("vo", [])]
(SLUG / f"mix{V}.json").write_text(json.dumps({"video": str(B / "picture.mp4"), "out": str(SLUG / f"final{V}.mp4"), "music": str(B / "music.wav"),
                                           "music_vol": 1.0, "fade_out": 1.2, "sfx": sfx}, indent=1), "utf8")
subprocess.run([sys.executable, str(ROOT / "tools/mix.py"), str(SLUG / f"mix{V}.json")], check=True)
print(json.dumps({"cut_starts": starts, "talk_end": TALK, "end": END}))
