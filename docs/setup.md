# Installation and setup

Everything you need before your first video, in order. Plan on 30-45 minutes the first time.

## 1. Programs to install

| Program | Why | Needed? | Windows (winget) | macOS (Homebrew) | Linux (apt) | Check |
|---|---|---|---|---|---|---|
| **Claude Code** | Runs the agent, the skills and the MCP servers | Required | install from [claude.com/claude-code](https://claude.com/claude-code) | same | same | `claude --version` |
| **Python 3.12+** (3.11 works) | All the tools in `tools/` and the dashboard | Required | `winget install Python.Python.3.12` | `brew install python@3.12` | `sudo apt install python3 python3-venv python3-pip` | `python --version` |
| **Node.js 22+** | HyperFrames (the scene renderer), Three.js, GSAP, the Firecrawl MCP server | Required | `winget install OpenJS.NodeJS.LTS` | `brew install node` | [nodejs.org](https://nodejs.org) | `node --version` |
| **FFmpeg** | Cutting clips, review sheets, mixing, loudness | Required | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` | `ffmpeg -version` |
| **Git** | Cloning this repo and the dependencies | Required | `winget install Git.Git` | `brew install git` | `sudo apt install git` | `git --version` |
| **Deno** | Lets yt-dlp solve YouTube's player challenges (research); without it some lookups fail | Recommended | `winget install DenoLand.Deno` | `brew install deno` | [deno.com](https://deno.com) | `deno --version` |

Open a new terminal after installing so the new programs are on your PATH.

## 2. Accounts and API keys

| Service | What it is used for | Needed? | Where to get the key | Where it goes |
|---|---|---|---|---|
| **Claude** (subscription or API) | The agent itself | Required | your Claude account | Claude Code login |
| **ElevenLabs** | The voiceover with word timings and acted moods | Optional (free Edge voice works without it). Use a paid plan before you monetize: the free plan has no commercial licence | elevenlabs.io → API keys; the voice ID is on the voice's page | `.env`: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| **Firecrawl** | Searching and reading source pages for the two-source fact check | Recommended | firecrawl.dev → API keys (`fc-...`) | your environment: `FIRECRAWL_API_KEY` (read by `.mcp.json`) |
| **Google Gemini** | The dashboard: drafting a project, virality scoring, auto-indexing your clips, trend research | Needed for the dashboard | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `.env`: `GEMINI_API_KEY` |
| **Pixabay** | Free stock clips and photos for real-world comparisons | Optional | pixabay.com/api/docs (free account) | `.env`: `PIXABAY_API_KEY` |
| **Higgsfield** | AI stills, background removal, upscaling | Optional | connect it in Claude's connector settings | no key in this repo |
| **YouTube Data API** (OAuth) | Only if you want the dashboard to upload for you; by default you upload by hand | Optional | Google Cloud Console → enable YouTube Data API v3 → OAuth client (Desktop app) → download the JSON | `client_secret.json` in the repo root (git-ignored); the first upload opens a browser to sign in |

Keys never go in git: `.env` is ignored, and `.mcp.json` only references `${FIRECRAWL_API_KEY}`.

## 3. Install, step by step

Run these from the folder where you keep projects.

**3.1 Get the repo and a Python environment**

```bash
git clone https://github.com/kathan987/social-media-automator.git
```

```bash
cd social-media-automator
```

```bash
python -m venv .venv
```

Activate it: Windows PowerShell `.venv\Scripts\Activate.ps1`, macOS/Linux `source .venv/bin/activate`. Then:

```bash
pip install -r requirements.txt
```

**3.2 The dashboard.** Nothing extra: that one `pip install` covers it, and its engine (`dashboard/engine.py`: keys,
Gemini, JSON repair, fonts, YouTube upload) is built in.

**3.3 The scene renderer**

```bash
npm install
```

npm may print an "allow-scripts" warning; the render still works.

**3.4 Fonts.** Download [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue),
[Anton](https://fonts.google.com/specimen/Anton) and [Poppins](https://fonts.google.com/specimen/Poppins) (free, OFL).
Put `BebasNeue-Regular.ttf`, `Anton-Regular.ttf` and `Poppins-SemiBold.ttf` in `assets/fonts/`. Optional: a bold serif
saved as `georgiab.ttf` (wanted poster) and a bold monospace as `consolab.ttf` (evaluation form); without them the
browser's serif and monospace are used.

**3.5 Copy Three.js, GSAP and the font into the scene template**

```bash
python tools/setup_scene.py
```

**3.6 Prove the 3D layer renders.** This should print "Render complete" and make an 8-second clip:

```bash
npx hyperframes render scenes/explainer-scene --quality draft --output scenes/explainer-scene/selftest.mp4
```

**3.7 Your config and keys.** Copy the two example files, then fill them in:

```bash
cp config.example.json config.json
```

```bash
cp .env.example .env
```

In `config.json`: channel name, niche, weekly targets, the two series characters, caps. In `.env`: the keys from section 2.

**3.8 Firecrawl in Claude Code.** `.mcp.json` already defines the server. Set the key in the terminal you start
Claude from (PowerShell: `$env:FIRECRAWL_API_KEY="fc-..."`, bash/zsh: `export FIRECRAWL_API_KEY=fc-...`), then start
`claude` in this folder and approve the project's `firecrawl` server when asked.

**3.9 The skills.** Install the YouTube and Instagram packs and the HyperFrames skills (exact commands in
`docs/skills.md`). The `social-media-automator` skill already ships in `.claude/skills/`.

**3.10 Sounds and logo.** Put short sound effects in `assets/sfx/`: `whoosh.mp3`, `hit.mp3`, `boom.mp3`, `click.mp3`
(cards, form ticks, the subscribe click), `bell.mp3` (end card), `good-ending.mp3`, `bad-ending.mp3` (Pixabay's sound
effects allow commercial use). `tools/sticker_short.py` writes the first five into each `mix.json` and skips any that are
missing. Put your channel logo at `assets/logo.jpg` for the subscribe end card.

**3.11 Your footage.** Put your own recordings in `footage/` and short best-moment cuts (4-14 s) in `footage/clips/`.
Start each file name with a game or topic code (`rdr2-horse-ride.mp4`): the dashboard groups clips by it.

**3.12 Your style.** Fill in `docs/style.md`, `docs/topics.md` and `docs/inspirations.md`.

## 4. Start the dashboard

```bash
python dashboard/app.py
```

Open http://localhost:7071. It reads the folders on disk (no database):
- **Overview:** this week's uploads against `weekly_targets`, the review queue, b-roll used, the footage library.
- **Videos:** create a project, edit its plan, run draft / voice / render, approve, and copy the upload text.
- **Gameplay:** every clip in `footage/` with its `docs/footage.md` entry; new recordings are indexed by Gemini while
  the dashboard runs.
- **Agents:** a live feed of every step (`python dashboard/activity.py <slug|channel> <step> "<agent>" <running|done>`).
- **Library / Docs:** your assets and these docs, editable in the browser.

Optional: put a `hero.jpg` (one you own) in `dashboard/assets/` for the Overview banner.

## 5. Check that everything works

```bash
python -m unittest discover -s dashboard
```

All 35 tests should pass (they use temporary folders and spend no credits). Then make your first
video: README "Create your own video".

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` (Windows) | Use `python`. The `yt-*` / `ig-*` skills write `python3` in their docs. |
| `ModuleNotFoundError` (flask, moviepy, google) when starting the dashboard | Activate the venv and run `pip install -r requirements.txt` again. |
| "Set GEMINI_API_KEY in .env" | Add the key from aistudio.google.com/apikey to `.env` and restart the dashboard. |
| `Missing: node_modules/...` from `setup_scene.py` | Run `npm install` first, and put the font in `assets/fonts/`. |
| ElevenLabs `quota_exceeded` | Use `tools/vo_edge.py` (free), or top up the plan. |
| yt-dlp: "Sign in to confirm your age" | That video is age-restricted. Pick another source; do not use your browser cookies. |
| yt-dlp: "No supported JavaScript runtime" | Install Deno (section 1). |
| The 3D layer is blank in a render | Check `npx hyperframes check scenes/<scene> --json`: `runtime.ok` must be true. |
| A 404 for `hero.jpg` on the dashboard | Optional banner image: add your own to `dashboard/assets/` or ignore it. |
