"""Find the Shorts in your niche that beat their OWN channel (the /yt-viral method), with yt-dlp and no API key.
  python tools/find_outliers.py hashtag1 hashtag2 ...        e.g. python tools/find_outliers.py arthurmorgan rdr2 rdr2lore
Hashtag pages -> pre-filter on the listing's view count -> look each one up for date + channel -> rank by views over the
median of that channel's last 30 Shorts. No date cutoff (story topics are evergreen); recent ones are flagged R, story-style
titles X. -> research/outliers-<date>.json"""
import datetime
import json
import re
import shutil
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YTDLP = shutil.which("yt-dlp") or "yt-dlp"  # pip install yt-dlp
TAGS = [t.lstrip("#") for t in sys.argv[1:]]
if not TAGS:
    sys.exit(__doc__)
PER_TAG = 80
MIN_LISTED_VIEWS = 30_000   # skip the long tail before paying for a detail lookup
EXPLAINER = re.compile(r"explain|story|life|backstory|origin|history|who is|who was|lore|truth|what happened|"
                       r"tragic|dark|secret|real|actually|before|why|how|ending|death|died|redemption|timeline", re.I)
RECENT = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y%m%d")


def ytdlp(*args, timeout=120):
    out = subprocess.run([YTDLP, *args], capture_output=True, text=True, encoding="utf8", errors="replace", timeout=timeout)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {}


def tag(t):
    try:
        return t, ytdlp("--flat-playlist", "-J", "--playlist-items", f"1:{PER_TAG}", f"https://www.youtube.com/hashtag/{t}/shorts").get("entries") or []
    except subprocess.TimeoutExpired:
        return t, []


def detail(vid):
    try:
        d = ytdlp("-J", "--skip-download", "--no-warnings", f"https://www.youtube.com/shorts/{vid}", timeout=90)
    except subprocess.TimeoutExpired:
        return None
    if not d:
        return None
    return {k: d.get(k) for k in ("id", "title", "view_count", "like_count", "comment_count", "duration", "upload_date",
                                  "channel", "channel_id", "channel_follower_count", "description")}


ids = {}
with ThreadPoolExecutor(6) as pool:
    for t, entries in pool.map(tag, TAGS):
        for e in entries:
            if e.get("id") and (e.get("view_count") or 0) >= MIN_LISTED_VIEWS:
                ids.setdefault(e["id"], []).append(t)
print(len(ids), "ids >=", MIN_LISTED_VIEWS, "listed views from", len(TAGS), "hashtags", flush=True)
with ThreadPoolExecutor(8) as pool:
    rows = [r for r in pool.map(detail, ids) if r and r.get("view_count")]
keep = []
for r in rows:
    r["tags"] = ids[r["id"]]
    r["explainer"] = bool(EXPLAINER.search(r["title"] or ""))
    r["recent"] = (r.get("upload_date") or "") >= RECENT
    if (r.get("duration") or 0) <= 180:
        keep.append(r)


def median(cid):
    try:
        d = ytdlp("--flat-playlist", "-J", "--playlist-items", "1:30", f"https://www.youtube.com/channel/{cid}/shorts")
    except subprocess.TimeoutExpired:
        return cid, None
    views = [e["view_count"] for e in d.get("entries") or [] if e.get("view_count")]
    return cid, statistics.median(views) if len(views) >= 4 else None


with ThreadPoolExecutor(8) as pool:
    medians = dict(pool.map(median, {r["channel_id"] for r in keep if r.get("channel_id")}))
for r in keep:
    r["channel_median"] = medians.get(r["channel_id"])
    base = r["channel_median"] or r.get("channel_follower_count") or 1000
    r["multiple"] = round(r["view_count"] / max(base, 1000), 1)
    r["url"] = "https://www.youtube.com/shorts/" + r["id"]
    r["description"] = (r.get("description") or "")[:300]
keep.sort(key=lambda r: (r["multiple"], r["view_count"]), reverse=True)
out = ROOT / "research" / f"outliers-{datetime.date.today().isoformat()}.json"
out.write_text(json.dumps(keep, indent=1, ensure_ascii=False), "utf8")
print(len(keep), "kept of", len(rows), "->", out.name)
for r in keep[:60]:
    print(f"{r['multiple']:>6}x {r['view_count']:>11,} med {int(r['channel_median'] or 0):>9,} {r['duration'] or 0:>3}s "
          f"{r['upload_date']} {'R' if r['recent'] else ' '}{'X' if r['explainer'] else ' '} | {(r['channel'] or '')[:16]:16} | {(r['title'] or '')[:62]}")
