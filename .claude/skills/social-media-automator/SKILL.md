---
name: social-media-automator
description: >-
  Make a finished vertical Short or Reel end to end: find what is working, research two-source facts, score hooks,
  script, voice with word timings, build a HyperFrames scene with stickers and a Three.js element over your own
  footage, review, mix, thumbnail and upload text. Use when the user says "make a short", "make an explainer",
  "next video", "generate both shorts", gives a topic or a character, or asks to run the channel workflow.
---

# social-media-automator

Read `docs/rules.md` first: its rules win. Then follow these steps and say which one you are on.

## 1. Pick what to make
- No topic given: `python tools/find_outliers.py <3-10 niche hashtags>` and read `research/outliers-<date>.json`
  (rank by `multiple`, not views). Propose three ideas, each in one line with the format it fits (`docs/formats.md`).
- Series: take the next unmade question in `docs/topics.md`.

## 2. Facts
Find two reliable sources for every claim (Firecrawl search first, scrape only when the excerpt is not enough; stay in
the budget). Write `projects/<slug>/research.md`: each claim, its two URLs, then the credits used. Write `meta.json`:
`{"topic", "type", "game", "created": "YYYY-MM-DD"}`.

## 3. Hooks and script
Write five hooks from the yt-script formulas, run `hookscore.py`, show the best two with scores. Write the script on the
winner in the length of its format (`config.json`), mood tags like `[serious]` allowed, ending on one personal question.
Run `/ig-human` on it. Save `projects/<slug>/script.txt`.

## 4. Voice
`python tools/vo_elevenlabs.py <slug> projects/<slug>/script.txt 1.1` (or the free `tools/vo_edge.py`). Check the
duration fits the format. Read `words.json` to place every cut and sticker on a word.

## 5. Scene
- Pick the footage: the real moment that proves the claim first, then one clip per beat. Extract stills at the planned
  offsets and look at them: no menus, weapon wheels, cut-off subtitles or black bars.
- Copy `templates/example-explainer/spec.json`, change the cuts (`[word, after_seconds, clip, {offset, focus, bars, keep}]`),
  stickers (`[id, "st/x.png" | "html:<b>BIG</b><span>small</span>", startRef, endRef, css]`), `badge` and `three`.
- `python tools/sticker_short.py projects/<slug>/spec.json`
- `npx hyperframes render scenes/<scene> --output scenes/<scene>/out.mp4`

## 6. Review and fix
`ffmpeg -i scenes/<scene>/out.mp4 -vf "fps=0.5,scale=216:-2,tile=9x2" -frames:v 1 scenes/<scene>/review.jpg`, look at it,
fix the spec, rebuild, re-render. The first frame must be the strongest visual.

## 7. Mix and package
- `mix.json`: the render, a music bed (~0.14), the voice as the first sfx at 1.0, a boom at 0, whooshes on cuts, hits on
  sticker chips. `python tools/mix.py projects/<slug>/mix.json` -> `final.mp4` at -14 LUFS.
- `/yt-package` for the title + thumbnail words, `/yt-seo` for the description with every source link.
- `thumb.json` then `python tools/thumbnail.py <slug>`. Write `upload.json` (title, description, tags, pinned, notes).

## 8. Hand off
Give the owner `final.mp4`, both thumbnails and `upload.json`, plus what was not verified. Remind them to upload as private
+ scheduled and to tick "altered or synthetic content" for AI voice or images. Never upload yourself.
