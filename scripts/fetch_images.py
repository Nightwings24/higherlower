#!/usr/bin/env python3
"""
Fetch a representative image for each astronomy word via the Wikipedia
REST API (page summary thumbnail). Words with no match, a disambiguation
page, or no thumbnail are logged so they can be fixed via overrides.json.

Brainrot-category words are skipped entirely - those images are supplied
manually via overrides.json.
"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "input_words.json"
CACHE_DIR = ROOT / "data" / "cache" / "images"
OUTPUT_PATH = ROOT / "data" / "images.json"

# Wikipedia page titles for words whose plain name is ambiguous or a
# disambiguation page (e.g. "Mercury" the planet vs. the element/god).
TITLE_OVERRIDES = {
    "Mercury": "Mercury (planet)",
    "Ceres": "Ceres (dwarf planet)",
    "Eris": "Eris (dwarf planet)",
    "Europa": "Europa (moon)",
    "Titan": "Titan (moon)",
    "Ganymede": "Ganymede (moon)",
    "Io": "Io (moon)",
    "Callisto": "Callisto (moon)",
    "Phobos": "Phobos (moon)",
    "Deimos": "Deimos (moon)",
    "Triton": "Triton (moon)",
    "Orion": "Orion (constellation)",
    "Leo": "Leo (constellation)",
    "Cassiopeia": "Cassiopeia (constellation)",
    "Gemini": "Gemini (constellation)",
    "Taurus": "Taurus (constellation)",
    "Sagittarius": "Sagittarius (constellation)",
    "Perseverance Rover": "Perseverance (rover)",
    "Cassini": "Cassini–Huygens",
    "Juno": "Juno (spacecraft)",
    "Blue Origin": "Blue Origin",
    "White Dwarf": "White dwarf",
    "Shooting Star": "Meteoroid",
}

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
HEADERS = {"User-Agent": "higher-lower-space-game/1.0 (educational project)"}
REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 5


def load_astronomy_words():
    data = json.loads(INPUT_PATH.read_text())
    return data.get("astronomy", [])


def fetch_summary(word):
    lookup_title = TITLE_OVERRIDES.get(word, word)
    cache_file = CACHE_DIR / (word.replace("/", "_") + ".json")
    if cache_file.exists():
        cached = json.loads(cache_file.read_text())
        # Retry cached failures except when we now have a better title to try.
        if (cached.get("ok") or cached.get("status") != 429) and word not in TITLE_OVERRIDES:
            return cached

    url = WIKI_API.format(urllib.parse.quote(lookup_title))
    resp = None
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 429:
            break
        wait = 5 * attempt
        print(f"  429 on {word}, retrying in {wait}s ({attempt}/{MAX_RETRIES})", file=sys.stderr)
        time.sleep(wait)

    if resp.status_code != 200:
        result = {"ok": False, "status": resp.status_code}
    else:
        payload = resp.json()
        if payload.get("type") == "disambiguation":
            result = {"ok": False, "status": "disambiguation"}
        else:
            thumb = payload.get("thumbnail", {}).get("source")
            original = payload.get("originalimage", {}).get("source")
            if not thumb and not original:
                result = {"ok": False, "status": "no_image"}
            else:
                result = {
                    "ok": True,
                    "imageUrl": original or thumb,
                    "title": payload.get("title"),
                    "pageUrl": payload.get("content_urls", {})
                    .get("desktop", {})
                    .get("page"),
                }
    cache_file.write_text(json.dumps(result, indent=2))
    return result


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    words = load_astronomy_words()
    print(f"Fetching images for {len(words)} astronomy words")

    results = {}
    missing = []

    for i, word in enumerate(words, 1):
        r = fetch_summary(word)
        if r.get("ok"):
            results[word] = {"imageUrl": r["imageUrl"], "source": "wikipedia"}
            print(f"[{i}/{len(words)}] OK   {word}")
        else:
            missing.append((word, r.get("status")))
            print(f"[{i}/{len(words)}] MISS {word} ({r.get('status')})")
        time.sleep(REQUEST_DELAY_SECONDS)

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(f"\nWrote {len(results)} images to {OUTPUT_PATH}")

    if missing:
        print(f"\n{len(missing)} words need a manual image override:", file=sys.stderr)
        for word, status in missing:
            print(f"  - {word} ({status})", file=sys.stderr)


if __name__ == "__main__":
    main()
