"""Who is doing what. Every agent appends one line per status change to activity.jsonl at the channel root;
the dashboard's Agents page shows it live (refreshes every 3 s).

  python dashboard/activity.py <video-slug|channel> <step> "<agent>" <running|done|failed|skipped> ["detail"]

Dashboard steps (draft, voice, render, publish), research.py and gameplay auto-indexing log themselves.
Claude logs the rest (Firecrawl, Agent-Reach, Higgsfield, the yt-* skills, motion engines) with the command above.
"""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUSES = ("running", "done", "failed", "skipped")
# The pipeline (docs/skills.md): (step, name, agents, budget / rule shown on the board)
PIPELINE = [
    (0, "Plan the week", ["Claude /yt-plan", "content-matrix", "voice-builder"], "7 news + 7 what-if + 4 did-you-know a week"),
    (1, "Find what's viral", ["research.py swipe", "/yt-viral swipe.py", "Gemini", "Agent-Reach", "Firecrawl"], "Firecrawl ≤ 10 credits"),
    (2, "News and leaks", ["niche-research", "Agent-Reach", "Firecrawl", "Claude"], "Firecrawl ≤ 10 credits · 2 sources per claim"),
    (3, "Script", ["/yt-script hookscore.py", "hook-generator", "/yt-shorts", "reels-scripting", "Claude", "Gemini"], "5 hooks scored · 20-30 s · mood tags"),
    (4, "Assets", ["Asset library", "Firecrawl", "Higgsfield", "GIPHY", "Pixabay", "Gemini"], "Higgsfield ≤ 15 credits · log in assets.md"),
    (5, "Motion graphics", ["motion-playbook", "HyperFrames + GSAP", "media-use", "Remotion", "Motion Canvas"], "full-screen kind: motion · storyboard + stills first"),
    (6, "Voice", ["ElevenLabs"], "eleven_v4 with mood tags"),
    (7, "Assemble", ["Renderer", "FFmpeg", "video-use"], "a cut every 2-3 s · no on-screen credits"),
    (8, "Virality check + package", ["Gemini", "/yt-package title.py", "/yt-seo", "pinned-comment", "Higgsfield"], "Gemini score before upload"),
    (9, "Publish", ["Owner"], "owner approves and uploads"),
    (10, "Learn", ["/yt-retention", "/yt-audit", "/yt-comment", "post-scorer", "Gemini"], "score the live Short"),
]
STEPS = {s[0] for s in PIPELINE}
# Plain-language guide for the Agents page: what each step does, why, what goes in and what comes out.
GUIDE = {
    0: ("Decide which Shorts to make this week, spread over the formats.", "A plan beats random uploads: one Short a day keeps the channel growing.",
        "Channel goals, last week's results", "A topic list (docs/topics.md)"),
    1: ("Look at which Shorts in your niche are blowing up right now, ranked by how far each beat its own channel's normal views.",
        "Copy formats that already work instead of guessing.", "Public YouTube listings", "A swipe file of winning formats (research/)"),
    2: ("Find today's real news and check every claim against two reliable sources.",
        "One wrong 'fact' kills trust. Leaks are allowed only when they are labelled.", "News sites, Reddit, X", "Verified claims, two source links each"),
    3: ("Write five hooks, score them, keep the best, then write a 20-30 s script with voice mood tags like [excited].",
        "The first 2 seconds decide whether people swipe away.", "Verified claims, viral formats", "Shots with narration (project.json)"),
    4: ("Collect everything that goes on screen: official images and trailer clips, memes, stock, AI clips and your gameplay.",
        "Real proof on screen makes a Short believable.", "The script's shots", "Files in the project's assets/, logged in assets.md"),
    5: ("Build animated scenes such as counters, calendars and stamps over real gameplay.",
        "Moving numbers hold attention better than still text.", "Numbers and facts from the script", "Motion scenes (m-*.mp4)"),
    6: ("ElevenLabs reads the script with emotion and returns the timing of every word.",
        "Word timings let the one-word captions land exactly on the voice.", "Narration", "vo.mp3 + captions.json"),
    7: ("The renderer stacks it all: proof on top, gameplay below, one-word captions, topic badge, arrows, sound effects and the mood ending.",
        "This is where the editing standard is enforced.", "Shots, voice, gameplay clips, sounds", "final.mp4 (20-30 s, 1080x1920)"),
    8: ("Gemini scores the finished Short, then the title, description, tags and pinned comment are written.",
        "Packaging decides who clicks; the score catches weak edits before upload.", "final.mp4", "Title, description with sources, tags, pinned comment"),
    9: ("You watch, approve and upload. The agent never publishes on its own.",
        "A person signs off on everything that goes public.", "Approved final.mp4 + text", "A private, scheduled YouTube Short"),
    10: ("After it is live: read retention, swipe rate and comments, and feed the lessons into the next plan.",
         "This loop is how the channel gets past 300 views.", "YouTube Studio numbers", "Lessons in docs/, a better next Short"),
}
AGENT_INFO = {
    "Claude": "The main agent: researches, writes, edits and checks everything.",
    "Claude /yt-plan": "Claude plans the week's topics with the yt-plan skill.",
    "content-matrix": "Skill that spreads topics across formats so the week is not repetitive.",
    "voice-builder": "Skill that keeps the channel's voice and wording consistent.",
    "research.py swipe": "Script that ranks viral Shorts by how far they beat their channel's median.",
    "/yt-viral swipe.py": "The same ranking, run through the yt-viral skill.",
    "Gemini": "Google's AI: watches videos, scores Shorts, indexes gameplay. Free tier, with daily limits.",
    "Agent-Reach": "Reads Reddit threads, YouTube transcripts and X posts.",
    "Firecrawl": "Searches and reads web pages. Budget: 20 credits per Short.",
    "niche-research": "Skill that finds what your audience is talking about.",
    "/yt-script hookscore.py": "Scores hook lines against 21 proven hook formulas.",
    "hook-generator": "Skill that writes hook options.",
    "/yt-shorts": "Skill that checks the Short's structure, loop and pacing.",
    "reels-scripting": "Skill for short-form script structure.",
    "Asset library": "The shared folder of images, memes, sounds and clips (assets/).",
    "Higgsfield": "AI image and video generator. Budget: 15 credits per Short.",
    "GIPHY": "Reaction memes: WASTED, shocked, press X to doubt and more.",
    "Pixabay": "Free stock videos and images, commercial use allowed.",
    "motion-playbook": "The channel's rules for motion scenes.",
    "HyperFrames + GSAP": "Turns HTML animations into video frames.",
    "media-use": "Skill that picks the right media source for each shot.",
    "Remotion": "React-based video engine, the backup motion tool.",
    "Motion Canvas": "Code-based animation tool, another backup.",
    "ElevenLabs": "AI voice with emotion tags and word timings.",
    "Renderer": "The channel's own editor (workflow.py) that builds final.mp4.",
    "FFmpeg": "Cuts, converts and checks video and audio.",
    "video-use": "Skill with video editing helpers.",
    "/yt-package title.py": "Checks title length, wording and the thumbnail-text pairing.",
    "/yt-seo": "Writes the description, tags and search text.",
    "pinned-comment": "Skill that writes the pinned comment that starts a discussion.",
    "Owner": "You. Approve and upload: nothing goes public without you.",
    "/yt-retention": "Reads where viewers drop off.",
    "/yt-audit": "Audits the channel's packaging and consistency.",
    "/yt-comment": "Drafts replies to comments.",
    "post-scorer": "Skill that scores a post against what performed before.",
    "Dashboard": "This app, logging its own updates.",
}


def log(video, step, agent, status, detail=""):
    if int(step) not in STEPS or status not in STATUSES or not str(agent).strip():
        raise ValueError(f"step must be one of {sorted(STEPS)}, status one of {STATUSES}, agent non-empty")
    entry = {"at": dt.datetime.now().isoformat(timespec="seconds"), "video": str(video or "channel"),
             "step": int(step), "agent": str(agent).strip(), "status": status, "detail": str(detail)[:300]}
    # ponytail: one appended line per event, no lock; move to SQLite if two writers ever interleave lines
    with (ROOT / "activity.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def board(limit=1000):
    path = ROOT / "activity.jsonl"
    lines = path.read_text("utf-8").splitlines()[-limit:] if path.exists() else []
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except ValueError:  # a half-written line from a crashed writer: skip it
            continue
    latest = {}  # (video, step, agent) -> newest entry
    for e in entries:
        latest[(e["video"], e["step"], e["agent"])] = e
    return {"pipeline": [{"step": s, "name": n, "agents": a, "rule": r, **dict(zip(("what", "why", "input", "output"), GUIDE[s]))}
                         for s, n, a, r in PIPELINE],
            "agent_info": AGENT_INFO,
            "now": [e for e in latest.values() if e["status"] == "running"],
            "latest": list(latest.values()), "feed": entries[-40:][::-1]}


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    print(log(*sys.argv[1:]))
