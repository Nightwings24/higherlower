# Higher or Lower: Space Edition

A "Higher or Lower" guessing game - like higherlowergame.com - where you compare
Google search popularity between astronomy terms (and, once you add them,
Indian internet-brainrot terms). See `PROMPT.md` for the full design spec.

## Project layout

```
data/
  input_words.json   # source word list, by category ("astronomy", "brainrot")
  overrides.json      # manual fixes/additions (image, score, category per word)
  trends_scores.json  # generated: Google Trends popularity per word
  images.json         # generated: Wikipedia image URL per astronomy word
  words.json           # generated: final merged file the game reads
  cache/               # cached API responses so reruns don't refetch
scripts/
  fetch_trends.py      # Google Trends scores (chained batch calibration)
  fetch_images.py      # Wikipedia images for astronomy words
  build_words.py       # merges trends + images + overrides -> data/words.json
site/
  index.html, styles.css, game.js   # the game itself (static, no backend)
```

## Running the data pipeline

```bash
pip3 install --user pytrends requests
python3 scripts/fetch_trends.py     # ~5-8 min, rate-limit friendly, resumable
python3 scripts/fetch_images.py     # ~1-2 min
python3 scripts/build_words.py      # merges everything -> data/words.json
```

Each script caches its raw API responses under `data/cache/`, so if a run
gets interrupted or rate-limited, just rerun the same command - completed
words are skipped.

## Adding your own brainrot words

Add a `"brainrot"` array to `data/input_words.json` alongside `"astronomy"`.
Brainrot words are **not** auto-fetched - supply their score and image
directly via `data/overrides.json`:

```json
{
  "Ravi Kishan": {
    "score": 42,
    "imageUrl": "https://example.com/ravi-kishan.jpg",
    "category": "brainrot"
  }
}
```

Any word that appears only in `overrides.json` is added as a fully manual
entry - you don't need to touch `input_words.json` or rerun the fetch
scripts. Then just rerun:

```bash
python3 scripts/build_words.py
```

## Fixing a specific word's image or score

Add/edit its entry in `data/overrides.json` (same format as above - any
field you set there wins over the auto-fetched value) and rerun
`build_words.py`. No need to redo the Trends/image fetch.

## Playing the game

```bash
python3 -m http.server 8765      # run from the astro/ project root
```

Then open `http://localhost:8765/site/`.

**Controls:** click Higher/Lower, or use ↑/H and ↓/L on the keyboard.
Score resets every time you reload the page; your best-ever streak is
saved locally in the browser. Word order is randomized every run, and a
category filter (All / Astronomy / Brainrot) lets you narrow the pool.
