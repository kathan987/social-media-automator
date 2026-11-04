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
  3. **Captions**: 1-3 word phrases, the spoken word lit in your `accent` colour; a pause of 0.3 s ends a phrase.
     `"keywords": [...]` makes one word per phrase giant, with a punch-in on the footage. `"captions": "plain"` shows
     small whole phrases (up to 6 words) in Poppins instead, for a quieter, film-like Short. `"nocap": [[from, to], ...]`
     drops captions while a graphic carries its own labels. **Title cards** for names and places
     (`html:<b>TITLE</b><span>KICKER</span>`): an accent line, a small kicker and a headline that un-blurs. No boxes.
     Cards rotate through five spots (`tl`, `tr`, `c`, `ml`, `mr`); `place:xx` in the card's css picks one.
  4. **2-3 motion-graphics modules, a different set each Short** (`fx`): `poster` (a wanted-style poster; add `stamp`
     to land a verdict on it later), `form` (an evaluation form that ticks or crosses rows, then stamps), `route` (a
     path drawing from pin to pin with a plane), `count` (a number ladder rolls), `flip` (a big departure-board number),
     `doors` (a grid of doors swings open), `light` (a point of light opens into an image), `meter` (a photo with a gauge),
     `blueprint` (box A -> arrow -> box B), `split` (then vs now panels), `vote` (two answer chips), `notify` (a phone
     notification types on), `comment` (a comment is typed and posted), `callout` (a red circle and arrow on a point),
     `iris` (lights down to a spotlight). Their fields are in the JS `FX` functions of the builder. Plus one Three.js
     element where it explains something (`timeline`, `jet`; add your own in `scenes/explainer-scene/assets/explain3d.js`;
     `"dim": 0.5` darkens the footage under it), at most 2 per Short.
  5. **End card** (`endcard`): 2.9 s after the last word, the question stays up, your channel row and a subscribe button
     appear, a cursor clicks it and the bell rings. Needs `assets/logo.jpg`.
  6. A name badge on top (`"badge": "NAME"`), or your logo (`"logo"`) with a label pill under it (`"pill"`); `"card_top"`
     moves the top title cards and the hook down. The builder writes a sound for every action into `mix.json`
     (files from `assets/sfx/`) and puts a voice boost (EQ + compression) on `vo.mp3`. Film grain and a vignette are always on.
  7. **Per cut** (the 4th item of a `cuts` entry): `offset`, `focus`, `bars`, `keep` as before, plus `fit` (the whole 16:9
     frame over a blurred fill, for wide subjects; 1.4 zooms in), `still` (freeze the frame at `offset`), `gamma` (lift a
     dark clip) and `gvol`. The clip is a name in `footage/clips/`, a file under `footage/`, or an absolute path.
  8. **Clip audio**: `"game_audio": 0.35` mixes every clip's own sound (punches, shots, ambience) under the voice;
     `gvol` per cut overrides it (0 = silent). The stretches are cut to `projects/<slug>/game/` and added to `mix.json`.
  9. **Look** (`"look": "rdr"`): a named entry in `LOOK_CSS` in the builder that swaps the display font and palette
     (`rdr`: a western display font, white and red only; put `ChineseRocks-Regular.otf` in `assets/fonts/`). Add your
     own entry for your niche.
- Beats: the claim (0-2 s) -> 3-5 beats of proof -> the turning point -> one personal question.
- **30-45 s**, 75-125 spoken words. Run one character for five Shorts in a row before switching.
- Titles: "The real reason ...", "The ONLY ...", "Hidden ...". Facts only, two sources.

## 5. Film story (your own gameplay told like a short film)
For a recording with real dialogue (calls, cutscenes, NPC reactions). `tools/film_short.py projects/<slug>/film.json`.
- **50-65 s.** The NPC lines carry it; 3-5 short voice lines at most. Act 1 light and funny, a turn, then emotion.
- Square film window, serif subtitles keyed to source seconds, chapter lines, a call log or tally if the story has one,
  a black end card with the payoff line and a soft replay of the key line.
- Music follows the acts (playful -> slow piano, or a short rock burst on the turn). Make a `"version": "b"` to compare.
- Example and lessons: `docs/insights.md` section 4.

## 6. Painted explainer beats (inside any explainer)
p5.brush paintings for moments the footage does not have (a cutscene you did not record, a childhood, a diagnosis).
`scenes/brush-explainers`: write one shot function per beat in `src/scenes/`, check with `npm run brush-sheet`, render
with `npm run brush-render`, then cut `out/beats.mp4` into the spec by offset. Paint still lifes, landscapes, silhouettes
and light, never cartoon people; cut story b-roll between beats. Rules and the brush table: `docs/insights.md` 1-2.
A real character line can open the voice track: `tools/vo_parts.py` (section 3 of the insights).

## Add your own
Copy a section, name the type, give it a quota in `config.json`, and write its beats and length here.
