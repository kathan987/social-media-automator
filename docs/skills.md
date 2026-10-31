# Skills and tools the agent uses

The agent is Claude Code plus these skills, MCP servers and the scripts in `tools/`. Third-party skills are installed
from their own repos (they are not copied into this one).

## Skills
| Skill | What it does here | Install |
|---|---|---|
| `social-media-automator` (this repo) | The whole workflow as one skill: steps, rules, commands | ships in `.claude/skills/` |
| `yt-script`, `yt-package`, `yt-seo`, `yt-shorts`, `yt-viral`, `yt-retention`, `yt-audit`, `yt-chapters`, `yt-comment`, `yt-edit`, `yt-plan` | Hooks scored with `hookscore.py`, title + thumbnail pairing, descriptions, outlier ranking, retention and channel audits | `git clone https://github.com/Jakeschincariol/youtube-agent-skill.git` then `cp -r youtube-agent-skill/skills/yt-* ~/.claude/skills/` |
| `ig-reel`, `ig-caption`, `ig-human`, `ig-viral`, `ig-repurpose`, `ig-carousel`, `ig-story`, `ig-plan`, `ig-profile`, `ig-comment`, `ig-reply`, `ig-dm`, `ig-audit` | The same ideas cut for Reels, captions, and a humanizer that strips AI tells | `git clone https://github.com/Jakeschincariol/instagram-agent-skill.git` then `cp -r instagram-agent-skill/skills/ig-* ~/.claude/skills/` |
| `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use` | HTML-to-video: the scene format, the render CLI, ~450 ready blocks, media helpers | `npx skills add heygen-com/hyperframes` |
| `remotion-*` (optional) | Templated, data-driven videos and caption styles | `npx skills add remotion-dev/skills` |
| `hypit` (optional) | Clone a viral reference's structure | `npx skills add hypit-ai/hypit` |

The `yt-*` and `ig-*` tools say `python3`; on Windows run them with `python`.

## MCP servers (connected in Claude Code)
| Server | Used for | How it connects |
|---|---|---|
| Firecrawl | Searching and reading source pages for facts (budget: 20 credits per Short) | `.mcp.json` in this repo runs `npx -y firecrawl-mcp` with `FIRECRAWL_API_KEY` from your environment |
| Higgsfield (optional) | AI stills, background removal, upscaling (budget: 15 credits per Short) | Claude's connector settings |

## The dashboard (`dashboard/`)
A local web app at http://localhost:7071 (`python dashboard/app.py`) over the same folders: weekly targets, projects
with draft / voice / render / approve buttons, the footage library (auto-indexed by Gemini), a live agent feed, the asset
library and these docs. Its built-in `dashboard/engine.py` loads the keys from `.env`, calls Gemini (with model
fallback), repairs JSON replies, loads fonts and uploads to YouTube; nothing else to install. `dashboard/research.py` adds `score` (Gemini virality
check of a render), `trends`, `index-clips`, `incidents` (cut a long recording into clips) and `stock` (Pixabay).

## Scripts in `tools/`
| Script | Does |
|---|---|
| `find_outliers.py` | Ranks Shorts from hashtag pages by views over their channel's median |
| `vo_elevenlabs.py` | ElevenLabs voice + word timings -> `vo.mp3`, `words.json` |
| `vo_edge.py` | Free Microsoft Edge voice + word timings (same outputs) |
| `sticker_short.py` | Builds the HyperFrames page from `spec.json`: cuts, stickers, badge, captions, Three.js layer |
| `mix.py` | Voice + music + timed sound effects -> `final.mp4` at -14 LUFS |
| `thumbnail.py` | 9:16 and 16:9 thumbnails from `thumb.json` |
| `setup_scene.py` | Copies Three.js, GSAP and the font into the scene template after `npm install` |

## Also used
FFmpeg (cuts, review sheets, loudness), yt-dlp (research), Node 22+ (HyperFrames), Python 3.12+.
