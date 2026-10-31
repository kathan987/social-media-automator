# social-media-automator

An AI agent workflow that turns an idea into a finished vertical Short: researched, fact-checked, scripted, voiced,
edited over your own footage with stickers and a Three.js 3D element, mixed, thumbnailed and packaged for upload.

It runs inside [Claude Code](https://claude.com/claude-code). The "agent" is Claude plus a set of skills, a few small
scripts and a written workflow with rules. Nothing here posts for you: the agent delivers the file and the text, and
you upload.

It was built and tested on a gaming Shorts channel (story explainers about game characters, news, did-you-know and
what-if Shorts), but every step is generic. Swap the footage, the niche and the topic backlog and it works for any
channel built on your own recordings.

```
idea ──► research (two sources per claim) ──► 5 hooks scored ──► script ──► voice + word timings
     ──► scene spec (cuts on words, stickers on nouns, one 3D element) ──► HyperFrames render
     ──► review sheet ──► mix (-14 LUFS) ──► thumbnails + title + description ──► you upload
```

## What is in the box

| Path | What |
|---|---|
| `CLAUDE.md` | The agent's standing instructions |
| `.claude/skills/social-media-automator/` | The whole workflow as one skill Claude can run step by step |
| `docs/workflow.md` | The 13 steps, the tool for each and what it leaves behind |
| `docs/rules.md` | Facts, footage, AI disclosure, budgets, edit rules, and the monetization goal behind them |
| `docs/formats.md` | News, did-you-know, what-if and the explainer series format |
| `docs/style.md`, `docs/topics.md` | Templates you fill in for your channel |
| `docs/research.md` | How to find outliers, and what the first tests taught |
| `docs/skills.md` | Every skill, MCP server and script, with install commands |
| `tools/` | `find_outliers.py`, `vo_elevenlabs.py`, `vo_edge.py`, `sticker_short.py`, `mix.py`, `thumbnail.py`, `setup_scene.py` |
| `scenes/explainer-scene/` | The HyperFrames template with the Three.js layer (`assets/explain3d.js`) and a self-test page |
| `templates/example-explainer/` | A complete, sourced example project (script, spec, mix, thumbnail, upload text, research) |

## Quick start

**You need:** Claude Code, Python 3.11+, Node 22+, FFmpeg on your PATH, and git.

```bash
git clone https://github.com/kathan987/social-media-automator.git
```

```bash
cd social-media-automator
```

```bash
pip install -r requirements.txt
```

```bash
npm install
```

1. **Fonts.** Download [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) and
   [Anton](https://fonts.google.com/specimen/Anton) from Google Fonts and put `BebasNeue-Regular.ttf` and
   `Anton-Regular.ttf` in `assets/fonts/`.
2. **Scene setup.** This copies Three.js, GSAP and the font into the template:

   ```bash
   python tools/setup_scene.py
   ```

3. **Check that the 3D layer renders.** You should get an 8-second clip with a timeline and a jet:

   ```bash
   npx hyperframes render scenes/explainer-scene --quality draft --output scenes/explainer-scene/selftest.mp4
   ```

4. **Config.** Copy `config.example.json` to `config.json` and fill in your channel, niche, weekly targets and your
   two series characters. Copy `.env.example` to `.env` and add an ElevenLabs key if you have one (optional: the free
   Edge voice works without one).
5. **Skills.** Install the YouTube and Instagram skill packs and the HyperFrames skills (commands in `docs/skills.md`).
   Connect Firecrawl as an MCP server for research (and Higgsfield if you want AI stills).
6. **Your footage.** Put your own recordings in `footage/` and short best-moment cuts (4-14 s) in `footage/clips/`.
7. **Your style.** Fill in `docs/style.md` and `docs/topics.md`.

## Create your own video

The easy way: open Claude Code in this folder and say

```
Make the next explainer Short about <character>. Follow the social-media-automator skill.
```

Claude runs the steps below, shows you the two best hooks, the script and a review sheet, and hands you the finished
files. Here is what it does, so you can also run it by hand.

**1. Find an idea that is already working.** Rank Shorts in your niche by how far each beat its own channel:

```bash
python tools/find_outliers.py yourniche yourtopic yourcharacter
```

**2. Research.** For one claim, find two reliable sources and write them into `projects/<slug>/research.md`. The slug
is `YYYY-MM-DD-short-title`.

**3. Script.** Ask Claude for five hooks with `/yt-script`, keep the best-scored one, and write `projects/<slug>/script.txt`
(30-45 s for an explainer, ending on one question). `templates/example-explainer/script.txt` shows the shape.

**4. Voice.** Use ElevenLabs:

```bash
python tools/vo_elevenlabs.py <slug> projects/<slug>/script.txt 1.1
```

or the free voice:

```bash
python tools/vo_edge.py <slug> projects/<slug>/script.txt
```

Both write `vo.mp3` and `words.json`, which holds every word with its start time.

**5. Scene spec.** Copy `templates/example-explainer/spec.json` to `projects/<slug>/spec.json`. Each cut is
`[word, after_seconds, clip, {offset, focus, bars, keep}]`, and starts on that word. Each sticker is
`[id, image or html chip, start word, end word, css]`. `three` adds a 3D timeline or jet between two words, and
`badge` puts a name pill on top.

**6. Build and render.**

```bash
python tools/sticker_short.py projects/<slug>/spec.json
```

```bash
npx hyperframes render scenes/<scene> --output scenes/<scene>/out.mp4
```

**7. Review.** Make one frame every 2 seconds, check it for menus, cut-off subtitles and black bars, then fix the
spec and repeat step 6:

```bash
ffmpeg -i scenes/<scene>/out.mp4 -vf "fps=0.5,scale=216:-2,tile=9x2" -frames:v 1 scenes/<scene>/review.jpg
```

**8. Mix.** Copy `templates/example-explainer/mix.json`, point it at your render, music and voice, and set the
sound-effect times from `cues.json`:

```bash
python tools/mix.py projects/<slug>/mix.json
```

**9. Package.** Write `thumb.json` (2-3 words, never the title) and run:

```bash
python tools/thumbnail.py <slug>
```

Then write `upload.json` with the title, a description with every source link, tags and a pinned comment.

**10. Upload yourself.** Upload as private and scheduled in YouTube Studio, and tick "altered or synthetic content"
if the voice or any image is AI.

## Rules that matter most

- Two reliable sources for every claim. Never invent facts, quotes or footage.
- Your own recordings for gameplay. Official publisher art only with its URL in the description.
- The first frame is the thumbnail. A new visual every 2-4 seconds. One question at the end.
- The agent never publishes, never prints keys, and never commits footage (`.gitignore` blocks all media).

The full list is in `docs/rules.md`.

## Credits

The YouTube and Instagram skill packs are by [Jake Schincariol](https://github.com/Jakeschincariol), the scene engine
is [HyperFrames](https://github.com/heygen-com/hyperframes), and 3D is [Three.js](https://threejs.org). They are
installed from their own repos, not copied here.
