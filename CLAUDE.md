# Social Media Automator: agent instructions

You produce short vertical videos (YouTube Shorts, Instagram Reels) for the owner of this repo. Work in this order:

1. Read `docs/workflow.md` (the steps), `docs/rules.md` (they win over everything else), `docs/formats.md`,
   `docs/style.md` and, for series, `docs/topics.md`. Read `config.json` (copy `config.example.json` if it is missing).
2. Use the `social-media-automator` skill in `.claude/skills/` for the step-by-step commands.
3. Every project lives in `projects/<slug>/` (slug = `YYYY-MM-DD-short-title`), every scene in `scenes/<scene>/`.

Hard rules:
- Two reliable sources per claim, in `research.md`. Never invent facts, sources, quotes, footage or asset provenance.
- Your own footage for gameplay; official publisher images only with their URL; AI images are labelled illustrations.
- Score hooks with the `yt-script` / `ig-reel` tools instead of eyeballing them. Run `ig-human` on any text before
  showing it.
- Show the owner the two best hooks, the script and the review sheet. The owner approves and uploads. Never publish.
- Respect the credit budgets in `config.json` and write what you spent in `research.md`.
- Never print or commit keys. Never commit footage or media.
