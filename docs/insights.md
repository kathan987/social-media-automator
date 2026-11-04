# Insights from production (what worked, what the owner rejected, why)

Lessons from real Shorts, newest first. Read this before you plan a new format or change a style. Each section says what
the owner asked for, what we built, and the rule we keep.

## 1. Painted beats: subtle, never childish (2026-11-03)

**Owner, first version:** "the painted scenes are looking very childish make it subtle aesthetic and painted brush ...
add brolls as well ... the skills has too many brushes, so search and use according brush accordingly." The second
version was approved: "the style is nice", details still to improve.

What failed (v1): cartoon people with stick limbs and dot eyes, comic SFX words (POW, *COUGH*), a coin with a clover,
flat colour washes, and line "boil" on everything. It read as a kids' explainer under a cinematic voice.

What works (v2, `scenes/brush-explainers`):
- **Paint the story, not people.** Still lifes (a father's worn glove beside a child's), landscapes (a watchtower at
  dusk, a gate opening onto a sunrise), silhouettes (a rim-lit profile), documents (a ledger by candlelight, a journal
  page), anatomy (pencil lungs with spreading spots).
- **One brush per job** (p5.brush 3.0, `figures.js`):

  | Job | Brush |
  |---|---|
  | skies, walls, gloves, blood blooms | watercolour `fill` (bleed .2-.35, tex .5-.8, border .2-.7) over a flat `wash` |
  | smooth gradients | 36 thin flat strips with interpolated colours, then 3-4 loose watercolour passes for texture |
  | shadows, fence posts, smears, impact slashes | `charcoal`, custom `dry` |
  | sketch lines, anatomy, rib arcs, rim light | `HB`, `2H`, `2B`, `cpencil` |
  | chain-link, razor wire, ink writing, red underline | `rotring`, `pen` (hatch at +45 / -45 for mesh) |
  | the cough, dust | `spray` (mist), `glow()` motes |
  | pencil shading inside a shape | `hatch` with `HB`/`charcoal`, gradient .4-.6 |
- **Hold still.** Seed every static shape with `stillSeed(key)` (no boil), so a painting is calm; only what moves
  changes. Motion = a slow camera push (1.0 to 1.07), light breathing (candle, searchlight, sun glow), lines drawing on
  (`drawOn`), a gate swinging, a red bloom growing.
- **Dissolve, don't wipe.** Fade to and from a colour (`flash`) between beats; the comic brush-wipe was too loud.
- **Text in the painting** only when it is the story (a name in a ledger, the journal quote) and in a handwriting font
  (Caveat); move it clear of the caption band or turn captions off for that window (`nocap`).
- **Check, then render.** `npm run brush-sheet` (contact sheet), fix, then `npm run brush-render` (~40 ms a frame on a
  GPU; set `CHROME_PATH` or pass `--chrome=` to a Chrome / chrome-headless-shell). Keep the previous version for A/B.
- Still to improve (owner): more detail in the paintings (texture, foreground objects, more layered light).

## 2. Story b-roll between painted beats (2026-11-03)

Cut real b-roll on the exact word it illustrates, between painted beats: a boxer for "her father taught her to fight",
barbed wire on "Penitentiary", a barred window on "bad luck didn't put her in there", golden farmland on "a sick man who
can't pay", a pencil writing on "Arthur wrote it in his journal". Source: Pixabay (licence logged in `docs/assets.md`).
Check each clip on a strip of frames first: half of the results are off-topic (a tiger for "coin flip") or blurry at the
chosen offset. Credit "Stock b-roll: Pixabay" in the description.

## 3. Real character lines in the voice track (2026-11-03)

Open an explainer on the real moment: the trailer line "Lucia, do you know why you're here?" / "Bad luck, I guess."
`tools/vo_parts.py` joins Edge TTS parts and clips of real dialogue into one `vo.mp3` + `words.json`, so the character
lines get captions like the narration. Get exact word times with faster-whisper (small.en), not Gemini: Gemini's
timestamps were off by 1-3 s and picked the wrong shots twice (a news ticker, Jason instead of Lucia).

## 4. Film-style gameplay Shorts (2026-11-02)

**Owner:** "romantic filmstyle and aesthetic and subtle", NPC voices first, little voiceover, slow music, "proof
Trevor is Michael's best friend". `tools/film_short.py`:
- the footage in a square film window (warm grade, light bloom, grain, lifted blacks), serif subtitles (Cormorant
  Garamond) keyed to **source** seconds, speaker labels in small caps, chapter lines in the top bar, a call log that
  strikes through each name that did not answer, a black end card;
- per-cut game audio (the NPC lines carry the story), 4 short voice lines only, a playful track for the funny act and a
  slow piano for the turn, and the key call line replayed through a phone filter + echo over the end card.
- `"version": "b"` writes `final-b.mp4` next to `final.mp4`, so the owner compares cuts. The owner picked B: a rock
  burst (with an impact hit) right after the key line, then piano again when the friend shows up. Music that changes
  with the story beats a single bed.
- libass only finds static fonts by their full family name ("Cormorant Garamond SemiBold"); variable fonts silently fall
  back to Arial. Keep subtitles off the in-game phone with a per-cut right margin (`"mr"`).

## 5. Look and sound rules that keep coming back

- One self-contained question per explainer, 30-45 s, hook scored before writing; end on a question.
- Facts: two sources each, and for a game moment watch a playthrough (Gemini) to confirm it on screen.
- A per-series look: RDR = Chinese Rocks lettering, white + red, small plain captions; GTA 6 = official logo every frame.
- Thumbnails: two or three words that are not the title, real faces (official art or the owner's frames), never images
  of unknown origin.
- Loudness: mix to -14 LUFS; a quiet emotional end card (-20 dB) is fine.

## 6. Collage b-roll: what other creators do (research log, keep adding)

- The "Vox / Johnny Harris" collage look: paper cut-outs of real photos with rough, torn edges, halftone and paper
  textures, a grid or ruled lines in the background, hand-drawn circles and arrows that draw on to point at the subject,
  slight "wiggle" (frames held on twos / posterised time), parallax between layers, lens blur on the back layer, light
  sweeps and ink bleeds as transitions, and hard reveal cuts on the beat. (Tutorial chapters by createdaley and Denys
  Zhylin, 2025.)
- AI pipelines now build a collage still from a one-line metaphor, approve it, then animate it assembling from empty
  (the `collage-broll-explainers` / `gbro-collage-broll` skills: metaphor -> still -> animation, two approval gates).
- B-roll as structure (Inside the Edit): chain shots for a process, single shots for an idea, and place each on the
  emotional keyword of the line, not as wallpaper.
- 2026-11-04, "How to Make Collage Animations like Johnny Harris" (youtube.com/watch?v=DwTEZukgMmk, watched by Gemini):
  - Rough, hand-cut mask edges and real paper / paint / grain textures over every cut-out; clean vector edges look
    corporate or AI-made.
  - Three depth planes (back, middle, front, ~400 px apart in 3D) with a slow, motivated camera move: parallax without
    distraction.
  - Abstract ideas become objects that move with meaning: right = forward in time, left = the past, scale up = gaining
    importance, stacking = accumulation.
  - Every entrance, pop and stop lands on a stressed word or a pause in the voice.
  - Motion held on twos at 12 fps, snapping fast into place on the beat; smooth 60 fps kills the handmade feel.
  - Materials: scans of real documents, letters, maps, paintings, newspaper clippings, gold leaf, distressed paper, film
    grain. Never a random element that does not illustrate the line.
- What we take for our painted beats next: real document / photo cut-outs (official art, the owner's frames) as torn
  paper layers inside the paintings, three-plane parallax, motion on twos for collage pieces only (the paintings stay
  smooth), and every element keyed to a stressed word.
