"""Sticker-style Short builder: a logo or name badge fixed on top, one big word at a time, your footage full screen cut
on chosen words (punch-zoom + shake + flash), cut-out stickers popping on their nouns, an optional Three.js layer and
an optional end line-up. Timed to the voiceover's words.json.
  python tools/sticker_short.py projects/<slug>/spec.json
spec: {"slug": "...", "scene": "<scenes/ folder>", "template": "explainer-scene", "logo": "st/logo.png" | "badge": "NAME",
       "three": [{"kind": "timeline" | "jet", "start": ["word", after], "end": ["word", after], "labels": ["TOP|BOTTOM|#hex"]}],
       "cuts": [["word", after_seconds, "clip-name"], ...],            first cut starts at 0
       "stickers": [["id", "st/x.png" | "html:<b>..</b>", ["word", after], ["word", after] | "end", "css"], ...],
       "lineup": ["st/a.png", ...]  (optional: all stickers in a row from the last cut)}
Writes <scene>/index.html (clips cut to <scene>/assets/bgN.mp4) and videos/<slug>/cues.json."""
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
words = json.loads((SLUG / "words.json").read_text("utf8"))
END = round(words[-1]["end"] + 1.0, 2)


def at(ref):
    if ref == "end":
        return END
    token, after = ref
    return round(next(w["start"] for w in words if re.sub(r"[^a-z0-9]", "", w["text"].lower()) == token and w["start"] >= after), 2)


if spec.get("template") and not SCENE.exists():  # start a new scene from scenes/<template> (run tools/setup_scene.py first)
    shutil.copytree(SCENE.parent / spec["template"], SCENE, ignore=shutil.ignore_patterns("index.html", "selftest*", ".hyperframes", "*.mp4"))
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
st = [(sid, src, at(a), at(b), css) for sid, src, a, b, css in spec["stickers"]]
lineup = spec.get("lineup") or []
(SLUG / "cues.json").write_text(json.dumps({"cuts": cuts, "stickers": {s[0]: s[2] for s in st}, "end": END}, indent=1), "utf8")

bg_html = "\n".join('  <video id="bg%d" class="clip bg" src="assets/bg%d.mp4" muted playsinline data-start="%s" data-duration="%s" data-track-index="0"></video>'
                    % (i, i, s, round(e - s, 2)) for i, (s, e) in enumerate(segs))
st_html = "\n".join(('    <img class="st" id="%s" src="assets/%s" style="%s">' % (i, f, css)) if not f.startswith("html:")
                    else ('    <div class="st chip" id="%s" style="%s">%s</div>' % (i, css, f[5:])) for i, f, _, _, css in st)
lu_w = int(1040 / max(len(lineup), 1))
lu_html = "\n".join('    <img class="lu" id="lu%d" src="assets/%s" style="left:%dpx;width:%dpx">' % (k, f, int(20 + k * lu_w - lu_w * 0.45), int(lu_w * 1.9))
                   for k, f in enumerate(lineup))  # overlapping group shot: each sticker ~2x its slot
cap_html = "\n".join('    <div class="w" id="w%d">%s</div>' % (k, re.sub(r"[^\w'?!,.-]", "", w["text"]).upper()) for k, w in enumerate(words))
# a name pill instead of a logo, and an optional Three.js layer (assets/explain3d.js, drawn from HyperFrames' hf-seek time)
top_html = ('<div id="badge">%s</div>' % spec["badge"]) if spec.get("badge") else '<img id="logo" src="assets/%s">' % spec.get("logo", "st/logo.png")
three = [{**t, "start": at(t["start"]), "end": at(t["end"])} for t in spec.get("three", [])]
three_head = ("<script>window.__three = %s; window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};"
              " window.__hf.buildReady.three = new Promise(function (r) { window.__threeReady = r; });</script>\n"
              '<script type="module" src="assets/explain3d.js"></script>' % json.dumps(three)) if three else ""
three_html = '    <canvas id="three" width="1080" height="1920"></canvas>' if three else ""
page = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<script src="assets/gsap.min.js"></script>
<!-- Generated by tools/sticker_short.py -->
<style>
@font-face{font-family:"Bebas";src:url("assets/fonts/BebasNeue-Regular.ttf")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:"Bebas",sans-serif}
.bg{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover}
#ui{position:absolute;inset:0}
#logo{position:absolute;left:50%%;top:40px;width:430px;margin-left:-215px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))}
.w{position:absolute;left:0;right:0;top:640px;text-align:center;font-size:150px;line-height:1;color:#efefef;letter-spacing:.02em;text-shadow:0 6px 18px rgba(0,0,0,.75),0 2px 2px #000;opacity:0}
.st{position:absolute;opacity:0;filter:drop-shadow(0 12px 18px rgba(0,0,0,.6))}
.chip{text-align:center;background:#fff;color:#111;border-radius:26px;border:8px solid #ff4fa3;padding:14px 0}
.chip b{display:block;font-size:150px;line-height:1;font-weight:400}.chip span{display:block;font-size:56px;color:#ff4fa3}
.lu{position:absolute;bottom:110px;height:900px;object-fit:contain;object-position:50%% 100%%;opacity:0;filter:drop-shadow(0 10px 14px rgba(0,0,0,.6))}
#flash{position:absolute;inset:0;background:#fff;opacity:0}
#badge{position:absolute;left:50%%;top:48px;transform:translateX(-50%%);padding:10px 34px;border-radius:40px;background:#c1121f;color:#fff;font-size:64px;letter-spacing:.06em;white-space:nowrap;box-shadow:0 8px 20px rgba(0,0,0,.55)}
#three{position:absolute;inset:0;width:1080px;height:1920px}
</style>
%(THREE_HEAD)s
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="%(END)s" data-width="1080" data-height="1920">
%(BG)s
  <div id="ui" class="clip" data-start="0" data-duration="%(END)s" data-track-index="1" data-layout-allow-overlap data-layout-allow-overflow>
%(THREE)s
%(ST)s
%(LU)s
%(CAP)s
    %(TOP)s
    <div id="flash"></div>
  </div>
</div>
<script>
const W = %(W)s, CUTS = %(CUTS)s, ST = %(STJ)s, END = %(END)s, NLU = %(NLU)s;
const tl = gsap.timeline({ paused: true });
W.forEach(function (w, k) {
  const el = document.getElementById("w" + k), off = k + 1 < W.length ? W[k + 1][0] : END - 0.3;
  tl.set(el, { opacity: 1 }, w[0]).fromTo(el, { scale: 1.18 }, { scale: 1, duration: 0.1, ease: "power2.out" }, w[0]).set(el, { opacity: 0 }, off);
});
CUTS.forEach(function (c, i) {
  const el = document.getElementById("bg" + i), nx = i + 1 < CUTS.length ? CUTS[i + 1] : END;
  tl.fromTo(el, { scale: 1.12 }, { scale: 1.0, duration: 0.25, ease: "power3.out" }, c)
    .to(el, { scale: 1.06, duration: Math.max(0.3, nx - c - 0.25), ease: "none" }, c + 0.25);
  if (i > 0) tl.to("#flash", { opacity: 0.55, duration: 0.04 }, c).to("#flash", { opacity: 0, duration: 0.18 }, c + 0.04)
    .to("#ui", { x: 16, duration: 0.035, yoyo: true, repeat: 5 }, c);
});
ST.forEach(function (s) {
  const el = document.getElementById(s[0]);
  tl.fromTo(el, { opacity: 0, scale: 0.2, rotation: -10 }, { opacity: 1, scale: 1, rotation: s[3], duration: 0.3, ease: "back.out(2.4)" }, s[1])
    .to(el, { y: -12, duration: 0.6, yoyo: true, repeat: 1, ease: "sine.inOut" }, s[1] + 0.3)
    .to(el, { opacity: 0, scale: 0.6, duration: 0.15 }, Math.max(s[1] + 0.35, s[2] - 0.12));
});
for (let k = 0; k < NLU; k++) {
  tl.fromTo("#lu" + k, { opacity: 0, y: 200 }, { opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)" }, CUTS[CUTS.length - 1] + 0.15 + k * 0.12);
}
window.__timelines["main"] = tl;
</script>
</body>
</html>
""" % {"END": END, "BG": bg_html, "ST": st_html, "LU": lu_html, "CAP": cap_html, "TOP": top_html,
       "THREE_HEAD": three_head, "THREE": three_html,
       "W": json.dumps([[round(w["start"], 2)] for w in words]), "CUTS": json.dumps(cuts), "NLU": len(lineup),
       "STJ": json.dumps([[s[0], s[2], s[3], -4 if s[0].startswith("c") else 0] for s in st])}
(SCENE / "index.html").write_text(page, "utf8")
print("cuts", cuts, "end", END)
