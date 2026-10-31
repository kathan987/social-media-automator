# Research method and lessons

## Judge ideas by the multiple, not the views
Raw views rank channel size. The useful number is a video's views divided by the median of its own channel's last 30
Shorts (the `/yt-viral` method). `tools/find_outliers.py <hashtags>` does it with yt-dlp and no API key. A channel median
of 1-15K inflates multiples, so compare ideas, not exact numbers. Search results only show what already did well
(survivorship): flops are invisible.

## What character-lore Shorts that broke out had in common (sample of ~480 Shorts, 2026-10-31)
1. **One specific claim about one character**, not a life summary: "The ONLY reference to ...", "The real reason ...",
   "Hidden skill", "3 small details", "in every chapter".
2. **The real moment on screen at once**: the cutscene or gameplay that proves it, with plain text.
3. **22-54 s** for the strongest ones.
4. **Real-actor and quote angles travel far.** Use public facts only.
5. **Hits cluster in one niche**: one small channel had 7+ Shorts at 28x or more of its own median. Pick a lane and repeat it.

## What a first week of a new Shorts channel taught
- Views follow uploads: the one day with no upload dropped views by ~80%. Post every day.
- 99% of viewers were new and ~0.2% subscribed, so views, not subscribers, were the bottleneck.
- Shorter held better: 27-37 s Shorts kept 57-100% average viewed; 60-70 s ones kept 42-46%.
- Specific titles were found in search (11% of views): name the thing people type.
- "Comment below" earned almost nothing. A one-word, either/or question works better, plus a pinned comment.

## Weekly loop
Screenshot YouTube Studio (Content, Audience, and "viewed vs swiped" per Short) and run `/yt-audit` and `/yt-retention`.
Compare the top and bottom three by hook, length, format and first frame. Write the change into `formats.md` or `style.md`.
