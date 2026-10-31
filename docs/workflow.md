# Workflow: from idea to a finished Short

This is the order the agent works in, every time. Each step names the tool or skill that does it and what it leaves
behind in `projects/<slug>/`. `rules.md` wins wherever it is stricter than this file.

| # | Step | Tools / skills | Output in `projects/<slug>/` |
|---|---|---|---|
| 0 | **One-time setup** | README "Quick start": `pip`, `npm`, fonts, `tools/setup_scene.py`, skills, `config.json`, `.env` | a working `scenes/explainer-scene` self-test |
| 1 | **Find what is working** | `python tools/find_outliers.py <hashtags>` (views over each channel's own median), `/yt-viral` (`swipe.py`), `/ig-viral` | `research/outliers-<date>.json`, 3 idea candidates |
| 2 | **Gather facts** | Firecrawl (search / scrape) or the browser; Agent-Reach for Reddit and YouTube transcripts. Two reliable sources per claim. | `research.md` (each claim + its two URLs + credits used) |
| 3 | **Pick the topic** | The owner picks, or says "you pick". Use the next question in `topics.md` for a series. | `meta.json` (topic, type, created date) |
| 4 | **Script** | `/yt-script`: five hooks scored with `hookscore.py`, best two shown, then the spoken script. `/ig-reel` for Reels (`beats.py` times it). `/ig-human` strips the AI tells. | `script.txt` (mood tags like `[serious]` allowed) |
| 5 | **Voice** | `python tools/vo_elevenlabs.py <slug> projects/<slug>/script.txt 1.1` or the free `python tools/vo_edge.py <slug> projects/<slug>/script.txt` | `vo.mp3`, `words.json` (every word with start/end) |
| 6 | **Assets** | Your own footage in `footage/` (`footage/clips/` for short cuts), stickers in `scenes/<scene>/assets/st/`, official publisher images, optional AI stills (Higgsfield). Log every asset with its source URL. | files in the scene's `assets/` |
| 7 | **Scene plan** | Write `spec.json` (see `templates/example-explainer/spec.json`): cuts on words, stickers on nouns, one Three.js element where it explains something | `spec.json` |
| 8 | **Build + render** | `python tools/sticker_short.py projects/<slug>/spec.json`, then `npx hyperframes render scenes/<scene> --output scenes/<scene>/out.mp4` | `scenes/<scene>/index.html`, `out.mp4`, `cues.json` |
| 9 | **Review** | One frame every 2 s: `ffmpeg -i scenes/<scene>/out.mp4 -vf "fps=0.5,scale=216:-2,tile=9x2" -frames:v 1 review.jpg`. Look for menus, cut-off subtitles, black bars, a dark first frame. Fix the spec, rebuild. | `review.jpg` |
| 10 | **Mix** | `mix.json` (video, music, voice as the first sfx, whooshes on cuts, hits on stickers) then `python tools/mix.py projects/<slug>/mix.json` (-14 LUFS) | `final.mp4` |
| 11 | **Package** | `/yt-package` (title + thumbnail words as one pair), `/yt-seo` (description with every source link), `thumb.json` then `python tools/thumbnail.py <slug>`, a pinned comment | `thumbnail.jpg`, `thumbnail-16x9.jpg`, `upload.json` |
| 12 | **Hand-off** | The owner uploads in YouTube Studio as private + scheduled and ticks "altered or synthetic content" when AI voice or images are used. The agent never publishes. | the live Short |
| 13 | **Weekly review** | Studio screenshots into `/yt-audit` and `/yt-retention`: top vs bottom Shorts by viewed-vs-swiped, length, hook type. Write the changes back into these docs. | updated `formats.md` / `style.md` |

## Folder layout

```
footage/          your own recordings (never committed)
footage/clips/    short 4-14 s cuts of the best moments
projects/<slug>/  one folder per Short: meta, research, script, words, spec, mix, final, thumbnails, upload
scenes/<scene>/   one HyperFrames composition per Short (copied from scenes/explainer-scene)
assets/           stickers, music, sfx, fonts, official images (media never committed)
research/         outlier searches and analysis
templates/        a complete example project to copy
```

## Logging

Write credits used (Firecrawl, Higgsfield) into each project's `research.md`, and every new asset with its source URL
into your asset log (a table in `docs/` works). That is what keeps the next Short cheap.
