# Footage library

Index of your own recordings in `../footage/`, one entry per clip, so the agent can pick the right clip. While the
dashboard runs, Gemini indexes every new recording here automatically (`python dashboard/research.py index-clips` does
it by hand). Keep each heading equal to the file path under `footage/`.

Rules:
- Name files with a game or topic code first (`rdr2-horse-ride.mp4`); the dashboard groups clips by it.
- Never label a clip as something it is not.
- Note menus, pause screens, subtitles and letterbox bars so they are cropped or skipped.

## Entry template (copy per clip)

### clips/<code>-<what-happens>.mp4
- Game: <name>
- Length: mm:ss
- What happens: one or two plain sentences
- Best moments: timecodes + what each is
- Kind: crash | fail | chase | scenic | cutscene · Mood: funny | tense | epic | calm
- Ending: bad | good (if it works as a mood ending)
- Never use: timecodes with menus or desktop
- Used in:

---

## Entries
