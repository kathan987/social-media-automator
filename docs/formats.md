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
  1. Your footage of that character's game, full screen, cut on chosen words, never paused.
  2. Stickers popping in on their nouns: cut-out character art, a photo card from your own footage, text chips.
  3. One Three.js element where it explains something (`timeline` for an order of events, `jet` for a vehicle; add your
     own kinds in `scenes/explainer-scene/assets/explain3d.js`). At most 2 Three.js moments per Short.
  4. A name badge on top (`"badge": "NAME"`), one big caption word at a time.
- Beats: the claim (0-2 s) -> 3-5 beats of proof -> the turning point -> one personal question.
- **30-45 s**, 75-125 spoken words. Run one character for five Shorts in a row before switching.
- Titles: "The real reason ...", "The ONLY ...", "Hidden ...". Facts only, two sources.

## Add your own
Copy a section, name the type, give it a quota in `config.json`, and write its beats and length here.
