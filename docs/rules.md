# Rules (every Short)

## Facts
- **Two reliable sources per claim**, written into `research.md` before the script is final. A community wiki can be one
  of the two, never the only one. The game, show or product itself (a cutscene, a line of dialogue) counts as a source.
- **Never invent** a number, date, quote, leak or source. If a figure is missing, ask for it or write the line without it.
- **Rumours are rumours.** Say so in the description with the source. Never present a fake as real, and never show
  actual leaked footage (publishers file takedowns).

## Footage and assets
- Use your **own recordings** for gameplay. Publisher trailers and press images only when they are official, with the
  publisher URL in the description.
- **Stickers:** official character art with the background removed, or GIPHY / Tenor stickers. No fan art, no random
  image-search results, no AI likenesses of real people. Log each with its source URL.
- **AI images and clips are illustrations.** Never stamp them REAL or CONFIRMED. Disclose them in the description and tick
  YouTube's "altered or synthetic content" setting.
- **Music:** original or properly licensed tracks only. A copyrighted song can redirect all of a video's ad revenue.
- No on-screen credits clutter: sources, image credits, the footage credit and the AI line go in the description.

## Budgets
- Per Short: Firecrawl at most **20 credits**, Higgsfield at most **15 credits**, at most 6 AI images. Check the asset log
  and reuse before spending. Write what you spent in `research.md`.

## The edit
- Length: **20-30 s** for news / did-you-know / what-if, **30-45 s** for explainers (`config.json`).
- The first frame is the thumbnail: the strongest visual and the hook at 0.0 s, no fade-in, no greeting, no intro.
- A new visual every 2-4 s. One big caption word at a time. A boom on the opening, whooshes on cuts, hits on stickers.
- No game menus, weapon wheels, cut-off subtitles or black letterbox bars on screen (crop them with the spec's
  `keep` / `bars` options).
- End on one personal question that earns comments. One ask, not three.

## Never
- Publish or upload for the owner. Shorts stay private and scheduled until the owner approves them.
- Print or commit API keys. `.env` is git-ignored.
- Commit footage, renders or media. `.gitignore` blocks every video, audio, image and font file.

## The goal behind the rules
YouTube Partner Program (checked 2026-10-31): the ad-revenue tier is 1,000 subscribers plus 10 million qualified Shorts
views in 90 days (or 4,000 long-form watch hours). The YouTube Blog (10 Aug 2026) says new creators will need 20 million
Shorts views in 90 days (or 8,000 watch hours) once the 2027 change starts. Confirm the date in Studio's Earn tab.
Shorts views are hit-driven, so the plan is many shots at formats that produce outliers, then double down on what breaks out.
