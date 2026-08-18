#!/usr/bin/env python3
"""
Merge trends_scores.json + images.json + overrides.json into the final
data/words.json consumed by the game front-end.

Run order: fetch_trends.py -> fetch_images.py -> build_words.py

overrides.json format (create it manually as needed), keyed by word:
{
  "Ravi Kishan": {
    "imageUrl": "images/ravi-kishan.jpg",
    "score": 42,
    "category": "brainrot"
  }
}
Any field present in an override replaces the auto-fetched value.
Words present ONLY in overrides.json (not in input_words.json /
trends_scores.json) are added as fully manual entries - this is how you
hand-add a new word without rerunning the pipeline.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "input_words.json"
TRENDS_PATH = ROOT / "data" / "trends_scores.json"
IMAGES_PATH = ROOT / "data" / "images.json"
OVERRIDES_PATH = ROOT / "data" / "overrides.json"
OUTPUT_PATH = ROOT / "data" / "words.json"


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def main():
    input_words = load_json(INPUT_PATH, {})
    trends = load_json(TRENDS_PATH, {})
    images = load_json(IMAGES_PATH, {})
    overrides = load_json(OVERRIDES_PATH, {})

    category_by_word = {}
    for category, words in input_words.items():
        for w in words:
            category_by_word[w] = category

    all_words = set(category_by_word) | set(overrides)

    entries = []
    skipped = []

    for word in sorted(all_words):
        override = overrides.get(word, {})
        category = override.get("category") or category_by_word.get(word)

        score = override.get("score")
        if score is None and word in trends:
            score = round(trends[word]["score"], 1)

        image_url = override.get("imageUrl")
        if image_url is None and word in images:
            image_url = images[word]["imageUrl"]

        if category is None or score is None or image_url is None:
            skipped.append((word, category, score, image_url))
            continue

        entries.append({
            "word": word,
            "category": category,
            "score": score,
            "imageUrl": image_url,
        })

    OUTPUT_PATH.write_text(json.dumps(entries, indent=2))
    print(f"Wrote {len(entries)} complete entries to {OUTPUT_PATH}")

    if skipped:
        print(f"\n{len(skipped)} words skipped (missing category/score/image):")
        for word, category, score, image_url in skipped:
            missing = []
            if category is None:
                missing.append("category")
            if score is None:
                missing.append("score")
            if image_url is None:
                missing.append("imageUrl")
            print(f"  - {word}: missing {', '.join(missing)}")
        print("\nFix these via data/overrides.json, e.g.:")
        print('  { "WordName": { "score": 50, "imageUrl": "...", "category": "..." } }')


if __name__ == "__main__":
    main()
