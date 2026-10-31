"""Gemini research for the channel, using the studio's Gemini key and client.

  python research.py viral [N]                  Today's trending Shorts from VIRAL_PAGE (example: a GTA trends page; plain fetch,
                                                no Firecrawl); Gemini watches the top N (default 5) -> research/viral-<date>.json
  python research.py swipe                      Recent Shorts of every trending channel -> research/swipe-<date>.json,
                                                the input for the yt-viral skill (swipe.py ranks by multiple over channel median)
  python research.py shorts <url> [<url> ...]   Gemini watches each Short -> research/shorts-<date>.json
  python research.py score <final.mp4|url> ...  Gemini virality review of OUR Short (local file before upload, or its
                                                YouTube URL after) -> research/score-<date>.json
  python research.py trends [notes.md]          Gemini + Google Search on viral Shorts in config.json's niche -> research/trends-<date>.json
                                                With notes (search results Claude collected), Gemini analyses those
                                                instead of searching (free Gemini keys have no Google Search quota).
                                                Trends always compares against our docs and the latest shorts-*.json analysis.
  python research.py index-clips                Gemini indexes new recordings in footage/ into docs/footage.md
                                                (the dashboard runs this automatically every minute).
  python research.py stock "<query>" [videos|images] [N]   Free Pixabay clips/photos (commercial use OK) ->
                                                assets/stock/, each logged in docs/assets.md with its page URL.

Raw output only. Claude reviews it before anything goes into docs/ (facts still need two sources).
"""
import datetime
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))

from google.genai import types  # noqa: E402
from engine import client as _get_client, extract_json  # noqa: E402

MODELS = ("gemini-flash-latest", "gemini-3.5-flash", "gemini-flash-lite-latest")  # aliases survive model retirements
OUT = ROOT / "research"
CLIPS = ROOT / "footage"
INDEX = ROOT / "docs" / "footage.md"
CLIP_EXT = {".mp4", ".mov", ".mkv", ".webm"}
OBS_NAME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}")  # recorder default name -> gets a descriptive one
VIRAL_PAGE = os.environ.get("VIRAL_PAGE", "https://heistnotes.com/viral")  # a trends page for your niche
TODAY = datetime.date.today().isoformat()

SHORT_PROMPT = """You are a YouTube Shorts analyst. Watch this Short and return ONLY a JSON object:
{"title": "", "channel": "", "length_s": 0, "topic": "",
 "hook_first_2s": "exact words spoken + what is on screen in the first 2 seconds",
 "structure": ["beat-by-beat with timestamps"],
 "cuts_per_10s": 0,
 "visual_sources": "official trailer frames / gameplay / AI images / memes / facecam / mix",
 "text_on_screen": "headline text: font feel, size, colours, position",
 "captions": "word-by-word or phrases, colours, active-word highlight, position, emojis",
 "voice": "AI or human, gender, pace (estimate words per minute), energy, accent",
 "music_sfx": "", "ending_cta": "", "loops": "does the ending flow back into the start?",
 "why_it_works": [""], "weak_points": [""]}
Describe only what you actually see and hear. Do not guess view counts."""

SCORE_PROMPT = """You review YouTube Shorts for virality on a Shorts channel whose viewers swipe within 2 seconds.
Watch this Short as a viewer scrolling the Shorts feed and return ONLY a JSON object:
{"hook_0_2s": {"score": 0, "what_happens": "", "fix": ""},
 "swipe_risks": [{"t": "m:ss", "why": "", "fix": ""}],
 "pacing": "is there a new visual every 5-7 seconds? where does it drag?",
 "captions": "readable at phone size? synced?", "audio": "voice energy, SFX, loudness",
 "loop": "does the ending flow back into the start?", "ending": "",
 "share_or_comment_trigger": "what would make someone share or comment, or why nothing would",
 "overall_score": 0, "top_3_fixes": [""]}
Scores are 0-10. Judge only what you see and hear. Do not predict view counts."""

TRENDS_PROMPT = f"""Today is {TODAY}. Use Google Search.
Niche: {json.loads((ROOT / "config.json" if (ROOT / "config.json").exists() else ROOT / "config.example.json").read_text("utf-8")).get("niche", "")}.
Research which YouTube Shorts / TikToks in this niche went viral in roughly the last 14 days, and which topics people
are talking about right now. Return only JSON: {{"viral": [{{"title", "url", "why"}}], "topics": [{{"topic", "sources"}}]}}.
Only include source URLs you actually found. Mark anything not confirmed by the official source as rumour."""

CLIP_PROMPT = """These frames come from one of the channel owner's own gameplay recordings; each is labelled with its timestamp.
Return ONLY a JSON object:
{"game": "", "slug": "short kebab-case name starting with a game code, e.g. rdr2-horse-throws-arthur, bf6-tank-ambush, gta5-police-chase",
 "what_happens": "one or two plain sentences",
 "best_moments": [{"t": "m:ss", "what": ""}],
 "mood": "funny | tense | epic | calm", "use_for": "hook | payoff | filler | transition | background",
 "bad_news_endings": [{"t": "m:ss", "what": "fails, deaths, crashes, being thrown, WASTED/DEAD screens"}],
 "good_news_endings": [{"t": "m:ss", "what": "kills, wins, big explosions, escapes, mission passed"}],
 "never_use": [{"from": "m:ss", "to": "m:ss", "what": "desktop, browser, other apps, personal info, pause/settings menus"}]}
Describe only what is visible. Timestamps are approximate because frames are sampled."""


def ask(contents, tools=None):
    """Try each model in turn; return the first response."""
    err = None
    for model in MODELS:
        try:
            print(f"   -> {model}")
            return _get_client().models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(temperature=0.4, tools=tools))
        except Exception as e:  # quota / overload: try the next model
            err = e
            print(f"   ! {model} failed: {str(e)[:160]}")
    raise err


def watch_url(url: str) -> str:
    """Gemini reads YouTube by watch URL; turn /shorts/ID and youtu.be/ID into that."""
    m = re.search(r"(?:shorts/|youtu\.be/|v=)([\w-]{11})", url)
    if not m:
        raise ValueError(f"Not a YouTube video URL: {url}")
    return f"https://www.youtube.com/watch?v={m.group(1)}"


def video_part(src: str):
    """A YouTube URL is read directly; a local file (our final.mp4 before upload) goes through the Files API."""
    if src.startswith("http"):
        return types.Part(file_data=types.FileData(file_uri=watch_url(src)))
    client = _get_client()
    f = client.files.upload(file=src)
    while f.state.name == "PROCESSING":
        time.sleep(3)
        f = client.files.get(name=f.name)
    if f.state.name != "ACTIVE":
        raise ValueError(f"Gemini could not process {src}: {f.state.name}")
    return types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=f.mime_type))


def shorts(urls, prompt=SHORT_PROMPT):
    results = []
    for url in urls:
        print(f"Watching {url}")
        try:
            r = ask(types.Content(parts=[video_part(url), types.Part(text=prompt)]))
            results.append({"url": url, **extract_json(r.text)})
        except Exception as e:  # keep going; one bad video should not lose the rest
            results.append({"url": url, "error": str(e)[:300]})
    return results


def viral_list(page_html: str) -> list:
    """Trending Shorts from the page's schema.org ItemList, in the page's own ranking (fastest-spreading first)."""
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page_html, re.S):
        data = json.loads(block)
        for item in data if isinstance(data, list) else [data]:
            if item.get("@type") == "ItemList":
                return [{"title": v["name"], "url": v["url"], "channel": v.get("author", {}).get("name", ""),
                         "views": v.get("interactionStatistic", {}).get("userInteractionCount", 0),
                         "uploaded": v.get("uploadDate", "")[:10]}
                        for v in (e["item"] for e in item["itemListElement"])]
    raise ValueError(f"No trending list found on {VIRAL_PAGE}; the page layout may have changed")


def viral(top=5):
    page = urllib.request.urlopen(urllib.request.Request(VIRAL_PAGE, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
    listing = viral_list(page.read().decode("utf-8"))
    return {"source": VIRAL_PAGE, "trending": listing, "analysed": shorts([v["url"] for v in listing[:top]])}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "replace")


def count(text):
    """'1.3M views' -> 1300000."""
    m = re.match(r"([\d.,]+)\s*([KMB]?)", text.strip(), re.I)
    if not m:
        return 0
    return int(float(m.group(1).replace(",", "")) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2).upper()])


def channel_shorts(page_html, channel):
    """Recent Shorts (title, views) from a channel's public /shorts page."""
    items = re.findall(r'"overlayMetadata":\{"primaryText":\{"content":"((?:[^"\\]|\\.)*)"\},"secondaryText":\{"content":"([^"]*)"', page_html)
    return [{"channel": channel, "title": json.loads(f'"{t}"'), "views": count(v), "url": "", "duration": 30} for t, v in items]


def swipe(listing):
    """yt-viral input: each trending channel's recent Shorts, so a hit can be measured against its own channel median."""
    collected, seen = [], set()
    for video in listing:
        try:
            handle = re.search(r'"canonicalBaseUrl":"(/@[^"]+)"', fetch(video["url"])).group(1)
            if handle in seen:
                continue
            seen.add(handle)
            print(f"   {handle}")
            collected += channel_shorts(fetch(f"https://www.youtube.com{handle}/shorts"), video["channel"])
        except Exception as e:  # one private/removed channel should not stop the rest
            print(f"   ! {video['channel']}: {e}")
    return collected


def trends(notes_file=None):
    ours = "\n\n".join((ROOT / "docs" / n).read_text("utf-8") for n in ("style.md", "formats.md"))
    picked = sorted(OUT.glob("shorts-*.json"))
    prompt = (TRENDS_PROMPT + "\n\n=== OUR STYLE AND FORMATS ===\n" + ours
              + ("\n\n=== OWNER'S INSPIRATION SHORTS (analysed) ===\n" + picked[-1].read_text("utf-8") if picked else ""))
    if notes_file:
        prompt = prompt.replace("Use Google Search.", "Use ONLY the search results provided below; do not invent others.")
        r = ask(prompt + "\n\n=== SEARCH RESULTS ===\n" + Path(notes_file).read_text("utf-8"))
    else:
        r = ask(prompt, tools=[types.Tool(google_search=types.GoogleSearch())])
    meta = r.candidates[0].grounding_metadata if r.candidates else None
    found = [{"title": c.web.title, "uri": c.web.uri}
             for c in (getattr(meta, "grounding_chunks", None) or []) if getattr(c, "web", None)]
    return {**extract_json(r.text), "searched_sources": found}


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def clip_slug(slug: str, suffix: str) -> Path:
    """Safe, unused filename in footage/ from Gemini's suggested slug."""
    base = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:60] or "clip"
    path, n = CLIPS / f"{base}{suffix}", 2
    while path.exists():
        path, n = CLIPS / f"{base}-{n}{suffix}", n + 1
    return path


def clip_entry(name, duration, has_audio, a, frames):
    moments = lambda xs: ", ".join(f"{x.get('t', '?')} {x.get('what', '')}" for x in xs or []) or "none spotted"
    never = "; ".join(f"{x.get('from', '?')}-{x.get('to', '?')} {x.get('what', '')}" for x in a.get("never_use") or [])
    return "\n".join([
        f"### {name}", f"- Game: {a.get('game', '?')}", f"- Length: {mmss(duration)}",
        f"- What happens: {a.get('what_happens', '')}", f"- Best moments: {moments(a.get('best_moments'))}",
        f"- Mood: {a.get('mood', '')}", f"- Use for: {a.get('use_for', '')}",
        f"- Audio: {'yes (mute)' if has_audio else 'no'}", "- Used in:",
        f"- Bad-news endings: {moments(a.get('bad_news_endings'))}",
        f"- Good-news endings: {moments(a.get('good_news_endings'))}",
        f"- Notes: auto-indexed {TODAY} by Gemini from {frames} sampled frames "
        f"(timestamps ±{max(1, round(duration / frames / 2))}s; scrub to confirm)." + (f" **NEVER USE {never}.**" if never else ""),
        ""])


def index_clip(path: Path, frames=24) -> str:
    """Gemini looks at sampled frames, then the clip is renamed (recorder names only) and appended to the index."""
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                                      "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout)
    duration = float(info["format"]["duration"])
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    parts = []
    for k in range(frames):
        t = duration * (k + 0.5) / frames
        jpg = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                              "-vf", "scale=512:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                             capture_output=True, check=True).stdout
        parts += [types.Part(text=f"t={mmss(t)}"), types.Part.from_bytes(data=jpg, mime_type="image/jpeg")]
    a = extract_json(ask(types.Content(parts=parts + [types.Part(text=CLIP_PROMPT)])).text)
    if OBS_NAME.match(path.name):
        path = path.rename(clip_slug(a.get("slug", ""), path.suffix))  # fails while still recording -> retried later
    with INDEX.open("a", encoding="utf-8") as f:
        f.write("\n" + clip_entry(path.name, duration, has_audio, a, frames))
    return path.name


INCIDENT_PROMPT = """These frames come from ONE long gameplay recording, one every {every} seconds, each labelled t=m:ss.
List EVERY distinct incident worth using in a YouTube Short: crashes, explosions, kills, deaths, fails, chases, police,
stunts, funny or weird moments, and a few big scenic shots. Skip stretches where nothing happens. Return ONLY JSON:
{{"game": "", "incidents": [{{"start": "m:ss", "end": "m:ss", "what": "one plain sentence",
   "kind": "crash | explosion | kill | death | fail | chase | police | stunt | funny | scenic | cutscene",
   "mood": "funny | tense | epic | calm", "ending": "bad | good | none",
   "slug": "short kebab-case name starting with a game code, e.g. gta5-truck-flips-on-highway"}}],
 "never_use": [{{"from": "m:ss", "to": "m:ss", "what": "desktop, browser, other apps, pause/settings menus, map screen, loading screen, personal info"}}]}}
ending: bad = fail, death, WASTED/DEAD screen, crash; good = kill, win, escape, mission passed. Only what is visible."""


def to_seconds(stamp) -> float:
    parts = [float(x) for x in str(stamp).strip().split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(parts)))


def find_incidents(path: Path, every=2, chunk=45) -> dict:
    """Gemini reads the whole recording as frames (one every `every` s, `chunk` frames per call) and lists its incidents."""
    import tempfile
    with tempfile.TemporaryDirectory(dir=ROOT / "research" / "raw") as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps=1/{every},scale=384:-2", "-q:v", "5",
                        f"{tmp}/f%05d.jpg"], check=True)
        frames = sorted(Path(tmp).glob("f*.jpg"))
        found, never, game = [], [], ""
        for start in range(0, len(frames), chunk):
            parts = []
            for k, f in enumerate(frames[start:start + chunk], start):
                parts += [types.Part(text=f"t={mmss(k * every)}"), types.Part.from_bytes(data=f.read_bytes(), mime_type="image/jpeg")]
            print(f"   frames {start}-{start + len(parts) // 2} of {len(frames)}", flush=True)
            for attempt in range(6):  # free tier caps input tokens per minute: wait out a 429 instead of losing the whole video
                try:
                    a = extract_json(ask(types.Content(parts=parts + [types.Part(text=INCIDENT_PROMPT.format(every=every))])).text)
                    break
                except Exception as e:
                    if "429" not in str(e) or attempt == 5:
                        raise
                    print(f"   rate limited, waiting 65 s ({attempt + 1}/5)", flush=True)
                    time.sleep(65)
            time.sleep(12)  # ponytail: fixed pacing for the free tier; drop it once the key is on a paid plan
            game = game or a.get("game", "")
            found += a.get("incidents") or []
            never += a.get("never_use") or []
    return {"source": path.name, "game": game, "every": every, "incidents": found, "never_use": never}


def cut_incidents(path: Path, found: dict, pad=(1.0, 2.0), shortest=4.0, longest=14.0) -> list:
    """One clip per incident in footage/clips/ (not auto-indexed), indexed here with its source time."""
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                                     capture_output=True, text=True, check=True).stdout)
    duration, out, made = float(info["format"]["duration"]), CLIPS / "clips", []
    out.mkdir(exist_ok=True)
    ends = lambda n: n.get("to") or n.get("end")  # Gemini sometimes writes "end" instead of "to"
    blocked = [(to_seconds(n["from"]), to_seconds(ends(n)) + 1) for n in found["never_use"] if n.get("from") and ends(n)]  # +1 s: frames are 2 s apart
    taken = []
    for i in sorted(found["incidents"], key=lambda x: to_seconds(x.get("start", 0))):
        try:
            a, b = max(0, to_seconds(i["start"]) - pad[0]), min(duration, to_seconds(i["end"]) + pad[1])
        except (KeyError, ValueError):
            continue
        b = min(max(b, a + shortest), a + longest, duration)  # ponytail: long incidents keep their first 14 s; split them if that loses the payoff
        b = min([b] + [x for x, y in blocked if a < x < b])  # stop before a never-use range (menu, desktop) starts
        if b - a < shortest or any(x <= a < y for x, y in blocked) or any(a < y - 1 and x + 1 < b for x, y in taken):
            continue  # too short once trimmed, starts inside a never-use range, or mostly a moment already cut
        name = re.sub(r"[^a-z0-9-]+", "-", str(i.get("slug", "clip")).lower()).strip("-")[:60] or "clip"
        target, n = out / f"{name}.mp4", 2
        while target.exists():
            target, n = out / f"{name}-{n}.mp4", n + 1
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", str(path), "-r", "30",
                        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k", str(target)], check=True)
        taken.append((a, b))
        made.append({"file": f"clips/{target.name}", "source": path.name, "from": mmss(a), "to": mmss(b), **i})
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(f"\n## Clips cut from {path.name} ({TODAY}, Gemini every {found['every']} s; {len(made)} clips)\n")
        for m in made:
            f.write(f"\n### {m['file']}\n- Game: {found['game']}\n- From: {m['source']} {m['from']}-{m['to']}\n"
                    f"- What happens: {m.get('what', '')}\n- Kind: {m.get('kind', '')} · Mood: {m.get('mood', '')}\n"
                    f"- Ending: {m.get('ending', 'none')}\n- Used in:\n")
    return made


def new_clips(settle=120):
    """Recordings not yet in the index whose file has stopped changing for `settle` seconds."""
    indexed = INDEX.read_text("utf-8") if INDEX.exists() else ""
    return [p for p in sorted(CLIPS.iterdir()) if p.suffix.lower() in CLIP_EXT
            and f"### {p.name}\n" not in indexed and time.time() - p.stat().st_mtime > settle] if CLIPS.exists() else []


def stock(query, kind="videos", n=3):
    """Download the top Pixabay clips or photos into assets/stock/ and log each in assets.md."""
    import os
    import urllib.parse
    import workflow  # noqa: F401 -- loads .env (PIXABAY_API_KEY)
    key = os.getenv("PIXABAY_API_KEY")
    if not key:
        raise ValueError("Set PIXABAY_API_KEY in .env")
    if kind not in ("videos", "images"):
        raise ValueError("kind is videos or images")
    params = {"key": key, "q": query[:100], "safesearch": "true", "per_page": max(3, n)}
    if kind == "images":
        params["image_type"] = "photo"
    api = "https://pixabay.com/api/videos/" if kind == "videos" else "https://pixabay.com/api/"
    req = urllib.request.Request(f"{api}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "Mozilla/5.0"})  # 403s Python's default agent
    hits = json.loads(urllib.request.urlopen(req, timeout=30).read())["hits"][:n]
    folder = ROOT / "assets" / "stock"
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40]
    rows = []
    for h in hits:
        url = next(v["url"] for v in (h["videos"].get(s, {}) for s in ("large", "medium", "small")) if v.get("url")) \
            if kind == "videos" else h["largeImageURL"]
        name = f"{slug}-{h['id']}{'.mp4' if kind == 'videos' else (Path(url.split('?')[0]).suffix or '.jpg')}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        (folder / name).write_bytes(urllib.request.urlopen(req, timeout=120).read())
        rows.append({"file": f"stock/{name}", "tags": h.get("tags", ""), "source": h["pageURL"]})
    with (ROOT / "docs" / "assets.md").open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(f"| `{r['file']}` | stock | Pixabay {kind[:-1]}: {r['tags']} | {r['tags']} | "
                    f"{r['source']} (Pixabay Content License: commercial use OK, no attribution needed) | free | |\n")
    return rows


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    import activity  # the dashboard's Agents page shows each run live
    step = {"viral": 1, "swipe": 1, "shorts": 1, "trends": 1, "score": 8, "index-clips": 4, "stock": 4, "incidents": 4}.get(cmd)
    video = Path(args[0]).parent.name if cmd == "score" and args and "videos" in Path(args[0]).parts else "channel"
    agent = {"swipe": "research.py swipe", "stock": "Pixabay"}.get(cmd, "Gemini")
    if step is not None:
        activity.log(video, step, agent, "running", f"research.py {cmd} {' '.join(args)}")
        sys.excepthook = lambda kind, error, tb: (activity.log(video, step, agent, "failed", f"{cmd}: {error}"),
                                                  sys.__excepthook__(kind, error, tb))
    if cmd == "index-clips":
        for clip in new_clips():
            print(f"Indexing {clip.name}")
            print(f"   indexed as {index_clip(clip)}")
        activity.log(video, step, agent, "done", "index-clips")
        sys.exit()
    if cmd == "viral":
        data = viral(int(args[0]) if args else 5)
    elif cmd == "swipe":
        data = swipe(viral_list(fetch(VIRAL_PAGE)))
    elif cmd == "shorts" and args:
        data = shorts(args)
    elif cmd == "score" and args:
        data = shorts(args, SCORE_PROMPT)
    elif cmd == "trends":
        data = trends(args[0] if args else None)
    elif cmd == "incidents" and args:
        sources = sorted(CLIPS.glob("*LONG*.mp4")) + sorted(CLIPS.glob("*DESKTOP*.mp4")) if args == ["long"] else [CLIPS / a for a in args]
        for src in sources:
            print(f"Finding incidents in {src.name}", flush=True)
            activity.log(video, step, agent, "running", f"incidents in {src.name}")
            found = find_incidents(src)
            (OUT / f"incidents-{src.stem}.json").write_text(json.dumps(found, indent=2, ensure_ascii=False), "utf-8")
            made = cut_incidents(src, found)
            print(f"   {len(found['incidents'])} incidents -> {len(made)} clips", flush=True)
            activity.log(video, step, agent, "done", f"{src.name}: {len(made)} clips in footage/clips/")
        sys.exit()
    elif cmd == "stock" and args:
        rows = stock(args[0], args[1] if len(args) > 1 else "videos", int(args[2]) if len(args) > 2 else 3)
        for r in rows:
            print(f"{r['file']}  <- {r['source']}")
        activity.log(video, step, agent, "done", f"{len(rows)} stock files for '{args[0]}'")
        sys.exit()
    else:
        sys.exit(__doc__)
    OUT.mkdir(exist_ok=True)
    path, n = OUT / f"{cmd}-{TODAY}.json", 2
    while path.exists():  # a second run the same day must not overwrite the first
        path, n = OUT / f"{cmd}-{TODAY}-{n}.json", n + 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    activity.log(video, step, agent, "done", f"saved research/{path.name}")
    print(f"Saved {path}")
