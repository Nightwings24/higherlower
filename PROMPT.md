# Build Prompt: "Higher or Lower" - Space Edition

## Concept
A "Higher or Lower" web game (like HigherLowest.com) where players guess whether
one term is more or less searched on Google than another.

**Word bank: 150 words total**
- 130 astronomy/space terms - drafted and saved at `data/input_words.json`
  under the `"astronomy"` key. Pitched at first-year university student
  knowledge level: recognizable planets/moons/stars/missions/phenomena,
  not deep-cut niche terms.
- 20 "brainrot" terms - Indian-themed internet slang/viral figures, kept
  recent/current (e.g. "Ravi Kishan"). To be added by the user under a
  `"brainrot"` key in the same `input_words.json` file. This subset should
  be refreshed periodically since internet slang/virality dates quickly.

## Architecture: two separate phases

### Phase 1 - Offline data pipeline (run once, not at request time)
A standalone Python script that, given a word list, produces a single JSON file
of `{ word, category, score, imageUrl }` records. This is NOT called live by
the game.

**Popularity scores (Google Trends via pytrends):**
- pytrends compares max 5 terms per request, and scores (0–100) are only
  relative *within that batch* - not comparable across batches.
- Fix: every batch of 5 includes one fixed anchor term (e.g. "space") plus
  4 words from the list. Normalize each word's score against the anchor's
  score in that batch, so all words end up on one consistent scale.
- Use "past 12 months" timeframe, worldwide.
- Add delay/retry/backoff between requests - pytrends scrapes Trends and
  will get rate-limited/blocked if hit too fast.
- Cache raw responses so a failed run can resume instead of restarting.

**Images:**
- Astronomy terms: fetched automatically via the Wikipedia/Wikimedia REST API
  (`/page/summary/{title}`) - free, no key, usually has a thumbnail for
  planets, missions, telescopes, phenomena, etc. Script logs/flags any
  astronomy word that comes back with no image, for manual follow-up.
- Brainrot terms: NOT fetched automatically. This subset is small (~10% of
  the list), so images are hand-picked/uploaded manually and referenced by
  filename/path in the word list input (or added directly to `words.json`
  after the automated pass runs on the astronomy terms only).

**Output:** `data/words.json`, one array of objects, e.g.:
```json
{ "word": "Betelgeuse", "category": "astronomy", "score": 34, "imageUrl": "..." }
```

### Phase 1.5 - Manual override / admin editing
Since automated fetching won't be perfect for every word (missing/wrong
images especially for brainrot terms, occasionally odd Trends scores), the
pipeline needs a lightweight way to hand-edit `words.json` after generation
without re-running the whole fetch:
- **Override a word's image**: a simple `overrides.json` (or a small local
  admin script/page) keyed by word, e.g. `{ "Ravi Kishan": { "imageUrl":
  "images/ravi-kishan.jpg" } }`. The pipeline applies overrides after the
  automated fetch, so reruns don't clobber manual fixes.
- **Add a new word manually**: append an entry directly (with word, category,
  and either an auto-fetched or manually-supplied score/image) - either by
  adding it to the input word list before a pipeline run (auto-fetches score
  + image if astronomy), or by hand-adding a fully custom entry straight into
  `words.json`/`overrides.json` for brainrot terms or anything the pipeline
  can't resolve.
- Since `words.json` is plain JSON, this can just be direct file editing -
  no need for a full admin UI unless you want one later.

### Phase 2 - The actual game (static site)
Plain HTML/CSS/JS, reads `data/words.json` at load time (no live API calls,
no backend).

**Game loop (chain mechanic):**
1. Two cards shown side by side - left card (image + name + score revealed)
   and right card (image + name, score hidden).
2. Player picks whether the right card's search score is Higher or Lower
   than the left card's.
3. Reveal the right card's score:
   - Correct → the right card slides into the left position (its score now
     revealed), a new random word slides in on the right with its score
     hidden, and points +1. The chain continues.
   - Incorrect → game over, show final score, offer restart.
4. Never repeat a word within the same run; pick randomly from the pool
   (astronomy + brainrot mixed together) each round.

**Visual design:** take layout/UI inspiration from higherlowergame.com -
full-bleed left/right image cards, center VS divider with Higher/Lower
buttons, score counter, and the slide/reveal transition style.

**Nice-to-haves (optional, only if you want them):**
- Local high-score (localStorage), no backend needed.
- Simple CSS animations for the slide-in of the next card and the
  reveal/compare moment.

## Status
- ✅ Word list drafted: 130 astronomy terms saved at `data/input_words.json`.
- ⬜ 20 Indian-brainrot terms - to be added by the user under a `"brainrot"`
  key in the same file (see README.md for the override workflow).
- ✅ Data pipeline built (`scripts/fetch_trends.py`, `fetch_images.py`,
  `build_words.py`). Trends fetching uses chained batch calibration (see
  script docstring) instead of a single dominant anchor, since anchoring
  everything to one popular term flattened ~36% of niche words to a tied
  score of 0 - chaining cut that down to ~11.5%.
- ✅ `data/words.json` generated: all 130 astronomy words have a score and
  a working image (spot-checked; a couple of ambiguous Wikipedia titles
  needed manual `TITLE_OVERRIDES` in `fetch_images.py`, and one word -
  Blue Origin - needed a manual `data/overrides.json` image entry).
- ✅ Game front-end built at `site/` (plain HTML/CSS/JS, no backend).
  Deep-space "signal telemetry" visual design; chain mechanic; random
  word order with no immediate repeats; score resets on reload, best
  streak persisted via localStorage; category filter (All/Astronomy/
  Brainrot, auto-populated from whatever categories exist in the data);
  synthesized sound effects (no external audio assets); share button
  (Web Share API with clipboard fallback); keyboard shortcuts (↑/H,
  ↓/L); tie handling (equal scores count as correct either way).
- Not yet done: no automated browser screenshot was taken (no headless
  browser available in this sandbox) - code was verified via syntax/
  structural checks and should be visually confirmed in a real browser.
