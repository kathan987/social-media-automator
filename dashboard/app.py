"""Channel dashboard. Run: python dashboard/app.py  ->  http://localhost:7071

Reads the folders next to it (docs/, footage/, videos/, config.json). No database:
the filesystem is the state. Local only (127.0.0.1).
"""
import datetime as dt
import json
import re
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
import workflow as production
import activity

ROOT = Path(__file__).resolve().parent.parent
DOCS, VIDEOS, CLIPS = ROOT / "docs", ROOT / "projects", ROOT / "footage"
DOC_NAMES = ("rules.md", "workflow.md", "setup.md", "formats.md", "style.md", "topics.md", "research.md", "skills.md",
             "footage.md", "inspirations.md", "assets.md")
SKILLS = ROOT / ".claude" / "skills"  # this repo's project skills
CLIP_EXT = {".mp4", ".mov", ".mkv", ".webm"}
STAGES = [("brief", "brief.md"), ("research", "research.md"), ("script", "script.md"),
          ("shots", "shots.json"), ("voiceover", "vo.mp3"), ("render", "final.mp4"),
          ("uploaded", "publish.json")]

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024
busy = threading.Lock()
# shortcut: progress is in memory; use a durable worker if jobs must survive server restarts.
jobs = {}
tool_lock = threading.Lock()  # one research.py tool at a time, separate from production steps
tool = {"cmd": "", "status": "idle", "log": []}
TOOLS = {"stock", "incidents", "index-clips", "viral", "swipe", "trends"}


@app.before_request
def local_only():
    if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
        return jsonify(error="Local dashboard only"), 403
    origin = request.headers.get("Origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and urlsplit(origin).netloc != request.host:
        return jsonify(error="Cross-origin writes are disabled"), 403
    if request.method not in {"GET", "HEAD", "OPTIONS"} and "/run/" not in request.path:
        if not busy.acquire(blocking=False):
            return jsonify(error="A production step is running; wait before editing"), 409
        g.write_lock = True


@app.teardown_request
def release_write_lock(error):
    if g.pop("write_lock", False):
        busy.release()


@app.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(FileNotFoundError)
def missing(error):
    return jsonify(error="Required project file is missing; complete the preceding step first"), 400


def body():
    value = request.get_json(force=True)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def idle():
    if busy.locked() and not g.get("write_lock"):
        raise ValueError("A production step is running; wait before editing")


def jload(path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return default


def cfg():
    return jload(ROOT / "config.json", None) or jload(ROOT / "config.example.json", {})


def week_start(d):
    return d - dt.timedelta(days=d.weekday())


def list_videos():
    if not VIDEOS.exists():
        return []
    out = []
    for d in sorted(VIDEOS.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta = jload(d / "meta.json", {})
        shots = jload(d / "shots.json", [])
        publication = jload(d / "publish.json", {})
        kinds = [s.get("kind") for s in shots if isinstance(s, dict)] if isinstance(shots, list) else []
        out.append({
            "slug": d.name, "topic": meta.get("topic", d.name), "type": meta.get("type", ""),
            "game": meta.get("game", ""), "created": meta.get("created", ""),
            "approved": bool(meta.get("approved")),
            "stages": {k: publication.get("status") == "scheduled" if k == "uploaded" else (d / f).exists() for k, f in STAGES},
            "publication": publication, "job": jobs.get(d.name),
            "hf_images": kinds.count("higgsfield_image"), "hf_broll": kinds.count("higgsfield_broll"),
        })
    return out


@app.get("/")
def index():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.get("/assets/<path:name>")
def assets(name):
    return send_from_directory(Path(__file__).parent / "assets", name)


@app.get("/api/status")
def status():
    c = cfg()
    ws = week_start(dt.date.today()).isoformat()
    vs = list_videos()
    end = (week_start(dt.date.today()) + dt.timedelta(days=7)).isoformat()
    done = {t: sum(1 for v in vs if v["type"] == t and v["stages"]["uploaded"] and ws <= v["publication"].get("publish_at", "")[:10] < end) for t in c.get("weekly_targets", {})}
    allocations = [r for p in VIDEOS.glob("*/higgsfield.json") for r in jload(p, {}).get("requests", [])]
    broll = {game: sum(r["kind"] == "higgsfield_broll" and r.get("game") == game and ws <= r["created"] < end for r in allocations) for game in c.get("games", [])}
    oauth = jload(production.engine.CLIENT_SECRET, {}).get("installed", {})
    youtube_ready = all(isinstance(oauth.get(k), str) and oauth[k] and "YOUR" not in oauth[k].upper() and "PLACEHOLDER" not in oauth[k].upper() for k in ("client_id", "client_secret"))
    music = ROOT / "assets" / "music"
    options = {"kinds": sorted(production.KINDS), "stamps": sorted(production.STAMPS), "moods": sorted(production.MOODS),
               "sfx": sorted(c.get("sfx") or {}), "music": sorted(f.name for f in music.iterdir() if f.is_file()) if music.exists() else []}
    return jsonify(config=c, week_start=ws, done=done, broll_used=broll, videos=vs, options=options,
                   services={"elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID")),
                             "ai": bool(production.engine.gemini_key()),
                             "youtube": youtube_ready})


@app.post("/api/videos")
def new_video():
    b = body()
    topic = str(b.get("topic") or "").strip()
    if not topic or b.get("type") not in cfg().get("weekly_targets", {}):
        return jsonify(error="topic and a valid type are required"), 400
    today = dt.date.today().isoformat()
    slug = f"{today}-{re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:40]}"
    d = VIDEOS / slug
    if d.exists():
        return jsonify(error="that video folder already exists"), 409
    meta = {"topic": topic, "type": b["type"], "game": b.get("game", ""), "created": today, "approved": False}
    if meta["game"] not in cfg().get("games", []) + [""]:
        raise ValueError("Choose a configured game")
    (d / "assets").mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps(meta, indent=2), "utf-8")
    (d / "brief.md").write_text(f"# {topic}\n\nFormat: {b['type']}\nGame: {meta['game']}\n\nNotes:\n", "utf-8")
    production.write(d / "project.json", {"title": topic[:100], "description": "", "tags": [], "claims": [], "shots": []})
    return jsonify(slug=slug)


@app.post("/api/videos/<slug>/approve")
def approve(slug):
    idle()
    folder = production.project(slug)
    p = folder / "meta.json"
    meta = jload(p, {})
    meta["approved"] = not meta.get("approved")
    meta["approval_digest"] = production.digest(folder) if meta["approved"] else None
    production.write(p, meta)
    return jsonify(approved=meta["approved"])


@app.get("/files/<slug>/<name>")
def video_file(slug, name):
    return send_from_directory(production.project(slug), name)


@app.route("/api/videos/<slug>/project", methods=["GET", "PUT"])
def project_data(slug):
    folder = production.project(slug)
    if request.method == "PUT":
        idle()
        if (folder / "publish.json").exists():
            raise ValueError("This project has an upload receipt; create a new video for a new version")
        production.save_plan(folder, body())
    return jsonify(production.read(folder / "project.json"))


@app.get("/api/videos/<slug>/upload")
def upload_details(slug):
    """What the owner pastes into YouTube (owner, 2026-10-29: show it in a popup, no scrolling).
    upload.json if the video has one, else the project's own title/description/tags."""
    folder = production.project(slug)
    if (folder / "upload.json").exists():
        data = production.read(folder / "upload.json")
    else:
        plan = production.read(folder / "project.json") if (folder / "project.json").exists() else {}
        tags = plan.get("tags", [])
        data = {"title": plan.get("title", ""), "description": plan.get("description", ""),
                "tags": ", ".join(tags) if isinstance(tags, list) else str(tags), "pinned": plan.get("pinned_comment", ""), "notes": ""}
    data["thumbnails"] = [f"/files/{slug}/{n}" for n in ("thumbnail.jpg", "thumbnail-16x9.jpg") if (folder / n).exists()]
    return jsonify(data)


@app.post("/api/videos/<slug>/higgsfield")
def higgsfield_queue(slug):
    idle()
    return jsonify(production.higgsfield_requests(production.project(slug)))


@app.put("/api/videos/<slug>/higgsfield/<request_id>")
def higgsfield_result(slug, request_id):
    idle()
    return jsonify(production.record_higgsfield(production.project(slug), request_id, body()))


@app.post("/api/videos/<slug>/assets")
def add_asset(slug):
    idle()
    folder = production.project(slug)
    uploaded = request.files.get("file")
    name = secure_filename(uploaded.filename or "") if uploaded else ""
    if not name or Path(name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}:
        raise ValueError("Upload an image or video")
    target = folder / "assets" / name
    if target.exists():
        raise ValueError("Filename already exists; choose a new filename")
    uploaded.save(target)
    return jsonify(file=name)


@app.get("/api/videos/<slug>/assets")
def list_assets(slug):
    folder = production.project(slug) / "assets"
    return jsonify(sorted(f.name for f in folder.iterdir() if f.is_file()) if folder.exists() else [])


@app.get("/api/videos/<slug>/sheet")
def review_sheet(slug):
    """One frame per second of final.mp4 on a 10x3 grid (Shorts here are at most 30 s): the same review Claude does."""
    folder = production.project(slug)
    video, sheet = folder / "final.mp4", folder / "sheet.jpg"
    if not video.exists():
        raise FileNotFoundError(video)
    if not sheet.exists() or sheet.stat().st_mtime < video.stat().st_mtime:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", "fps=1,scale=216:-1,tile=10x3",
                        "-frames:v", "1", str(sheet)], check=True, timeout=120)
    return send_from_directory(folder, "sheet.jpg", max_age=0)


@app.post("/api/videos/<slug>/run/<action>")
def run_step(slug, action):
    folder = production.project(slug)
    data = body()
    if action not in {"draft", "voice", "render", "publish"}:
        raise ValueError("Unknown production step")
    if (folder / "publish.json").exists():
        raise ValueError("Upload receipt already exists; check YouTube Studio before changing this project")
    if not busy.acquire(blocking=False):
        return jsonify(error="Another production step is running"), 409
    jobs[slug] = {"action": action, "status": "running"}
    step, agent = {"draft": (3, "Gemini"), "voice": (6, "ElevenLabs"), "render": (7, "Renderer"), "publish": (9, "Owner")}[action]
    activity.log(slug, step, agent, "running", f"dashboard: {action}")
    def work():
        try:
            if action == "draft": production.draft(folder)
            elif action == "voice": production.narrate(folder)
            elif action == "render": production.render(folder)
            else: production.publish(folder, data.get("publish_at", ""))
            jobs[slug] = {"action": action, "status": "done"}
            activity.log(slug, step, agent, "done", f"dashboard: {action}")
        except Exception as error:
            jobs[slug] = {"action": action, "status": "failed", "error": str(error)[:800]}
            activity.log(slug, step, agent, "failed", str(error))
        finally:
            busy.release()
    threading.Thread(target=work, daemon=True).start()
    return jsonify(ok=True), 202


def clip_index():
    """docs/footage.md entries -> {heading: {field: value}}; "Kind: x · Mood: y" lines give two fields."""
    idx_file = DOCS / "footage.md"
    out, entry = {}, None
    for line in idx_file.read_text("utf-8").splitlines() if idx_file.exists() else []:
        if line.startswith("### "):
            entry = out.setdefault(line[4:].strip(), {})
        elif line.startswith("## "):
            entry = None
        elif entry is not None and line.startswith("- "):
            for part in line[2:].split(" · "):
                key, _, value = part.partition(":")
                if value.strip():
                    entry[key.strip().lower()] = value.strip()
    return out


@app.get("/api/clips")
def clips():
    idx = clip_index()
    files = sorted(f for f in CLIPS.rglob("*") if f.suffix.lower() in CLIP_EXT) if CLIPS.exists() else []
    return jsonify([{"file": rel, "mb": round(f.stat().st_size / 1e6, 1), "rejected": rel.startswith("_rejected/"),
                     "indexed": info is not None, "info": info or {}}  # cut clips are indexed as clips/<name>
                    for f in files for rel in [f.relative_to(CLIPS).as_posix()]
                    for info in [idx.get(rel, idx.get(f.name))]])


@app.get("/clips/<path:name>")
def clip_file(name):
    return send_from_directory(CLIPS, name)


@app.get("/api/tools")
def tool_state():
    return jsonify(tool)


@app.post("/api/tools/<cmd>")
def run_tool(cmd):
    """research.py from the dashboard: Pixabay stock, cutting long recordings, indexing, viral research. Logs to Agents."""
    b = body()
    if cmd not in TOOLS:
        raise ValueError("Unknown tool")
    args = []
    if cmd == "stock":
        query, n = str(b.get("query") or "").strip(), b.get("n", 3)
        if not 0 < len(query) <= 80 or b.get("kind", "videos") not in ("videos", "images") or isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 10:
            raise ValueError("Stock needs a search (max 80 characters), videos or images, and 1-10 files")
        args = [query, b.get("kind", "videos"), str(n)]
    elif cmd == "incidents":
        args = ["long"]  # every *LONG* / *DESKTOP* recording; clips already cut are skipped as near-duplicates
    elif cmd == "viral":
        top = b.get("top", 5)
        args = [str(min(max(top, 1), 20) if isinstance(top, int) and not isinstance(top, bool) else 5)]
    if not tool_lock.acquire(blocking=False):
        return jsonify(error=f"{tool['cmd']} is still running"), 409
    tool.update(cmd=cmd, status="running", log=[])

    def work():
        try:
            proc = subprocess.Popen([sys.executable, "-X", "utf8", "-B", "-u", "research.py", cmd, *args], cwd=Path(__file__).parent,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                tool["log"] = (tool["log"] + [line.rstrip()])[-60:]
            tool["status"] = "done" if proc.wait() == 0 else "failed"
        except Exception as error:
            tool["log"] = tool["log"] + [str(error)]
            tool["status"] = "failed"
        finally:
            tool_lock.release()
    threading.Thread(target=work, daemon=True).start()
    return jsonify(ok=True), 202


@app.get("/api/activity")
def agents():
    return jsonify(activity.board())


def library_rows():
    """docs/assets.md table rows; the File cell is an exact path or a pattern like `memes/<reaction>-<id>.mp4`."""
    p = DOCS / "assets.md"
    rows = []
    for line in p.read_text("utf-8").splitlines() if p.exists() else []:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.search(r"`([^`]+)`", cells[0])
        if len(cells) == 7 and m:
            rows.append(dict(zip(("file", "kind", "shows", "tags", "source", "credits", "used"), [m.group(1)] + cells[1:])))
    return rows


@app.get("/api/library")
def library():
    lib, rows = ROOT / "assets", library_rows()
    exact = {r["file"]: r for r in rows}
    patterns = {r["file"].split("/")[0]: r for r in rows if re.search(r"[*<]", r["file"])}
    files = sorted(f for f in lib.rglob("*") if f.is_file()) if lib.exists() else []
    return jsonify([{"file": rel, "folder": rel.split("/")[0], "kb": round(f.stat().st_size / 1024),
                     "info": exact.get(rel) or patterns.get(rel.split("/")[0])}
                    for f in files for rel in [f.relative_to(lib).as_posix()]])


@app.get("/library/<path:name>")
def library_file(name):
    return send_from_directory(ROOT / "assets", name)


@app.get("/api/references")
def references():
    """Inspiration videos: the Opus 5.5 study (research/opus_watch.py) with each prompt and Gemini's analysis."""
    d = ROOT / "research" / "opus-videos"
    watched = {}
    for line in (d / "watched.jsonl").read_text("utf-8").splitlines() if (d / "watched.jsonl").exists() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if "error" not in row:
            watched[row["slug"]] = row
    out = [{**{k: v.get(k) for k in ("slug", "author", "post_url", "category", "tech_tags", "title", "prompt", "prompt_partial", "poster_url")},
            "video": (d / "media" / f"{v['slug']}.mp4").exists(), "analysis": watched.get(v["slug"])}
           for v in jload(d / "videos.json", [])]
    wow = lambda r: (r["analysis"] or {}).get("wow_factor")
    out.sort(key=lambda r: -wow(r) if isinstance(wow(r), (int, float)) else 1)  # best first, unwatched last
    return jsonify(out)


def frontmatter(text):
    """name/description from a SKILL.md header, including folded `description: >` blocks."""
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    meta, key = {}, None
    for line in m.group(1).splitlines() if m else []:
        k = re.match(r"([\w-]+):\s*(.*)", line)
        if k:
            key, value = k.group(1), k.group(2).strip()
            meta[key] = "" if value in (">", "|", ">-", "|-") else value.strip('"')
        elif key and line.startswith(" "):
            meta[key] = (meta[key] + " " + line.strip()).strip()
    return meta


FAMILIES = ("remotion", "hyperframes")  # one pipeline agent ("Remotion") stands for every remotion-* skill


def uses(name, agent):
    word = agent.split()[0]
    return name in agent or (word in FAMILIES and name.startswith(word))


@app.get("/api/skills")
def skills():
    out = []
    for f in sorted(SKILLS.glob("*/SKILL.md")) if SKILLS.exists() else []:
        meta = frontmatter(f.read_text("utf-8", errors="replace"))
        name = meta.get("name") or f.parent.name
        steps = [f"{s}. {n}" for s, n, agents, _ in activity.PIPELINE if any(uses(name.lower(), a.lower()) for a in agents)]
        out.append({"name": name, "description": meta.get("description", ""), "steps": steps})
    return jsonify(out)


@app.get("/api/prompts")
def prompts():
    """The owner's Flow/Kling b-roll prompt bank (prompts/broll.json); generated = the clip is in assets/ai/."""
    bank = jload(ROOT / "prompts" / "broll.json", {"prompts": []})
    ai = ROOT / "assets" / "ai"
    for item in bank.get("prompts", []):
        item["file"] = f"ai/{item['id']}.mp4"
        item["generated"] = (ai / f"{item['id']}.mp4").exists()
    return jsonify(bank)


@app.get("/refs/<path:name>")
def reference_file(name):
    return send_from_directory(ROOT / "research" / "opus-videos" / "media", name)


@app.route("/api/docs/<name>", methods=["GET", "PUT"])
def doc(name):
    if name not in DOC_NAMES:
        return jsonify(error="unknown doc"), 404
    p = DOCS / name
    if request.method == "PUT":
        idle()
        text = body().get("text", "")
        if not isinstance(text, str): raise ValueError("Document text must be a string")
        p.write_text(text, "utf-8")
        return jsonify(ok=True)
    return jsonify(name=name, text=p.read_text("utf-8") if p.exists() else "")


def watch_clips():
    """Owner rule: new recordings in footage/ are indexed automatically (Gemini), never on request."""
    import time
    import research
    retry_at = {}
    while True:
        time.sleep(60)
        if not busy.acquire(blocking=False):
            continue
        try:
            for clip in research.new_clips():
                if retry_at.get(clip.name, 0) > time.time():
                    continue
                try:
                    activity.log("channel", 4, "Gemini", "running", f"auto-indexing {clip.name}")
                    name = research.index_clip(clip)
                    activity.log("channel", 4, "Gemini", "done", f"indexed {clip.name} as {name}")
                    print(f"Auto-indexing {clip.name} -> {name}")
                except Exception as e:  # Gemini quota or file still locked by the recorder: retry later
                    activity.log("channel", 4, "Gemini", "failed", f"{clip.name}: {e}")
                    retry_at[clip.name] = time.time() + 1800
                    print(f"Auto-index of {clip.name} failed, retrying in 30 min: {e}")
        finally:
            busy.release()


if __name__ == "__main__":
    print("Channel dashboard -> http://localhost:7071")
    threading.Thread(target=watch_clips, daemon=True).start()
    app.run("127.0.0.1", 7071, debug=False)
