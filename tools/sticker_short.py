"""Sticker-style Short builder: the owner's gameplay full screen, cut on chosen words, with phrase captions (active word
lit), title cards (kicker + headline through a mask), a trending hook, motion-graphics modules and a subscribe end card.
  python tools/sticker_short.py projects/<slug>/spec.json
spec: {"slug": "...", "scene": "<scenes/ folder>", "template": "explainer-scene",
       "badge": "NAME" | "logo": "st/x.png" (+ "pill": "LABEL" under the logo), "card_top": 250 (px, top title cards + hook),
       "accent": "#ffdd00" (captions, cards), "hot": "#ff3b30" (hook mark, stamps),
       "look": "rdr" (a named entry in LOOK_CSS: display font + palette overrides; add your own),
       "captions": "plain" (small whole phrases in Poppins, no word-by-word) | omitted (big phrases, spoken word lit),
       "keywords": ["word", ...] (one giant keyword per phrase that contains one, with a punch-in on the footage),
       "nocap": [[["word", after], ["word", after]], ...] (no captions in these windows: a graphic carries its own labels),
       "game_audio": 0.35 (volume of every clip's own audio under the voice; 0 = silent footage),
       "cuts": [["word", after_seconds, "clip", {offset, focus, bars, keep, fit, still, gamma, gvol}], ...],   first cut starts at 0
         clip: a name in footage/clips/, a path with an extension under footage/, or an absolute path (used as is)
       "stickers": [["id", "st/x.png" | "html:<b>TITLE</b><span>KICKER</span>", ["word", after], ["word", after] | "end", "css"], ...],
         title cards rotate through the spots tl, tr, c, ml, mr; "place:xx" in the css picks one,
       "hook": {"style": "slam" | "roll", "lines": [["word", after, "TEXT", hot?], ...]}   runs until the second cut,
       "fx": [{"kind": "poster" | "form" | "route" | "count" | "doors" | "light" | "flip" | "meter" | "blueprint" | "split" |
               "vote" | "notify" | "comment" | "callout" | "iris", "start": [...], "end": [...], ...}],  see the JS FX functions,
       "three": [{"kind": "timeline" | "jet", "start": [...], "end": [...], "labels": ["KICKER|TITLE|#hex"], "dim": 0.5}],
       "endcard": {"question": "...", "channel": "...", "tagline": "...", "seconds": 2.9},
       "lineup": ["st/a.png", ...]}
Writes <scene>/index.html (clips cut to <scene>/assets/bgN.mp4), projects/<slug>/cues.json, the clip audio in
projects/<slug>/game/ and the sfx (plus the voice boost and clip audio) in projects/<slug>/mix.json."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads(Path(sys.argv[1]).read_text("utf8"))
SLUG = ROOT / "projects" / spec["slug"]
SCENE = ROOT / "scenes" / spec["scene"]
A = SCENE / "assets"
LIB = ROOT / "assets"
words = json.loads((SLUG / "words.json").read_text("utf8"))
ENDC = spec.get("endcard")
TALK = round(words[-1]["end"] + 0.35, 2)  # voice done; the end card starts here
END = round(TALK + (ENDC.get("seconds", 2.9) if ENDC else 0.65), 2)
ACC, HOT = spec.get("accent", "#ffdd00"), spec.get("hot", "#ff3b30")


def at(ref):
    if ref == "end":
        return TALK
    token, after = ref[:2]
    return round(next(w["start"] for w in words if re.sub(r"[^a-z0-9]", "", w["text"].lower()) == token and w["start"] >= after), 2)


if spec.get("template"):  # explainer series: start from scenes/<template> (run tools/setup_scene.py first), always take its latest 3D layer
    tpl = SCENE.parent / spec["template"]
    if not SCENE.exists():
        shutil.copytree(tpl, SCENE, ignore=shutil.ignore_patterns("index.html", "selftest*", ".hyperframes", "*.mp4"))
    shutil.copy(tpl / "assets" / "explain3d.js", A / "explain3d.js")
LOOK = spec.get("look")  # a named look from LOOK_CSS below; its display font comes from assets/fonts/
LOOK_FONTS = {"rdr": "ChineseRocks-Regular.otf"}
(A / "fonts").mkdir(parents=True, exist_ok=True)
for f in [LIB / "fonts/Anton-Regular.ttf", LIB / "fonts/Poppins-SemiBold.ttf", LIB / "fonts/BebasNeue-Regular.ttf",
          LIB / "fonts/georgiab.ttf", LIB / "fonts/consolab.ttf"] + ([LIB / "fonts" / LOOK_FONTS[LOOK]] if LOOK in LOOK_FONTS else []):
    if not f.exists():  # the serif (poster), typewriter (form) and look fonts are optional: the page falls back
        print("font missing (fallback used):", f)
    elif not (A / "fonts" / f.name).exists():
        shutil.copy(f, A / "fonts")
PLAIN = spec.get("captions") == "plain"  # small regular-font phrases, shown whole (no word-by-word, no giant keyword)
GAME = spec.get("game_audio", 0)  # volume of the clip's own audio under the voice (0 = silent footage)
if ENDC and (LIB / "logo.jpg").exists() and not (A / "st" / "avatar.jpg").exists():  # your channel logo
    (A / "st").mkdir(exist_ok=True)
    shutil.copy(LIB / "logo.jpg", A / "st" / "avatar.jpg")

cuts = [0.0] + [at([t, a]) for t, a, *_ in spec["cuts"][1:]]
segs = [(cuts[i], cuts[i + 1] if i + 1 < len(cuts) else END) for i in range(len(cuts))]
for i, (cut, (s, e)) in enumerate(zip(spec["cuts"], segs)):
    # opt: offset (s), focus (0 left .. 1 right), bars (cinematic letterbox), keep [top, bottom] fractions (drops game subtitles)
    clip, opt = cut[2], (cut[3] if len(cut) > 3 else {})
    src = ROOT / "footage" / (clip if Path(clip).suffix else f"clips/{clip}.mp4")  # an absolute path wins over footage/
    keep = opt.get("keep") or ([0.125, 0.875] if opt.get("bars") else None)
    vf = (f"crop=iw:ih*{keep[1] - keep[0]}:0:ih*{keep[0]}," if keep else "") + f"scale=-2:1920,crop=1080:1920:(iw-1080)*{opt.get('focus', .5)}:0,fps=30"
    if opt.get("fit"):  # whole 16:9 frame (zoom = fit x 1.4 ...) over a blurred fill: for wide subjects like a poster in hand
        w = int(1080 * opt["fit"]) // 2 * 2
        vf = (f"crop=iw:ih*{keep[1] - keep[0]}:0:ih*{keep[0]}," if keep else "") + f"split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=24:2,eq=brightness=-0.12[bg];[b]scale={w}:-2,crop=1080:ih[fg];[bg][fg]overlay=0:(H-h)/2,fps=30"
    if opt.get("gamma"):  # lift a night clip
        vf += f",eq=gamma={opt['gamma']}:saturation=1.1"
    inp = ["-stream_loop", "-1", "-ss", str(opt.get("offset", 0)), "-i", str(src)]
    if opt.get("still"):  # freeze one frame (a document held up for under a second); the page's slow push moves it
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(opt.get("offset", 0)), "-i", str(src), "-frames:v", "1", str(A / f"still{i}.png")], check=True)
        inp = ["-loop", "1", "-i", str(A / f"still{i}.png")]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp,
                    "-t", str(round(e - s + 0.2, 2)), "-an", "-vf", vf,
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", str(A / f"bg{i}.mp4")], check=True)
    if opt.get("gvol", GAME):  # the same stretch of game audio (punches, shots, ambience), mixed under the voice
        (SLUG / "game").mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(opt.get("offset", 0)), "-i", str(src), "-t", str(round(e - s, 2)), "-vn",
                        "-af", "afade=t=in:d=0.08,afade=t=out:st=%s:d=0.12" % max(0, round(e - s - 0.12, 2)), str(SLUG / "game" / f"a{i}.wav")], check=True)

hook = spec.get("hook")
HOOK_END = cuts[1] if hook else 0
if hook:
    hook = {"style": hook.get("style", "slam"), "end": HOOK_END,
            "lines": [{"t": 0 if j == 0 else at(ln[:2]), "text": ln[2], "hot": bool(ln[3:4] and ln[3])} for j, ln in enumerate(hook["lines"])]}

# captions: phrases of up to 3 words / 16 characters, broken after punctuation; the hook is its own caption
W = [[round(w["start"], 2), re.sub(r"[^\w'?!-]", "", w["text"]).upper()] for w in words]
groups, cur = [], []
for k, (t, txt) in enumerate(W):
    if t < HOOK_END:
        continue
    if cur and (len(" ".join(W[j][1] for j in cur + [k])) > (30 if PLAIN else 16) or t - words[cur[-1]]["end"] > 0.3):  # a pause ends a phrase
        groups.append(cur)
        cur = []
    cur.append(k)
    if len(cur) == (6 if PLAIN else 3) or re.search(r"[.,?!:]$", words[k]["text"]):
        groups.append(cur)
        cur = []
if cur:
    groups.append(cur)
groups = [{"w": g, "s": W[g[0]][0]} for g in groups]
for a0, b0 in spec.get("nocap", []):  # windows where a graphic carries its own labels (no captions on top of it)
    groups = [g for g in groups if not (at(a0) <= g["s"] < at(b0))]
KW = {w.lower() for w in spec.get("keywords", [])}  # one giant keyword per phrase (caption hierarchy)
for g in groups:
    g["kw"] = next((k for k in g["w"] if re.sub(r"[^a-z0-9]", "", words[k]["text"].lower()) in KW), None)
kw_times = [W[g["kw"]][0] for g in groups if g["kw"] is not None]
for n, g in enumerate(groups):  # hold until the next phrase when the gap is short, else clear 0.3 s after the last word
    nxt = groups[n + 1]["s"] if n + 1 < len(groups) else None
    g["e"] = nxt if nxt and nxt - words[g["w"][-1]]["end"] < 0.6 else round(min(words[g["w"][-1]]["end"] + 0.3, TALK), 2)

PLACES = ["tl", "tr", "c", "ml", "mr"]  # title-card spots, rotated so no two cards sit in the same place; `place:xx` in the css picks one
cards, st = [], []
for sid, src, a, b, css in spec["stickers"]:
    if src.startswith("html:"):  # old chip markup -> title card: <b> is the headline, <span> the kicker
        m = re.search(r"<b>(.*?)</b>\s*<span>(.*?)</span>", src)
        col = re.search(r"border-color:\s*(#[0-9a-fA-F]+)", css)
        place = re.search(r"place:\s*(\w+)", css)
        cards.append({"s": at(a), "e": at(b), "t": m[1], "k": m[2], "c": col[1] if col else ACC,
                      "p": place[1] if place else PLACES[len(cards) % len(PLACES)]})
    else:
        st.append((sid, src, at(a), at(b), css))

fx = []
for f in spec.get("fx", []):
    f = {**f, "s": at(f["start"]), "e": at(f["end"])}
    for key in ("stamp_at", "sub_at", "swing_at", "punch_at", "stink_at", "a_at", "b_at", "note_at", "cold_at", "roll_at", "open_at"):
        if key in f:
            f[key] = at(f[key])
    for r in f.get("rows", []) + f.get("options", []):
        r["t"] = at(r["at"])
    fx.append(f)
three = [{**t, "start": at(t["start"]), "end": at(t["end"])} for t in spec.get("three", [])]
dims =[[t3["start"], t3["end"], t3["dim"]] for t3 in three if t3.get("dim")]
lineup = spec.get("lineup") or []

# sound for every visible action (times match the tweens in the page script)
sfx = [(0.0, "boom")] + [(c, "whoosh") for c in cuts[1:]]
if hook:
    sfx += [(ln["t"], "hit") for ln in hook["lines"][1:]]
sfx += [(c["s"], "tick") for c in cards]
for f in fx:
    sfx.append((f["s"] + (0.2 if f["kind"] == "route" else 0), "whoosh" if f["kind"] != "iris" else "hit"))
    if f["kind"] in ("notify", "comment"):  # typing
        sfx += [(f["s"] + 0.45 + q * 0.11, "tick") for q in range(6)]
    sfx += [(r["t"] + 0.35, "tick") for r in f.get("rows", [])]
    if "stamp_at" in f:
        sfx.append((f["stamp_at"] + 0.16, "boom"))
if ENDC:
    sfx += [(TALK + 1.3, "click"), (TALK + 1.5, "bell")]
sfx = sorted((round(t, 2), n) for t, n in sfx)
(SLUG / "cues.json").write_text(json.dumps({"cuts": cuts, "stickers": {s[0]: s[2] for s in st}, "cards": [c["s"] for c in cards],
                                            "talk": TALK, "end": END, "sfx": sfx}, indent=1), "utf8")
SFX = {"boom": ("boom.mp3", 0.45, 1.6), "hit": ("hit.mp3", 0.3, 0.9), "whoosh": ("whoosh.mp3", 0.35, None),
       "tick": ("click.mp3", 0.35, None), "click": ("click.mp3", 0.8, None), "bell": ("bell.mp3", 0.5, None)}  # assets/sfx/
VOICE_FX = "highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=90,equalizer=f=3200:t=q:w=1.2:g=3"  # voice boost
mix_file = SLUG / "mix.json"
if not (A / "grain.png").exists():  # film grain tile for the whole frame
    from PIL import Image
    Image.frombytes("L", (300, 300), os.urandom(300 * 300)).save(A / "grain.png")
if mix_file.exists():  # keep the voice and music, replace the effects and the clip audio
    mix = json.loads(mix_file.read_text("utf8"))
    mix["sfx"] = [{**c, "fx": VOICE_FX} for c in mix["sfx"] if c["file"].endswith("vo.mp3")] + [
        {"file": f"assets/sfx/{SFX[n][0]}", "at": t, "vol": SFX[n][1], **({"dur": SFX[n][2]} if SFX[n][2] else {})} for t, n in sfx if (LIB / "sfx" / SFX[n][0]).exists()] + [
        {"file": f"projects/{spec['slug']}/game/a{i}.wav", "at": s, "vol": (c[3] if len(c) > 3 else {}).get("gvol", GAME)}
        for i, (c, (s, e)) in enumerate(zip(spec["cuts"], segs)) if (c[3] if len(c) > 3 else {}).get("gvol", GAME)]
    mix_file.write_text(json.dumps(mix, indent=1), "utf8")

STROKE = ",".join(f"{x}px {y}px 0 #000" for x, y in [(7, 0), (-7, 0), (0, 7), (0, -7), (5, 5), (-5, 5), (5, -5), (-5, -5)])
bg_html = "\n".join('  <video id="bg%d" class="clip bg" src="assets/bg%d.mp4" muted playsinline data-start="%s" data-duration="%s" data-track-index="0"></video>'
                    % (i, i, s, round(e - s, 2)) for i, (s, e) in enumerate(segs))
st_html = "\n".join('    <img class="st" id="%s" src="assets/%s" style="%s">' % (i, f, css) for i, f, _, _, css in st)
lu_w = int(1040 / max(len(lineup), 1))
lu_html = "\n".join('    <img class="lu" id="lu%d" src="assets/%s" style="left:%dpx;width:%dpx">' % (k, f, int(20 + k * lu_w - lu_w * 0.45), int(lu_w * 1.9))
                    for k, f in enumerate(lineup))  # overlapping group shot: each sticker ~2x its slot
top_html = ('<div id="badge"><i></i>%s<i></i></div>' % spec["badge"]) if spec.get("badge") else (
    '<div id="top"><img src="assets/%s"><div id="pill">%s</div></div>' % (spec.get("logo", "st/logo.png"), spec["pill"]) if spec.get("pill")
    else '<img id="logo" src="assets/%s">' % spec.get("logo", "st/logo.png"))
three_head = ("<script>window.__three = %s; window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};"
              " window.__hf.buildReady.three = new Promise(function (r) { window.__threeReady = r; });</script>\n"
              '<script type="module" src="assets/explain3d.js"></script>' % json.dumps(three)) if three else ""
three_html = '    <canvas id="three" width="1080" height="1920"></canvas>' if three else ""
data = {"words": W, "groups": groups, "cuts": cuts, "end": END, "talk": TALK, "acc": ACC, "hot": HOT, "hook": hook, "cards": cards,
        "st": [[s[0], s[2], s[3]] for s in st], "fx": fx, "dims": dims, "kwt": kw_times, "endcard": ENDC, "nlu": len(lineup), "plain": PLAIN}
LOOK_CSS = {None: "", "rdr": """@font-face{font-family:"Rocks";src:url("assets/fonts/ChineseRocks-Regular.otf")}
#root,.stamp,.form .fh,.vote .opt,.route text,.clb{font-family:"Rocks",sans-serif!important}
.card .kk,.fxbox .kk,#badge{font-family:"Rocks";letter-spacing:.14em}
.card .tt span,.hook .hl>span{letter-spacing:.02em}
.form{background:rgba(14,11,9,.9);color:#fff;border:3px solid rgba(255,255,255,.8);font-family:"Poppins"}
.form .fs{color:#fff;border-bottom-color:#fff}.form .row{border-bottom-color:rgba(255,255,255,.3)}
.form .ok{color:#fff}.form .bad{color:var(--hot)}.form .ok~svg{stroke:#fff}.form .bad~svg{stroke:var(--hot)}
.form .stamp{background:rgba(14,11,9,.94)}
.endc .eq{font-size:120px}"""}[LOOK]  # "rdr": a western display font for every heading, white + red only
page = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<script src="assets/gsap.min.js"></script>
<!-- Generated by tools/sticker_short.py -->
<style>
@font-face{font-family:"Bebas";src:url("assets/fonts/BebasNeue-Regular.ttf")}
@font-face{font-family:"Anton";src:url("assets/fonts/Anton-Regular.ttf")}
@font-face{font-family:"Poppins";src:url("assets/fonts/Poppins-SemiBold.ttf")}
@font-face{font-family:"Serif";src:url("assets/fonts/georgiab.ttf")}
@font-face{font-family:"Mono";src:url("assets/fonts/consolab.ttf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:"Anton",sans-serif;--acc:__ACC__;--hot:__HOT__;--ctop:__CTOP__px}
#top{position:absolute;left:0;right:0;top:56px;display:flex;flex-direction:column;align-items:center;gap:10px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))}
#top img{width:230px}
#pill{font-family:"Poppins";font-size:30px;letter-spacing:.24em;color:#111;background:var(--acc);padding:6px 22px 4px;border-radius:30px}
.p-tl{left:80px;right:auto;top:var(--ctop);text-align:left}
.p-tr{right:80px;left:auto;top:var(--ctop);text-align:right}
.p-c{left:80px;right:80px;top:600px;text-align:center}
.p-ml{left:80px;right:auto;top:820px;text-align:left}
.p-mr{right:80px;left:auto;top:820px;text-align:right}
.p-tr .kk,.p-mr .kk{flex-direction:row-reverse}.p-c .kk{justify-content:center}
.p-tr .kk i,.p-mr .kk i{transform-origin:100% 50%}
.fxbox{position:absolute;opacity:0}
.fxbox .kk{display:flex;align-items:center;gap:20px;font-family:"Poppins";font-size:40px;letter-spacing:.2em;color:var(--acc);text-shadow:0 2px 12px rgba(0,0,0,.9)}
.fxbox .kk i{display:block;width:84px;height:8px;background:var(--acc)}
.cnt{height:1em;overflow:hidden;font-size:300px;line-height:1;color:#fff;text-shadow:0 10px 40px rgba(0,0,0,.7)}
.cnt .ladder{display:block}
.fxbox .sub{font-family:"Poppins";font-size:34px;letter-spacing:.16em;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.9)}
.flip .big{font-size:330px;line-height:1;color:#fff;text-shadow:0 10px 40px rgba(0,0,0,.7)}
.doors{position:absolute;opacity:0;display:grid;gap:16px;width:760px;left:160px;top:780px;perspective:1000px}
.door{height:104px;border-radius:8px 8px 0 0;background:radial-gradient(circle at 50% 60%,#fff3c4,#ffb347 55%,#c0601a);box-shadow:0 0 34px rgba(255,170,60,.55)}
.door i{display:block;width:100%;height:100%;border-radius:8px 8px 0 0;background:linear-gradient(#323848,#1b1f2a);border:4px solid #f4f4f4;transform-origin:0 50%}
.light{position:absolute;inset:0;opacity:0}
.light img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.light i{position:absolute;width:90px;height:90px;margin:-45px 0 0 -45px;border-radius:50%;background:radial-gradient(#fff,rgba(255,255,255,.6) 35%,rgba(255,255,255,0) 70%)}
.meter{position:absolute;inset:0;opacity:0}
.meter .mimg{position:absolute;left:140px;top:340px;width:600px;height:760px;object-fit:cover;border:10px solid #fff;border-radius:12px;box-shadow:0 30px 60px rgba(0,0,0,.6)}
.meter .gauge{position:absolute;left:540px;top:820px;width:470px;filter:drop-shadow(0 12px 24px rgba(0,0,0,.7))}
.meter .gauge text{font-family:"Anton";font-size:30px;fill:#fff}
.meter .stink{position:absolute;left:230px;top:250px;width:420px;height:420px;fill:none;stroke:var(--acc);stroke-width:10;stroke-linecap:round;filter:drop-shadow(0 0 8px rgba(0,0,0,.6))}
.bp{position:absolute;left:70px;top:340px;width:940px;height:740px;opacity:0;border-radius:10px;color:#e7f0f9;font-family:"Mono",monospace;overflow:hidden;background:linear-gradient(rgba(231,240,249,.1) 2px,transparent 2px) 0 0/44px 44px,linear-gradient(90deg,rgba(231,240,249,.1) 2px,transparent 2px) 0 0/44px 44px,radial-gradient(circle at 40% 30%,#2a58a6,#18336b 75%);box-shadow:0 34px 70px rgba(0,0,0,.6)}
.bp .bph{padding:30px 40px 22px;font-size:34px;letter-spacing:.12em;border-bottom:3px solid rgba(231,240,249,.7)}
.bp svg{position:absolute;left:20px;top:130px;width:900px;height:560px;fill:none;stroke:#e7f0f9;stroke-width:5;stroke-linecap:round;stroke-linejoin:round}
.bp .bx{position:absolute;top:330px;font-family:"Anton";font-size:62px;line-height:1.05;text-align:center}
.bp .bx small{display:block;font-family:"Mono",monospace;font-size:28px;letter-spacing:.14em;margin-bottom:10px;opacity:.85}
.bp .b1{left:60px;width:330px}.bp .b2{left:560px;width:320px}
.bp .bpn{position:absolute;left:560px;width:320px;top:520px;text-align:center;font-size:30px;letter-spacing:.12em;color:#fff}
.split{position:absolute;inset:0;opacity:0}
.split .half{position:absolute;left:60px;right:60px;height:390px;overflow:hidden;border:8px solid #fff;border-radius:12px;box-shadow:0 24px 50px rgba(0,0,0,.6)}
.split .top{top:330px}.split .bot{top:740px}
.split img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.split .yr{position:absolute;left:26px;bottom:14px;font-size:120px;line-height:1;color:var(--acc);text-shadow:0 6px 20px rgba(0,0,0,.8)}
.split .lb{position:absolute;left:30px;top:22px;font-family:"Poppins";font-size:34px;letter-spacing:.2em;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.9)}
.split .therm{position:absolute;right:40px;top:40px;width:90px;height:300px}
.vote{position:absolute;left:0;right:0;top:780px;display:flex;justify-content:center;gap:40px}
.vote .opt{opacity:0;font-family:"Anton";font-size:76px;padding:16px 44px 12px;border-radius:999px;box-shadow:0 18px 40px rgba(0,0,0,.55)}
.vote .o0{background:var(--hot);color:#fff}.vote .o1{background:var(--acc);color:#111}
.bg{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover}
#ui,.L{position:absolute;inset:0}
#scrim{position:absolute;inset:0;background:linear-gradient(rgba(0,0,0,.62),rgba(0,0,0,0) 34%,rgba(0,0,0,0) 52%,rgba(0,0,0,.5))}
#dim{position:absolute;inset:0;background:#05060a;opacity:0}
#logo{position:absolute;left:50%;top:40px;width:430px;margin-left:-215px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))}
#badge{position:absolute;left:0;right:0;top:118px;display:flex;justify-content:center;align-items:center;gap:22px;font-family:"Poppins";font-size:34px;letter-spacing:.32em;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.9);white-space:nowrap}
#badge i{display:block;width:64px;height:4px;background:var(--acc)}
.cap{position:absolute;left:70px;right:70px;top:1150px;text-align:center;font-size:106px;line-height:1.06;color:#fff;opacity:0;text-shadow:__STROKE__,0 14px 26px rgba(0,0,0,.6)}
.cap span{display:inline-block}
.cap.haskw span:not(.kw){font-size:64px}
.cap .kw{display:block;font-size:168px;line-height:.98;color:var(--acc)}
#bgw{position:absolute;inset:0}
#vig{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 52%,rgba(0,0,0,.55) 100%)}
#grain{position:absolute;left:-300px;top:-300px;right:-300px;bottom:-300px;background:url(assets/grain.png);opacity:.09;mix-blend-mode:overlay}
.glass{background:rgba(250,248,244,.95);border-radius:30px;box-shadow:0 24px 60px rgba(0,0,0,.4);color:#16171b}
.ntf,.cmt{position:absolute;left:70px;right:70px;top:340px;opacity:0;padding:26px 32px;font-family:"Poppins"}
.ntf .hd,.cmt .hd{display:flex;align-items:center;gap:16px}
.ntf .av,.cmt .av{width:58px;height:58px;border-radius:50%;background:var(--hot);color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px}
.ntf .ap,.cmt .ap{font-size:26px;color:#80838c}.ntf .ap b,.cmt .ap b{color:#16171b}
.ntf .tx{display:inline-block;font-size:44px;line-height:1.2;margin-top:14px}
.ntf .rp,.cmt .rp{font-size:30px;color:#555b66;margin-top:14px;padding:12px 18px;background:#eceae5;border-radius:18px}
.cmt .fl{position:relative;margin-top:16px;padding:14px 22px;border-radius:20px;background:#eceae5;font-size:44px;min-height:82px}
.cmt .ph{position:absolute;left:22px;top:14px;color:#9a9da6}.cmt .ty{display:inline-block}
.cmt .ok{display:inline-block;margin-top:14px;padding:8px 18px;border-radius:20px;background:#1f8a4c;color:#fff;font-size:28px;opacity:0}
.card{position:absolute;opacity:0}
.card .kk{display:flex;align-items:center;gap:20px;font-family:"Poppins";font-size:40px;letter-spacing:.2em;color:var(--c);text-shadow:0 2px 12px rgba(0,0,0,.9)}
.card .kk i{display:block;width:84px;height:8px;background:var(--c);transform-origin:0 50%}
.card .tt{overflow:hidden;padding:6px 0 12px}
.card .tt span{display:block;font-size:138px;line-height:1.02;color:#fff;text-shadow:0 8px 34px rgba(0,0,0,.7)}
.st{position:absolute;opacity:0;filter:drop-shadow(0 12px 18px rgba(0,0,0,.6))}
.lu{position:absolute;bottom:110px;height:900px;object-fit:contain;object-position:50% 100%;opacity:0;filter:drop-shadow(0 10px 14px rgba(0,0,0,.6))}
.hook{position:absolute;left:60px;right:60px;top:calc(var(--ctop) + 40px);text-align:center}
.hook .hl{opacity:0;overflow:hidden;padding:4px 0}
.hook .hl>span{display:inline-block;position:relative;z-index:1;isolation:isolate;font-size:124px;line-height:1.04;color:#fff;padding:0 20px;text-shadow:0 10px 30px rgba(0,0,0,.7)}
.hook .mk{position:absolute;left:0;right:0;top:9%;bottom:4%;background:var(--hot);z-index:-1;transform-origin:0 50%}
.hook.roll .hl.hot>span{color:var(--acc)}
.cell{display:inline-block;position:relative;overflow:hidden;vertical-align:top}
.cell .gh{visibility:hidden}.cell .sp{position:absolute;left:0;right:0;top:0;text-align:center}
.hook.roll .bar{position:absolute;left:12%;right:12%;bottom:0;height:10px;background:var(--acc);transform-origin:0 50%}
.poster{position:absolute;left:250px;top:330px;width:580px;height:760px;opacity:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;
  background:radial-gradient(ellipse at 50% 45%,#f1e4c3 0%,#e2cfa2 60%,#b48b52 100%);box-shadow:0 34px 70px rgba(0,0,0,.65),inset 0 0 70px rgba(90,55,20,.55);color:#2b1a0c;font-family:"Serif",Georgia,serif;text-align:center}
.poster .p1{font-size:128px;line-height:1;letter-spacing:.03em}
.poster .rule{width:440px;height:6px;border-top:2px solid #2b1a0c;border-bottom:2px solid #2b1a0c}
.poster .p2{font-size:84px;line-height:1}.poster .p3{font-size:44px;letter-spacing:.12em}.poster .p4{font-size:28px;letter-spacing:.2em;opacity:.75}
.poster .nail{position:absolute;top:26px;left:50%;width:22px;height:22px;margin-left:-11px;border-radius:50%;background:radial-gradient(#777,#222)}
.stamp{position:absolute;left:50px;right:50px;top:250px;opacity:0;border:12px solid var(--hot);border-radius:14px;color:var(--hot);font-family:"Anton";font-size:150px;line-height:1;padding:8px 0 16px;text-align:center;mix-blend-mode:multiply}
.stamp small{display:block;font-family:"Poppins";font-size:32px;letter-spacing:.14em;margin-top:6px}
.form{position:absolute;left:100px;top:360px;width:880px;opacity:0;background:#f3f0e8;border-radius:12px;padding:44px 50px 56px;box-shadow:0 34px 70px rgba(0,0,0,.6);font-family:"Mono",Consolas,monospace;color:#1d2430}
.form .fh{font-family:"Anton";font-size:66px;white-space:nowrap}
.form .fs{font-size:30px;color:#5d6675;margin:6px 0 20px;padding-bottom:18px;border-bottom:5px solid #1d2430}
.form .row{display:flex;align-items:center;font-size:44px;padding:24px 0;border-bottom:2px dashed #b9b4a8;opacity:0}
.form .row span{flex:1}.form .row b{margin-right:22px}.form .ok{color:#1f8a4c}.form .bad{color:#c1121f}
.form svg{width:58px;height:58px;fill:none;stroke-width:4.5;stroke-linecap:round;stroke-dasharray:60;stroke-dashoffset:60}
.form .ok~svg{stroke:#1f8a4c}.form .bad~svg{stroke:#c1121f}
.poster .stamp{top:210px;left:30px;right:30px;font-size:190px;background:rgba(241,228,195,.93);mix-blend-mode:normal;box-shadow:0 0 0 8px rgba(241,228,195,.93)}
.form .stamp{top:200px;left:60px;right:60px;font-size:120px;background:rgba(243,240,232,.93);mix-blend-mode:normal}
.route{position:absolute;inset:0;opacity:0}
.route text{font-family:"Anton";fill:#fff;paint-order:stroke;stroke:#000;stroke-width:10px}
.route .kt{font-family:"Poppins";font-size:30px;letter-spacing:.2em;fill:var(--acc);stroke-width:8px}
.plane{position:absolute;left:-40px;top:-40px;width:80px;height:80px;opacity:0;filter:drop-shadow(0 6px 10px rgba(0,0,0,.7))}
.iris{position:absolute;inset:0;opacity:0;--r:1300px;background:radial-gradient(circle at 50% 63%,rgba(0,0,0,0) var(--r),rgba(3,3,6,.92) calc(var(--r) + 160px))}
.endc{position:absolute;inset:0;opacity:0}
.endc .dim{position:absolute;inset:0;background:rgba(5,5,9,.72)}
.endc .eq{position:absolute;left:90px;right:90px;top:360px;text-align:center;font-size:100px;line-height:1.06;color:#fff}
.endc .sub{position:absolute;left:0;right:0;top:800px;display:flex;justify-content:center;align-items:center;gap:30px}
.endc .sub img{width:150px;height:150px;border-radius:50%;border:5px solid #fff}
.endc .nm{font-family:"Poppins";font-size:58px;line-height:1.1;color:#fff}.endc .nm small{display:block;font-size:30px;color:#c4c4cc;letter-spacing:.05em}
.endc .btn{position:absolute;left:270px;top:1020px;width:540px;height:128px;border-radius:64px;background:#ff0033;color:#fff;font-family:"Poppins";font-size:50px;letter-spacing:.1em;box-shadow:0 16px 40px rgba(0,0,0,.5)}
.endc .btn span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}.endc .b2{opacity:0}
.endc .bell{position:absolute;left:836px;top:1042px;width:84px;height:84px;fill:#fff;opacity:0}
.endc .cur{position:absolute;left:560px;top:1090px;width:110px;height:110px}
#flash{position:absolute;inset:0;background:#fff;opacity:0}
#three{position:absolute;inset:0;width:1080px;height:1920px}
.cap.plain{top:1270px;font-family:"Poppins";font-size:50px;line-height:1.28;text-shadow:0 0 6px #000,0 2px 4px #000,0 6px 18px rgba(0,0,0,.8)}
__LOOK__
</style>
__THREE_HEAD__
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__END__" data-width="1080" data-height="1920">
<div id="bgw">
__BG__
</div>
  <div id="ui" class="clip" data-start="0" data-duration="__END__" data-track-index="1" data-layout-allow-overlap data-layout-allow-overflow>
    <div id="scrim"></div>
    <div id="vig"></div>
    <div id="dim"></div>
__THREE__
    <div class="L" id="Lfx"></div>
__ST__
__LU__
    <div class="L" id="Lcard"></div>
    <div class="L" id="Lhook"></div>
    <div class="L" id="Lcap"></div>
    __TOP__
    <div id="grain"></div>
    <div id="flash"></div>
    <div class="L" id="Lend"></div>
  </div>
</div>
<script>
const D = __DATA__;
const tl = gsap.timeline({ paused: true });
function el(tag, cls, html, parent) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  parent.appendChild(e);
  return e;
}
const $ = (id) => document.getElementById(id);

// footage: punch-in on every cut, slow push while it plays, a light flash on the cut (no shake)
D.cuts.forEach(function (c, i) {
  const e = $("bg" + i), nx = i + 1 < D.cuts.length ? D.cuts[i + 1] : D.end;
  tl.fromTo(e, { scale: 1.14 }, { scale: 1.0, duration: 0.28, ease: "power3.out" }, c)
    .to(e, { scale: 1.06, duration: Math.max(0.3, nx - c - 0.28), ease: "none" }, c + 0.28);
  if (i > 0) tl.to("#flash", { opacity: 0.32, duration: 0.03 }, c).to("#flash", { opacity: 0, duration: 0.2 }, c + 0.03);
});

// departure-board roll: each letter spins through random glyphs and lands (hook "roll" and fx "flip")
let rollSeed = 7;
const rollRnd = () => (rollSeed = (rollSeed * 9301 + 49297) % 233280) / 233280;
function rollCells(span, text, t, animate) {
  const AB = "BDGHJLMNPQRSTVWXZ0123456789";  // no vowels: a scramble never spells a word
  let ci = 0;
  for (const ch of text) {
    if (ch === " ") { span.appendChild(document.createTextNode(" ")); continue; }
    const cell = el("span", "cell", null, span), n = 6 + Math.floor(rollRnd() * 5);
    el("span", "gh", ch, cell);
    let s = "";
    for (let q = 0; q < n; q++) s += AB[Math.floor(rollRnd() * AB.length)] + "<br>";
    const strip = el("span", "sp", s + ch, cell);
    if (animate) tl.fromTo(strip, { yPercent: 0 }, { yPercent: -100 * n / (n + 1), duration: 0.45 + ci * 0.03, ease: "power3.out" }, t);
    else gsap.set(strip, { yPercent: -100 * n / (n + 1) });
    ci++;
  }
  return 0.45 + ci * 0.03;
}

// hook: "slam" lines rise through a mask, the hot line gets a marker swipe; "roll" letters spin like a departure board
if (D.hook) {
  const H = D.hook, box = el("div", "hook " + H.style, null, $("Lhook"));
  tl.set("#dim", { opacity: 0.3 }, 0).to("#dim", { opacity: 0, duration: 0.2 }, H.end - 0.12);
  H.lines.forEach(function (ln, j) {
    const row = el("div", "hl" + (ln.hot ? " hot" : ""), null, box);
    tl.set(row, { opacity: 1 }, ln.t);
    if (H.style === "roll") {
      const span = el("span", null, null, row), land = rollCells(span, ln.text, ln.t, j > 0);  // line 1 is landed on frame 0
      if (ln.hot) tl.fromTo(el("i", "bar", null, row), { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, ln.t + land);
    } else {
      const span = el("span", null, ln.text, row);
      if (ln.hot) tl.fromTo(el("i", "mk", null, span), { scaleX: 0 }, { scaleX: 1, duration: 0.22, ease: "power3.out" }, ln.t + 0.08);
      if (j) tl.fromTo(span, { yPercent: 115 }, { yPercent: 0, duration: 0.24, ease: "power4.out" }, ln.t);  // line 1 is up on frame 0
    }
  });
  tl.to(box, { y: -60, opacity: 0, duration: 0.16, ease: "power2.in" }, H.end - 0.16);
}

// captions: one phrase at a time, the spoken word lit in the accent colour
D.groups.forEach(function (g) {
  if (D.plain) {  // the whole phrase at once, small, regular font
    const p = el("div", "cap plain", g.w.map((k) => D.words[k][1]).join(" "), $("Lcap"));
    tl.fromTo(p, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.14, ease: "power2.out" }, g.s).set(p, { opacity: 0 }, g.e);
    return;
  }
  const box = el("div", "cap" + (g.kw != null ? " haskw" : ""), null, $("Lcap"));
  g.w.forEach(function (k, j) {
    el("span", k === g.kw ? "kw" : null, D.words[k][1], box).id = "w" + k;
    if (j + 1 < g.w.length) box.appendChild(document.createTextNode(" "));
  });
  tl.set(box, { opacity: 1 }, g.s).set(box, { opacity: 0 }, g.e);
  g.w.forEach(function (k, j) {
    const kw = k === g.kw, t0 = D.words[k][0], t2 = j + 1 < g.w.length ? D.words[g.w[j + 1]][0] : g.e;
    tl.fromTo("#w" + k, { opacity: 0, filter: kw ? "blur(24px)" : "blur(10px)", y: kw ? 0 : 10, scale: kw ? 1.25 : 1 },
      { opacity: 1, filter: "blur(0px)", y: 0, scale: 1, duration: kw ? 0.16 : 0.12, ease: "power3.out" }, t0);
    if (!kw && g.kw == null) tl.set("#w" + k, { color: D.acc }, t0).set("#w" + k, { color: "#fff" }, t2);
  });
});
D.kwt.forEach((t0) => tl.to("#bgw", { scale: 1.07, duration: 0.14, ease: "power3.out" }, t0).to("#bgw", { scale: 1, duration: 0.6, ease: "power2.inOut" }, t0 + 0.35));
tl.fromTo("#grain", { x: 0, y: 0 }, { x: 290, y: 170, duration: D.end, ease: "steps(" + Math.round(D.end * 12) + ")" }, 0);

// title cards: an accent line draws, the kicker slides in, the headline rises through a mask; it leaves upward
D.cards.forEach(function (c) {
  const b = el("div", "card p-" + c.p, '<div class="kk"><i></i><span>' + c.k + '</span></div><div class="tt"><span>' + c.t + "</span></div>", $("Lcard"));
  b.style.setProperty("--c", c.c);
  const dx = /r$/.test(c.p) ? 26 : c.p === "c" ? 0 : -26;
  const i = b.querySelector("i"), k = b.querySelector(".kk span"), t = b.querySelector(".tt span");
  tl.set(b, { opacity: 1 }, c.s)
    .fromTo(i, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, c.s)
    .fromTo(k, { opacity: 0, x: dx }, { opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }, c.s + 0.06)
    .fromTo(t, { opacity: 0, filter: "blur(18px)", scale: 1.06 }, { opacity: 1, filter: "blur(0px)", scale: 1, duration: 0.32, ease: "power3.out" }, c.s + 0.1)
    .to(t, { yPercent: -110, duration: 0.2, ease: "power2.in" }, c.e - 0.22)
    .to([k, i], { opacity: 0, duration: 0.15 }, c.e - 0.2).set(b, { opacity: 0 }, c.e);
});

D.st.forEach(function (s) {
  const e = $(s[0]);
  tl.fromTo(e, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.6)" }, s[1])
    .to(e, { y: -12, duration: 0.6, yoyo: true, repeat: 1, ease: "sine.inOut" }, s[1] + 0.3)
    .to(e, { opacity: 0, scale: 0.7, duration: 0.15 }, Math.max(s[1] + 0.35, s[2] - 0.12));
});
for (let k = 0; k < D.nlu; k++) {
  tl.fromTo("#lu" + k, { opacity: 0, y: 200 }, { opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)" }, D.cuts[D.cuts.length - 1] + 0.15 + k * 0.12);
}

function stamp(box, f) {
  const s = el("div", "stamp", f.stamp + (f.stamp_sub ? "<small>" + f.stamp_sub + "</small>" : ""), box);
  tl.fromTo(s, { opacity: 0, scale: 2.4, rotation: -4 }, { opacity: 1, scale: 1, rotation: -12, duration: 0.16, ease: "power2.in" }, f.stamp_at)
    .fromTo(box, { scale: 1 }, { scale: 0.97, duration: 0.06, yoyo: true, repeat: 1 }, f.stamp_at + 0.16);
  if (f.sub_at) tl.fromTo(s.querySelector("small"), { opacity: 0 }, { opacity: 1, duration: 0.2 }, f.sub_at);
}
function dropIn(box, f, rot) {
  tl.set(box, { opacity: 1 }, f.s)
    .fromTo(box, { y: -1300, rotation: rot - 11 }, { y: 0, rotation: rot, duration: 0.5, ease: "power3.out" }, f.s)
    .to(box, { y: 1500, rotation: rot + 12, duration: 0.32, ease: "power2.in" }, f.e - 0.32).set(box, { opacity: 0 }, f.e);
}
const FX = {
  // a wanted poster drops in and is nailed up; a second one with "stamp" lands a red verdict on the same poster
  poster: function (f) {
    const p = el("div", "poster", '<i class="nail"></i><div class="p1">' + f.head + '</div><div class="rule"></div><div class="p2">' + f.title +
      '</div><div class="rule"></div><div class="p3">' + f.sub + '</div><div class="p4">' + (f.foot || "") + "</div>", $("Lfx"));
    dropIn(p, f, -3);
    if (f.stamp) stamp(p, f);
  },
  // an evaluation form slides up; the header types on, each row ticks or crosses on its word, then the stamp
  form: function (f) {
    const p = el("div", "form", '<div class="fh">' + f.head + '</div><div class="fs">' + f.sub + "</div>" + f.rows.map(function (r) {
      return '<div class="row"><span>' + r.label + '</span><b class="' + r.kind + '">' + r.value + '</b><svg viewBox="0 0 26 26"><path d="' +
        (r.kind === "ok" ? "M4 14 L10 20 L22 6" : "M5 5 L21 21 M21 5 L5 21") + '"/></svg></div>';
    }).join(""), $("Lfx"));
    tl.set(p, { opacity: 1 }, f.s)
      .fromTo(p, { y: 1100, rotation: 5 }, { y: 0, rotation: -2, duration: 0.45, ease: "power3.out" }, f.s)
      .fromTo(p.querySelector(".fh"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.5, ease: "steps(24)" }, f.s + 0.25)
      .to(p, { y: 1500, rotation: 8, duration: 0.32, ease: "power2.in" }, f.e - 0.32).set(p, { opacity: 0 }, f.e);
    p.querySelectorAll(".row").forEach(function (r, i) {
      const t = f.rows[i].t;
      tl.fromTo(r, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.25, ease: "power3.out" }, t)
        .fromTo(r.querySelector("b"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.3, ease: "steps(10)" }, t + 0.1)
        .fromTo(r.querySelector("path"), { strokeDashoffset: 60 }, { strokeDashoffset: 0, duration: 0.3, ease: "power2.out" }, t + 0.35);
    });
    stamp(p, f);
  },
  // a flight path draws from pin A to pin B with a plane riding the line
  route: function (f) {
    const [ax, ay, al, ak] = f.a, [bx, by, bl, bk] = f.b, [cx, cy] = f.c, d = "M" + ax + " " + ay + " Q" + cx + " " + cy + " " + bx + " " + by;
    const pin = (x, y, l, k, id) => '<g id="' + id + '"><circle cx="' + x + '" cy="' + y + '" r="20" fill="var(--acc)" stroke="#000" stroke-width="6"/>' +
      '<text class="kt" x="' + x + '" y="' + (y - 132) + '" text-anchor="middle">' + k + '</text><text x="' + x + '" y="' + (y - 40) + '" text-anchor="middle" font-size="76">' + l + "</text></g>";
    const box = el("div", "route", '<svg width="1080" height="1920" viewBox="0 0 1080 1920"><path d="' + d + '" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="6" stroke-dasharray="4 18" stroke-linecap="round"/>' +
      '<path class="draw" d="' + d + '" fill="none" stroke="var(--acc)" stroke-width="12" stroke-linecap="round"/>' + pin(ax, ay, al, ak, "pa") + pin(bx, by, bl, bk, "pb") + "</svg>", $("Lfx"));
    const plane = el("div", "plane", '<svg viewBox="0 0 26 26" width="80" height="80"><path fill="#fff" stroke="#000" stroke-width="1" d="M2 13 L9 11 L13 2 L16 2 L14 11 L21 11 L23 7.5 L25 7.5 L24 13 L25 18.5 L23 18.5 L21 15 L14 15 L16 24 L13 24 L9 15 Z"/></svg>', box);
    const draw = box.querySelector(".draw"), len = draw.getTotalLength(), t0 = f.s + 0.2, dur = Math.min(1.4, (f.e - f.s) * 0.5);
    draw.style.strokeDasharray = len;
    tl.set(box, { opacity: 1 }, f.s)
      .fromTo("#pa", { scale: 0, transformOrigin: ax + "px " + ay + "px" }, { scale: 1, duration: 0.3, ease: "back.out(1.6)" }, f.s)
      .fromTo(draw, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease: "power2.inOut" }, t0)
      .fromTo("#pb", { scale: 0, transformOrigin: bx + "px " + by + "px" }, { scale: 1, duration: 0.3, ease: "back.out(1.6)" }, t0 + dur - 0.05)
      .set(plane, { opacity: 1 }, t0).set(plane, { opacity: 0 }, t0 + dur).to(box, { opacity: 0, duration: 0.2 }, f.e - 0.2);
    const N = 16, ease = (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);  // same curve as power2.inOut
    const pt = (u) => [(1 - u) * (1 - u) * ax + 2 * u * (1 - u) * cx + u * u * bx, (1 - u) * (1 - u) * ay + 2 * u * (1 - u) * cy + u * u * by];
    for (let q = 0; q <= N; q++) {
      const u = ease(q / N), [x, y] = pt(u), [x2, y2] = pt(Math.min(u + 0.01, 1)), [x1, y1] = pt(Math.max(u - 0.01, 0));
      const rot = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
      if (q === 0) tl.set(plane, { x: x, y: y, rotation: rot }, t0);
      else tl.to(plane, { x: x, y: y, rotation: rot, duration: dur / N, ease: "none" }, t0 + (q - 1) * dur / N);
    }
  },
  // a number ladder rolls (1x .. 10x) under a kicker; placed like a title card
  count: function (f) {
    const b = el("div", "fxbox p-" + (f.place || "c"), '<div class="kk"><i></i><span>' + f.kicker + '</span></div><div class="cnt"><span class="ladder">' +
      f.values.join("<br>") + "</span></div>" + (f.sub ? '<div class="sub">' + f.sub + "</div>" : ""), $("Lfx"));
    const n = f.values.length, t0 = f.roll_at || f.s + 0.2, d = f.roll || 1.3;
    tl.set(b, { opacity: 1 }, f.s)
      .fromTo(b.querySelector("i"), { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, f.s)
      .fromTo(b.querySelector(".cnt"), { yPercent: 40, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.3, ease: "power4.out" }, f.s + 0.05)
      .fromTo(b.querySelector(".ladder"), { yPercent: 0 }, { yPercent: -100 * (n - 1) / n, duration: d, ease: "power2.inOut" }, t0)
      .fromTo(b.querySelector(".cnt"), { scale: 1 }, { scale: 1.12, duration: 0.1, yoyo: true, repeat: 1 }, t0 + d)
      .to(b, { opacity: 0, y: -40, duration: 0.2, ease: "power2.in" }, f.e - 0.2);
  },
  // a grid of doors swings open in a diagonal wave, warm light behind each ("interiors")
  doors: function (f) {
    const cols = f.cols || 6, rows = f.nrows || 3, b = el("div", "doors", null, $("Lfx"));
    b.style.gridTemplateColumns = "repeat(" + cols + ", 1fr)";
    if (f.top) b.style.top = f.top + "px";
    for (let q = 0; q < cols * rows; q++) el("div", "door", "<i></i>", b);
    tl.set(b, { opacity: 1 }, f.s).fromTo(b, { y: 60 }, { y: 0, duration: 0.3, ease: "power3.out" }, f.s);
    b.querySelectorAll(".door i").forEach((d, q) => tl.fromTo(d, { rotationY: 0 }, { rotationY: -80, duration: 0.4, ease: "power2.out" },
      (f.open_at || f.s + 0.3) + (Math.floor(q / cols) + (q % cols)) * 0.05));
    tl.to(b, { opacity: 0, duration: 0.2 }, f.e - 0.2);
  },
  // a point of light opens into an image (zoom through)
  light: function (f) {
    const b = el("div", "light", '<img src="assets/' + f.img + '"><i></i>', $("Lfx")), im = b.querySelector("img"), dot = b.querySelector("i");
    const x = f.x || 540, y = f.y || 760;
    dot.style.left = x + "px";
    dot.style.top = y + "px";
    tl.set(b, { opacity: 1 }, f.s)
      .fromTo(dot, { scale: 0 }, { scale: 1.4, duration: 0.25, ease: "power3.out" }, f.s)
      .fromTo(im, { clipPath: "circle(0px at " + x + "px " + y + "px)" }, { clipPath: "circle(1500px at " + x + "px " + y + "px)", duration: 0.7, ease: "power3.in" }, f.s + 0.2)
      .to(dot, { opacity: 0, duration: 0.2 }, f.s + 0.7)
      .fromTo(im, { scale: 1.18 }, { scale: 1.0, duration: Math.max(0.5, f.e - f.s - 0.2), ease: "power1.out" }, f.s + 0.2)
      .to(b, { opacity: 0, duration: 0.2 }, f.e - 0.2);
  },
  // big rolling number (a countdown) under a kicker
  flip: function (f) {
    const b = el("div", "fxbox flip p-" + (f.place || "c"), '<div class="kk"><i></i><span>' + f.kicker + '</span></div><div class="big"><span></span></div>', $("Lfx"));
    rollCells(b.querySelector(".big span"), f.text, f.s + 0.1, true);
    tl.set(b, { opacity: 1 }, f.s).fromTo(b.querySelector("i"), { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, f.s)
      .to(b, { opacity: 0, y: -40, duration: 0.2, ease: "power2.in" }, f.e - 0.2);
  },
  // a photo card with a gauge: the needle swings to the red zone, stink lines draw on and rise, a punch-in
  meter: function (f) {
    const arc = (a, b2) => {
      const pt = (d) => [200 - 160 * Math.cos(d * Math.PI / 180), 210 - 160 * Math.sin(d * Math.PI / 180)];
      const [x1, y1] = pt(a), [x2, y2] = pt(b2);
      return "M" + x1 + " " + y1 + " A160 160 0 0 1 " + x2 + " " + y2;
    };
    const z = f.zones || ["CLEAN", "OK", "FILTHY"];
    const b = el("div", "meter", '<img class="mimg" src="assets/' + f.img + '">' +
      '<svg class="gauge" viewBox="0 0 400 250"><path d="' + arc(0, 180) + '" fill="none" stroke="#151515" stroke-width="44"/>' +
      '<path d="' + arc(2, 58) + '" fill="none" stroke="#5fd068" stroke-width="30"/><path d="' + arc(62, 118) + '" fill="none" stroke="#ffd166" stroke-width="30"/>' +
      '<path d="' + arc(122, 178) + '" fill="none" stroke="' + D.hot + '" stroke-width="30"/>' +
      '<text x="30" y="245">' + z[0] + '</text><text x="200" y="28" text-anchor="middle">' + z[1] + '</text><text x="370" y="245" text-anchor="end">' + z[2] + "</text>" +
      '<g class="needle"><path d="M193 210 L200 64 L207 210 Z" fill="#fff"/><circle cx="200" cy="210" r="15" fill="#fff"/></g></svg>' +
      '<svg class="stink" viewBox="0 0 420 420">' + [0, 1, 2].map((q) => {
        const x = 90 + q * 120;
        return '<path d="M' + x + " 400 C " + (x - 50) + " 330, " + (x + 50) + " 280, " + x + " 210 S " + (x - 50) + " 90, " + x + ' 20"/>';
      }).join("") + "</svg>", $("Lfx"));
    const nd = b.querySelector(".needle"), sw = f.swing_at || f.s + 1, st0 = f.stink_at || sw - 0.8;
    tl.set(b, { opacity: 1 }, f.s)
      .fromTo(b.querySelector(".mimg"), { y: 900, rotation: 6 }, { y: 0, rotation: -2, duration: 0.45, ease: "power3.out" }, f.s)
      .fromTo(b.querySelector(".gauge"), { scale: 0, rotation: -20, transformOrigin: "50% 80%" }, { scale: 1, rotation: 0, duration: 0.4, ease: "back.out(1.6)" }, f.s + 0.25)
      .fromTo(nd, { rotation: -84, svgOrigin: "200 210" }, { rotation: -60, duration: 0.3, ease: "power2.out", svgOrigin: "200 210" }, f.s + 0.4)
      .to(nd, { rotation: 74, duration: 0.55, ease: "back.out(2.2)", svgOrigin: "200 210" }, sw)
      .to(nd, { keyframes: [{ rotation: 66 }, { rotation: 78 }, { rotation: 70 }, { rotation: 75 }], duration: 0.8, svgOrigin: "200 210" }, sw + 0.55);
    b.querySelectorAll(".stink path").forEach((p, q) => {
      const L = p.getTotalLength();
      p.style.strokeDasharray = L;
      tl.fromTo(p, { strokeDashoffset: L, opacity: 1 }, { strokeDashoffset: 0, duration: 0.7, ease: "power2.out" }, st0 + q * 0.18)
        .to(p, { y: -60, opacity: 0.2, duration: 1.6, ease: "sine.inOut" }, st0 + 0.7 + q * 0.18);
    });
    if (f.punch_at) tl.fromTo(b.querySelector(".mimg"), { scale: 1 }, { scale: 1.08, duration: 0.12, ease: "power3.out" }, f.punch_at)
      .to(b.querySelector(".mimg"), { scale: 1, duration: 0.4, ease: "power2.out" }, f.punch_at + 0.12);
    tl.to(b, { opacity: 0, y: -60, duration: 0.25, ease: "power2.in" }, f.e - 0.25);
  },
  // a cyanotype system diagram: the header types on, box A draws, an arrow draws, box B draws, a note
  blueprint: function (f) {
    const b = el("div", "bp", '<div class="bph">' + f.title + '</div><svg viewBox="0 0 900 560"><rect class="r1" x="40" y="120" width="330" height="300" rx="8"/>' +
      '<path class="ar" d="M392 270 L522 270 M498 246 L522 270 L498 294"/><rect class="r2" x="540" y="90" width="320" height="360" rx="8"/></svg>' +
      '<div class="bx b1"><small>' + f.a[0] + "</small>" + f.a[1] + '</div><div class="bx b2"><small>' + f.b[0] + "</small>" + f.b[1] + '</div><div class="bpn">' + (f.note || "") + "</div>", $("Lfx"));
    const draw = (sel, t0, d) => {
      const e = b.querySelector(sel), L = e.getTotalLength();
      e.style.strokeDasharray = L;
      tl.fromTo(e, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: d, ease: "power2.inOut" }, t0);
    };
    const ta = f.a_at || f.s + 0.5, tb = f.b_at || ta + 1.5;
    tl.set(b, { opacity: 1 }, f.s)
      .fromTo(b, { y: 1100, rotation: 4 }, { y: 0, rotation: -1.5, duration: 0.45, ease: "power3.out" }, f.s)
      .fromTo(b.querySelector(".bph"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "steps(28)" }, f.s + 0.3);
    draw(".r1", ta, 0.5);
    tl.fromTo(b.querySelector(".b1"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.4, ease: "steps(12)" }, ta + 0.4);
    draw(".ar", tb - 0.4, 0.4);
    draw(".r2", tb, 0.5);
    tl.fromTo(b.querySelector(".b2"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.4, ease: "steps(12)" }, tb + 0.4)
      .fromTo(b.querySelector(".bpn"), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, f.note_at || tb + 0.9)
      .to(b, { y: 1500, rotation: 6, duration: 0.32, ease: "power2.in" }, f.e - 0.32).set(b, { opacity: 0 }, f.e);
  },
  // then vs now: two stacked panels slide in from opposite sides, the years roll, a thermometer drops in the top one
  split: function (f) {
    const half = (cls, h) => '<div class="half ' + cls + '"><img src="assets/' + h.img + '"><div class="lb">' + h.label + '</div><div class="yr"><span></span></div>' +
      (h.therm ? '<svg class="therm" viewBox="0 0 90 300"><rect x="30" y="10" width="30" height="230" rx="15" fill="rgba(255,255,255,.25)" stroke="#fff" stroke-width="5"/>' +
        '<circle cx="45" cy="255" r="32" fill="#4fc3ff" stroke="#fff" stroke-width="5"/><rect class="merc" x="37" y="30" width="16" height="220" rx="8" fill="#4fc3ff"/></svg>' : "") + "</div>";
    const b = el("div", "split", half("top", f.top) + half("bot", f.bot), $("Lfx")), tp = b.querySelector(".top"), bt = b.querySelector(".bot");
    tl.set(b, { opacity: 1 }, f.s)
      .fromTo(tp, { x: -1200 }, { x: 0, duration: 0.45, ease: "power3.out" }, f.s)
      .fromTo(bt, { x: 1200 }, { x: 0, duration: 0.45, ease: "power3.out" }, f.s + 0.15)
      .fromTo(b.querySelectorAll("img"), { scale: 1.15 }, { scale: 1, duration: f.e - f.s, ease: "none" }, f.s);
    rollCells(tp.querySelector(".yr span"), f.top.year, f.s + 0.35, true);
    rollCells(bt.querySelector(".yr span"), f.bot.year, f.s + 0.5, true);
    const m = b.querySelector(".merc");
    if (m) tl.fromTo(m, { scaleY: 1, transformOrigin: "50% 100%" }, { scaleY: 0.22, duration: 0.8, ease: "power2.inOut" }, f.cold_at || f.s + 1.5);
    tl.to(b, { opacity: 0, duration: 0.2 }, f.e - 0.2);
  },
  // two answer chips pop for the comment question
  vote: function (f) {
    const b = el("div", "vote", f.options.map((o, q) => '<div class="opt o' + q + '">' + o.text + "</div>").join(""), $("Lfx"));
    tl.set(b, { opacity: 1 }, f.s);
    b.querySelectorAll(".opt").forEach((o, q) => tl.fromTo(o, { opacity: 0, scale: 0.3, rotation: q ? 6 : -6 }, { opacity: 1, scale: 1, rotation: q ? 3 : -3, duration: 0.35, ease: "back.out(1.8)" }, f.options[q].t)
      .to(o, { scale: 1.06, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut" }, f.options[q].t + 0.5));
    tl.to(b, { opacity: 0, duration: 0.2 }, f.e - 0.2);
  },
  notify: function (f) {
    const b = el("div", "ntf glass", '<div class="hd"><div class="av">' + (f.icon || "!") + '</div><div class="ap"><b>' + f.app + "</b> · now</div></div>" +
      '<div class="tx">' + f.text + "</div>" + (f.reply ? '<div class="rp">&#8627; ' + f.reply + "</div>" : ""), $("Lfx"));
    if (f.top) b.style.top = f.top + "px";
    const n = f.text.length, td = Math.min(1.2, 0.045 * n);
    tl.fromTo(b, { opacity: 0, filter: "blur(18px)", y: -30, scale: 0.96 }, { opacity: 1, filter: "blur(0px)", y: 0, scale: 1, duration: 0.4, ease: "power3.out" }, f.s)
      .fromTo(b.querySelector(".tx"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: td, ease: "steps(" + n + ")" }, f.s + 0.35);
    if (f.reply) tl.fromTo(b.querySelector(".rp"), { opacity: 0, filter: "blur(10px)", y: 10 }, { opacity: 1, filter: "blur(0px)", y: 0, duration: 0.3 }, f.s + 0.5 + td);
    tl.to(b, { opacity: 0, filter: "blur(14px)", duration: 0.3, ease: "power2.in" }, f.e - 0.3);
  },
  comment: function (f) {
    const b = el("div", "cmt glass", '<div class="hd"><div class="av">' + (f.icon || "&#9733;") + '</div><div class="ap"><b>you</b> · now</div></div>' +
      '<div class="fl"><span class="ph">Add a comment...</span><span class="ty">' + f.text + '</span></div><div class="ok">&#10003; Posted</div>' +
      (f.sub ? '<div class="rp">' + f.sub + "</div>" : ""), $("Lfx"));
    if (f.top) b.style.top = f.top + "px";
    const n = f.text.length, td = Math.min(1.0, 0.06 * n), t1 = f.s + 0.45;
    tl.fromTo(b, { opacity: 0, filter: "blur(18px)", y: -30, scale: 0.96 }, { opacity: 1, filter: "blur(0px)", y: 0, scale: 1, duration: 0.4, ease: "power3.out" }, f.s)
      .set(b.querySelector(".ph"), { opacity: 0 }, t1)
      .fromTo(b.querySelector(".ty"), { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: td, ease: "steps(" + n + ")" }, t1)
      .fromTo(b.querySelector(".ok"), { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.25, ease: "back.out(2)" }, t1 + td + 0.2);
    if (f.sub) tl.fromTo(b.querySelector(".rp"), { opacity: 0, filter: "blur(10px)", y: 10 }, { opacity: 1, filter: "blur(0px)", y: 0, duration: 0.3 }, t1 + td + 0.5);
    tl.to(b, { opacity: 0, filter: "blur(14px)", duration: 0.3, ease: "power2.in" }, f.e - 0.3);
  },
  // HUD callout: a red circle draws around a point, an arrow draws towards it, an optional label
  callout: function (f) {
    const [x, y, r] = f.at_xy, [ax, ay] = f.from || [x + r + 160, y + r + 160], lb = f.label || "";
    const b = el("div", "callout", '<svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0;fill:none;stroke:#ff2d2d;stroke-width:10;stroke-linecap:round;filter:drop-shadow(0 3px 8px rgba(0,0,0,.7))">' +
      '<ellipse class="cr" cx="' + x + '" cy="' + y + '" rx="' + r + '" ry="' + r * 0.8 + '"/><path class="aw" d="M' + ax + " " + ay + " Q" + (ax - 20) + " " + (y + 10) + " " + (x + r * 0.9) + " " + (y + r * 0.6) + '"/>' +
      '<path class="ah" d="M' + (x + r * 0.9 + 34) + " " + (y + r * 0.6 + 4) + " L" + (x + r * 0.9) + " " + (y + r * 0.6) + " L" + (x + r * 0.9 + 12) + " " + (y + r * 0.6 + 34) + '"/></svg>' +
      (lb ? '<div class="clb" style="position:absolute;left:' + (ax - 160) + "px;top:" + (ay + 14) + 'px;font-family:Anton;font-size:56px;color:#fff;text-shadow:0 0 6px #000,0 4px 12px #000">' + lb + "</div>" : ""), $("Lfx"));
    b.style.cssText = "position:absolute;inset:0;opacity:0";
    tl.set(b, { opacity: 1 }, f.s);
    b.querySelectorAll("ellipse, path").forEach((p, q) => {
      const L = p.getTotalLength();
      p.style.strokeDasharray = L;
      tl.fromTo(p, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: q ? 0.25 : 0.35, ease: "power2.out" }, f.s + (q ? 0.3 + q * 0.12 : 0));
    });
    if (lb) tl.fromTo(b.querySelector(".clb"), { opacity: 0, filter: "blur(12px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.25 }, f.s + 0.55);
    tl.to(b, { opacity: 0, duration: 0.2 }, f.e - 0.2);
  },
  // lights go down to a spotlight on the caption (a whispered aside)
  iris: function (f) {
    const d = el("div", "iris", null, $("Lfx"));
    tl.set(d, { opacity: 1 }, f.s).fromTo(d, { "--r": "1300px" }, { "--r": "330px", duration: 0.55, ease: "power3.out" }, f.s)
      .to(d, { "--r": "1400px", duration: 0.3, ease: "power2.in" }, f.e - 0.3).set(d, { opacity: 0 }, f.e);
  },
};
D.fx.forEach((f) => FX[f.kind](f));
D.dims.forEach((d) => tl.to("#dim", { opacity: d[2], duration: 0.25 }, d[0]).to("#dim", { opacity: 0, duration: 0.25 }, d[1] - 0.25));

// end card: the question stays up, the channel row and a subscribe button arrive, a cursor clicks it, the bell rings
if (D.endcard) {
  const E = D.endcard, T = D.talk;
  const box = el("div", "endc", '<div class="dim"></div><div class="eq">' + E.question + '</div><div class="sub"><img src="assets/st/avatar.jpg"><div class="nm">' + E.channel +
    "<small>" + (E.tagline || "") + '</small></div></div><div class="btn"><span class="b1">SUBSCRIBE</span><span class="b2">SUBSCRIBED</span></div>' +
    '<svg class="bell" viewBox="0 0 24 24"><path d="M12 2a6 6 0 0 0-6 6v4l-2 3h16l-2-3V8a6 6 0 0 0-6-6zm-2.4 15a2.4 2.4 0 0 0 4.8 0z"/></svg>' +
    '<svg class="cur" viewBox="0 0 24 24"><path fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="round" d="M4 2 L4 19 L8.4 14.8 L11.6 21.6 L14.6 20.2 L11.4 13.6 L17.6 13.6 Z"/></svg>', $("Lend"));
  const btn = box.querySelector(".btn"), cur = box.querySelector(".cur"), bell = box.querySelector(".bell");
  tl.set(box, { opacity: 1 }, T)
    .fromTo(box.querySelector(".dim"), { opacity: 0 }, { opacity: 1, duration: 0.35 }, T)
    .fromTo(box.querySelector(".eq"), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" }, T + 0.05)
    .fromTo(box.querySelector(".sub"), { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, T + 0.25)
    .fromTo(btn, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, T + 0.35)
    .fromTo(cur, { x: 420, y: 560, opacity: 0 }, { x: 0, y: 0, opacity: 1, duration: 0.55, ease: "power2.inOut" }, T + 0.7)
    .to(cur, { scale: 0.82, duration: 0.08, yoyo: true, repeat: 1 }, T + 1.3)
    .to(btn, { scale: 0.94, duration: 0.08, yoyo: true, repeat: 1 }, T + 1.3)
    .set(box.querySelector(".b1"), { opacity: 0 }, T + 1.36).set(box.querySelector(".b2"), { opacity: 1 }, T + 1.36)
    .to(btn, { backgroundColor: "#2e2e33", duration: 0.12 }, T + 1.36)
    .fromTo(bell, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.2, ease: "back.out(2)" }, T + 1.45)
    .to(bell, { keyframes: [{ rotation: 18 }, { rotation: -16 }, { rotation: 12 }, { rotation: -8 }, { rotation: 0 }], duration: 0.6, transformOrigin: "50% 10%" }, T + 1.5)
    .to(cur, { x: 300, y: 420, opacity: 0, duration: 0.5, ease: "power2.in" }, T + 1.8);
}
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
for key, val in {"__END__": str(END), "__BG__": bg_html, "__ST__": st_html, "__LU__": lu_html, "__TOP__": top_html, "__THREE_HEAD__": three_head,
                 "__THREE__": three_html, "__ACC__": ACC, "__HOT__": HOT, "__CTOP__": str(spec.get("card_top", 340 if spec.get("pill") else 250)), "__STROKE__": STROKE, "__LOOK__": LOOK_CSS, "__DATA__": json.dumps(data)}.items():
    page = page.replace(key, val)
(SCENE / "index.html").write_text(page, "utf8")
print("cuts", cuts, "talk", TALK, "end", END, "groups", len(groups), "sfx", len(sfx))
