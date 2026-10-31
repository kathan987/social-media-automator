# Formats

Every brief names one format. Weekly quotas live in `config.json` (`weekly_targets`).

## 1. News
- What changed, stated as the first words. Beats: hook (what changed) -> what we actually know -> what it means -> what
  is still unconfirmed -> one question.
- Visuals: official images / trailer frames with slow push-ins, your gameplay underneath, a countdown badge if a launch is near.
- 20-30 s. Two sources per claim.

## 2. Did you know
- ONE surprising, specific, verified fact as a bold claim in the first sentence. Proof on screen at once (a side-by-side,
  a zoom on the exact frame). Then why it matters or the twist, then one question ("Did you notice this?").
- 20-30 s. A new visual every 1.5-3 s.

## 3. What if
- A funny hypothetical said out loud as "what if", so nobody takes it as news. One joke, escalated three times, a twist,
  a comment question. Real details inside it still follow the two-source rule.
- 20-30 s. AI stills allowed for the imagined scenes, labelled as illustrations.

## 4. Explainer (one question about one character, the series format)
- **One self-contained claim about one character per Short**, phrased as a curiosity gap: "The real reason ...",
  "The ONLY ...", "Hidden ...", or a number of details. Never a life summary and never "Part N". The backlog of
  questions, in story order, lives in `topics.md`.
- **Open on the real moment**: a cutscene or gameplay clip from your own recording that proves the claim, at 0.0 s.
- **Scene recipe** (one HyperFrames composition, built by `tools/sticker_short.py`):
  1. **Hook** (`hook`, 0 s to the second cut): the hook line as kinetic type, line 1 already on frame 0. `"slam"` lines
     rise through a mask with a marker swipe on the key line; `"roll"` letters spin like a departure board.
  2. Your footage of that character's game, full screen, cut on chosen words, never paused.
  3. **Captions**: 1-3 word phrases, the spoken word lit in your `accent` colour. **Title cards** for names and places
     (`html:<b>TITLE</b><span>KICKER</span>`): an accent line, a small kicker and a headline rising through a mask. No boxes.
  4. **2-3 motion-graphics modules, a different set each Short** (`fx`): `poster` (a wanted-style poster; add `stamp`
     to land a verdict on it later), `form` (an evaluation form that ticks or crosses rows, then stamps), `route` (a
     path drawing from pin to pin with a plane), `iris` (lights down to a spotlight). Plus one Three.js element where it
     explains something (`timeline`, `jet`; add your own in `scenes/explainer-scene/assets/explain3d.js`), at most 2 per Short.
  5. **End card** (`endcard`): 2.9 s after the last word, the question stays up, your channel row and a subscribe button
     appear, a cursor clicks it and the bell rings. Needs `assets/logo.jpg`.
  6. A name badge on top (`"badge": "NAME"`). The builder writes a sound for every action into `mix.json`.
- Beats: the claim (0-2 s) -> 3-5 beats of proof -> the turning point -> one personal question.
- **30-45 s**, 75-125 spoken words. Run one character for five Shorts in a row before switching.
- Titles: "The real reason ...", "The ONLY ...", "Hidden ...". Facts only, two sources.

## Add your own
Copy a section, name the type, give it a quota in `config.json`, and write its beats and length here.
