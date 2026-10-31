"""Sticker-style Short builder: the owner's gameplay full screen, cut on chosen words, with phrase captions (active word
lit), title cards (kicker + headline through a mask), a trending hook, motion-graphics modules and a subscribe end card.
  python tools/sticker_short.py projects/<slug>/spec.json
spec: {"slug": "...", "scene": "<scenes/ folder>", "template": "explainer-scene", "badge": "NAME" | "logo": "st/x.png",
       "accent": "#ffdd00" (captions, cards), "hot": "#ff3b30" (hook mark, stamps),
       "cuts": [["word", after_seconds, "clip", {offset, focus, bars, keep}], ...],   first cut starts at 0
       "stickers": [["id", "st/x.png" | "html:<b>TITLE</b><span>KICKER</span>", ["word", after], ["word", after] | "end", "css"], ...],
       "hook": {"style": "slam" | "roll", "lines": [["word", after, "TEXT", hot?], ...]}   runs until the second cut,
       "fx": [{"kind": "poster" | "form" | "route" | "iris", "start": [...], "end": [...], ...}],  see the JS fx* functions,
       "three": [{"kind": "timeline" | "jet", "start": [...], "end": [...], "labels": ["KICKER|TITLE|#hex"]}],
       "endcard": {"question": "...", "channel": "...", "tagline": "...", "seconds": 2.9},
       "lineup": ["st/a.png", ...]}
Writes <scene>/index.html (clips cut to <scene>/assets/bgN.mp4), projects/<slug>/cues.json and the sfx in projects/<slug>/mix.json."""
import json
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
(A / "fonts").mkdir(parents=True, exist_ok=True)
for f in [LIB / "fonts/Anton-Regular.ttf", LIB / "fonts/Poppins-SemiBold.ttf", LIB / "fonts/BebasNeue-Regular.ttf",
          LIB / "fonts/georgiab.ttf", LIB / "fonts/consolab.ttf"]:  # the last two are optional (poster serif, form typewriter)
    if f.exists() and not (A / "fonts" / f.name).exists():
        shutil.copy(f, A / "fonts")
if ENDC and (LIB / "logo.jpg").exists() and not (A / "st" / "avatar.jpg").exists():  # your channel logo
    (A / "st").mkdir(exist_ok=True)
    shutil.copy(LIB / "logo.jpg", A / "st" / "avatar.jpg")

cuts = [0.0] + [at([t, a]) for t, a, *_ in spec["cuts"][1:]]
segs = [(cuts[i], cuts[i + 1] if i + 1 < len(cuts) else END) for i in range(len(cuts))]
for i, (cut, (s, e)) in enumerate(zip(spec["cuts"], segs)):
    # opt: offset (s), focus (0 left .. 1 right), bars (cinematic letterbox), keep [top, bottom] fractions (drops game subtitles)
    clip, opt = cut[2], (cut[3] if len(cut) > 3 else {})
    src = ROOT / "footage" / (clip if clip.endswith(".mp4") else f"clips/{clip}.mp4")
    keep = opt.get("keep") or ([0.125, 0.875] if opt.get("bars") else None)
    vf = (f"crop=iw:ih*{keep[1] - keep[0]}:0:ih*{keep[0]}," if keep else "") + f"scale=-2:1920,crop=1080:1920:(iw-1080)*{opt.get('focus', .5)}:0,fps=30"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-ss", str(opt.get("offset", 0)), "-i", str(src),
                    "-t", str(round(e - s + 0.2, 2)), "-an", "-vf", vf,
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", str(A / f"bg{i}.mp4")], check=True)

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
    if cur and len(" ".join(W[j][1] for j in cur + [k])) > 16:
        groups.append(cur)
        cur = []
    cur.append(k)
    if len(cur) == 3 or re.search(r"[.,?!]$", words[k]["text"]):
        groups.append(cur)
        cur = []
if cur:
    groups.append(cur)
groups = [{"w": g, "s": W[g[0]][0]} for g in groups]
for n, g in enumerate(groups):  # hold until the next phrase when the gap is short, else clear 0.3 s after the last word
    nxt = groups[n + 1]["s"] if n + 1 < len(groups) else None
    g["e"] = nxt if nxt and nxt - words[g["w"][-1]]["end"] < 0.6 else round(min(words[g["w"][-1]]["end"] + 0.3, TALK), 2)

cards, st = [], []
for sid, src, a, b, css in spec["stickers"]:
    if src.startswith("html:"):  # old chip markup -> title card: <b> is the headline, <span> the kicker
        m = re.search(r"<b>(.*?)</b>\s*<span>(.*?)</span>", src)
        col = re.search(r"border-color:\s*(#[0-9a-fA-F]+)", css)
        cards.append({"s": at(a), "e": at(b), "t": m[1], "k": m[2], "c": col[1] if col else ACC})
    else:
        st.append((sid, src, at(a), at(b), css))

fx = []
for f in spec.get("fx", []):
    f = {**f, "s": at(f["start"]), "e": at(f["end"])}
    for key in ("stamp_at", "sub_at"):
        if key in f:
            f[key] = at(f[key])
    for r in f.get("rows", []):
        r["t"] = at(r["at"])
    fx.append(f)
three = [{**t, "start": at(t["start"]), "end": at(t["end"])} for t in spec.get("three", [])]
lineup = spec.get("lineup") or []

# sound for every visible action (times match the tweens in the page script)
sfx = [(0.0, "boom")] + [(c, "whoosh") for c in cuts[1:]]
if hook:
    sfx += [(ln["t"], "hit") for ln in hook["lines"][1:]]
sfx += [(c["s"], "tick") for c in cards]
for f in fx:
    sfx.append((f["s"] + (0.2 if f["kind"] == "route" else 0), "whoosh" if f["kind"] != "iris" else "hit"))
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
mix_file = SLUG / "mix.json"
if mix_file.exists():  # keep the voice and music, replace the effects
    mix = json.loads(mix_file.read_text("utf8"))
    mix["sfx"] = [c for c in mix["sfx"] if c["file"].endswith("vo.mp3")] + [
        {"file": f"assets/sfx/{SFX[n][0]}", "at": t, "vol": SFX[n][1], **({"dur": SFX[n][2]} if SFX[n][2] else {})} for t, n in sfx if (LIB / "sfx" / SFX[n][0]).exists()]
    mix_file.write_text(json.dumps(mix, indent=1), "utf8")

STROKE = ",".join(f"{x}px {y}px 0 #000" for x, y in [(7, 0), (-7, 0), (0, 7), (0, -7), (5, 5), (-5, 5), (5, -5), (-5, -5)])
bg_html = "\n".join('  <video id="bg%d" class="clip bg" src="assets/bg%d.mp4" muted playsinline data-start="%s" data-duration="%s" data-track-index="0"></video>'
                    % (i, i, s, round(e - s, 2)) for i, (s, e) in enumerate(segs))
st_html = "\n".join('    <img class="st" id="%s" src="assets/%s" style="%s">' % (i, f, css) for i, f, _, _, css in st)
lu_w = int(1040 / max(len(lineup), 1))
lu_html = "\n".join('    <img class="lu" id="lu%d" src="assets/%s" style="left:%dpx;width:%dpx">' % (k, f, int(20 + k * lu_w - lu_w * 0.45), int(lu_w * 1.9))
                    for k, f in enumerate(lineup))  # overlapping group shot: each sticker ~2x its slot
top_html = ('<div id="badge"><i></i>%s<i></i></div>' % spec["badge"]) if spec.get("badge") else '<img id="logo" src="assets/%s">' % spec.get("logo", "st/logo.png")
three_head = ("<script>window.__three = %s; window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};"
              " window.__hf.buildReady.three = new Promise(function (r) { window.__threeReady = r; });</script>\n"
              '<script type="module" src="assets/explain3d.js"></script>' % json.dumps(three)) if three else ""
three_html = '    <canvas id="three" width="1080" height="1920"></canvas>' if three else ""
data = {"words": W, "groups": groups, "cuts": cuts, "end": END, "talk": TALK, "acc": ACC, "hot": HOT, "hook": hook, "cards": cards,
        "st": [[s[0], s[2], s[3]] for s in st], "fx": fx, "endcard": ENDC, "nlu": len(lineup)}
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
@font-face{font-family:"Serif",Georgia,serif;src:url("assets/fonts/georgiab.ttf")}
@font-face{font-family:"Mono",Consolas,monospace;src:url("assets/fonts/consolab.ttf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:"Anton",sans-serif;--acc:__ACC__;--hot:__HOT__}
.bg{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover}
#ui,.L{position:absolute;inset:0}
#scrim{position:absolute;inset:0;background:linear-gradient(rgba(0,0,0,.62),rgba(0,0,0,0) 34%,rgba(0,0,0,0) 52%,rgba(0,0,0,.5))}
#dim{position:absolute;inset:0;background:#05060a;opacity:0}
#logo{position:absolute;left:50%;top:40px;width:430px;margin-left:-215px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))}
#badge{position:absolute;left:0;right:0;top:118px;display:flex;justify-content:center;align-items:center;gap:22px;font-family:"Poppins";font-size:34px;letter-spacing:.32em;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.9);white-space:nowrap}
#badge i{display:block;width:64px;height:4px;background:var(--acc)}
.cap{position:absolute;left:70px;right:70px;top:1150px;text-align:center;font-size:106px;line-height:1.06;color:#fff;opacity:0;text-shadow:__STROKE__,0 14px 26px rgba(0,0,0,.6)}
.cap span{display:inline-block}
.card{position:absolute;left:80px;right:80px;top:250px;opacity:0}
.card .kk{display:flex;align-items:center;gap:20px;font-family:"Poppins";font-size:40px;letter-spacing:.2em;color:var(--c);text-shadow:0 2px 12px rgba(0,0,0,.9)}
.card .kk i{display:block;width:84px;height:8px;background:var(--c);transform-origin:0 50%}
.card .tt{overflow:hidden;padding:6px 0 12px}
.card .tt span{display:block;font-size:138px;line-height:1.02;color:#fff;text-shadow:0 8px 34px rgba(0,0,0,.7)}
.st{position:absolute;opacity:0;filter:drop-shadow(0 12px 18px rgba(0,0,0,.6))}
.lu{position:absolute;bottom:110px;height:900px;object-fit:contain;object-position:50% 100%;opacity:0;filter:drop-shadow(0 10px 14px rgba(0,0,0,.6))}
.hook{position:absolute;left:60px;right:60px;top:290px;text-align:center}
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
</style>
__THREE_HEAD__
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__END__" data-width="1080" data-height="1920">
__BG__
  <div id="ui" class="clip" data-start="0" data-duration="__END__" data-track-index="1" data-layout-allow-overlap data-layout-allow-overflow>
    <div id="scrim"></div>
    <div id="dim"></div>
__THREE__
    <div class="L" id="Lfx"></div>
__ST__
__LU__
    <div class="L" id="Lcard"></div>
    <div class="L" id="Lhook"></div>
    <div class="L" id="Lcap"></div>
    __TOP__
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

// hook: "slam" lines rise through a mask, the hot line gets a marker swipe; "roll" letters spin like a departure board
if (D.hook) {
  const H = D.hook, box = el("div", "hook " + H.style, null, $("Lhook"));
  let seed = 7;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280, AB = "BDGHJLMNPQRSTVWXZ0123456789";  // no vowels: a scramble never spells a word
  tl.set("#dim", { opacity: 0.3 }, 0).to("#dim", { opacity: 0, duration: 0.2 }, H.end - 0.12);
  H.lines.forEach(function (ln, j) {
    const row = el("div", "hl" + (ln.hot ? " hot" : ""), null, box);
    tl.set(row, { opacity: 1 }, ln.t);
    if (H.style === "roll") {
      const span = el("span", null, null, row);
      let ci = 0;
      for (const ch of ln.text) {
        if (ch === " ") { span.appendChild(document.createTextNode(" ")); continue; }
        const cell = el("span", "cell", null, span), n = 6 + Math.floor(rnd() * 5);
        el("span", "gh", ch, cell);
        let s = "";
        for (let q = 0; q < n; q++) s += AB[Math.floor(rnd() * AB.length)] + "<br>";
        const strip = el("span", "sp", s + ch, cell);
        if (j) tl.fromTo(strip, { yPercent: 0 }, { yPercent: -100 * n / (n + 1), duration: 0.45 + ci * 0.03, ease: "power3.out" }, ln.t);
        else gsap.set(strip, { yPercent: -100 * n / (n + 1) });  // line 1 is landed on frame 0 (the thumbnail frame)
        ci++;
      }
      if (ln.hot) tl.fromTo(el("i", "bar", null, row), { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, ln.t + 0.45 + ci * 0.03);
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
  const box = el("div", "cap", null, $("Lcap"));
  g.w.forEach(function (k, j) {
    el("span", null, D.words[k][1], box).id = "w" + k;
    if (j + 1 < g.w.length) box.appendChild(document.createTextNode(" "));
  });
  tl.set(box, { opacity: 1 }, g.s).fromTo(box, { scale: 0.86, y: 16 }, { scale: 1, y: 0, duration: 0.16, ease: "power3.out" }, g.s).set(box, { opacity: 0 }, g.e);
  g.w.forEach(function (k, j) {
    const t2 = j + 1 < g.w.length ? D.words[g.w[j + 1]][0] : g.e;
    tl.set("#w" + k, { color: D.acc, scale: 1.08 }, D.words[k][0]).set("#w" + k, { color: "#fff", scale: 1 }, t2);
  });
});

// title cards: an accent line draws, the kicker slides in, the headline rises through a mask; it leaves upward
D.cards.forEach(function (c) {
  const b = el("div", "card", '<div class="kk"><i></i><span>' + c.k + '</span></div><div class="tt"><span>' + c.t + "</span></div>", $("Lcard"));
  b.style.setProperty("--c", c.c);
  const i = b.querySelector("i"), k = b.querySelector(".kk span"), t = b.querySelector(".tt span");
  tl.set(b, { opacity: 1 }, c.s)
    .fromTo(i, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, c.s)
    .fromTo(k, { opacity: 0, x: -26 }, { opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }, c.s + 0.06)
    .fromTo(t, { yPercent: 110 }, { yPercent: 0, duration: 0.34, ease: "power4.out" }, c.s + 0.1)
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
  // lights go down to a spotlight on the caption (a whispered aside)
  iris: function (f) {
    const d = el("div", "iris", null, $("Lfx"));
    tl.set(d, { opacity: 1 }, f.s).fromTo(d, { "--r": "1300px" }, { "--r": "330px", duration: 0.55, ease: "power3.out" }, f.s)
      .to(d, { "--r": "1400px", duration: 0.3, ease: "power2.in" }, f.e - 0.3).set(d, { opacity: 0 }, f.e);
  },
};
D.fx.forEach((f) => FX[f.kind](f));

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
                 "__THREE__": three_html, "__ACC__": ACC, "__HOT__": HOT, "__STROKE__": STROKE, "__DATA__": json.dumps(data)}.items():
    page = page.replace(key, val)
(SCENE / "index.html").write_text(page, "utf8")
print("cuts", cuts, "talk", TALK, "end", END, "groups", len(groups), "sfx", len(sfx))
