#!/usr/bin/env python3
"""
Fetch Google Trends popularity scores for the word list using CHAINED batch
calibration instead of a single fixed anchor.

Why not a fixed anchor: pytrends compares up to 5 terms per request on a
0-100 scale relative to the batch's peak. If every batch includes one very
dominant anchor (e.g. "space"), niche words get rounded down to 0 in nearly
every batch -- there's not enough numeric resolution left for them.

Instead: words are pre-sorted into rough fame tiers (TIERS below, hand-
judged), most-famous first. Batches of 5 are formed by sliding a 1-word
overlap ("bridge") between consecutive batches, so every batch only ever
compares words of *similar* popularity to each other -- preserving
resolution -- and the bridge word lets us rescale each batch onto one
running global scale.

Global score for a new batch = raw_score_in_batch * (bridge_global_score /
bridge_raw_score_in_batch).

Caches raw batch responses to data/cache/trends2/ so a failed/interrupted
run can resume without re-fetching batches already completed.
"""
import json
import sys
import time
import hashlib
from pathlib import Path

from pytrends.request import TrendReq

TIMEFRAME = "today 12-m"
REQUEST_DELAY_SECONDS = 10
MAX_RETRIES = 5

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "input_words.json"
CACHE_DIR = ROOT / "data" / "cache" / "trends2"
OUTPUT_PATH = ROOT / "data" / "trends_scores.json"

# Hand-judged rough fame tiers, most famous first. Order within a tier
# doesn't matter much -- only the overall gradient across tiers does, since
# it keeps neighboring batches close in popularity.
TIERS = [
    # Tier 1: universally known
    ["Sun", "Moon", "Earth", "Mars", "Jupiter", "Saturn", "NASA", "Rocket",
     "Telescope", "Gravity", "Astronaut", "Universe", "Orbit", "Black Hole",
     "Solar System"],
    # Tier 2: common pop-science / school level
    ["Mercury", "Venus", "Uranus", "Neptune", "Pluto", "Milky Way", "Big Bang",
     "Solar Eclipse", "Lunar Eclipse", "Comet", "Meteor Shower",
     "Aurora Borealis", "Space Station", "International Space Station",
     "Elon Musk", "Albert Einstein", "Neil Armstrong", "Stephen Hawking",
     "SpaceX", "Satellite", "Nebula", "Supernova", "Sirius", "Moon Landing",
     "ISRO"],
    # Tier 3: known to a curious first-year-university audience
    ["Andromeda Galaxy", "Hubble Space Telescope", "James Webb Space Telescope",
     "Voyager 1", "Voyager 2", "Apollo 11", "Sputnik", "Yuri Gagarin",
     "Galileo Galilei", "Carl Sagan", "Kalpana Chawla", "Sunita Williams",
     "Rakesh Sharma", "Asteroid Belt", "Solar Flare", "Space Shuttle",
     "Space Race", "Mars Rover", "Curiosity Rover", "Falcon 9", "Starlink",
     "Chandrayaan-3", "Orion", "Big Dipper", "Ursa Major", "Dark Matter",
     "Exoplanet", "Light Year", "Shooting Star", "Space Tourism", "Starship"],
    # Tier 4: moderately niche / space-enthusiast level
    ["Titan", "Europa", "Ganymede", "Io", "Callisto", "Wormhole",
     "Neutron Star", "White Dwarf", "Red Giant", "Event Horizon", "Scorpius",
     "Leo", "Taurus", "Gemini", "Sagittarius", "Cassiopeia", "Pegasus",
     "Great Red Spot", "Rings of Saturn", "Chandrayaan-2", "Chandrayaan-1",
     "Perseverance Rover", "New Horizons", "Cassini", "Juno", "Artemis",
     "Blue Origin", "ESA", "Betelgeuse", "Polaris", "Planetarium"],
    # Tier 5: niche / technical
    ["Proxima Centauri", "Alpha Centauri", "Rigel", "Vega", "Antares",
     "Aldebaran", "Arcturus", "Canopus", "Phobos", "Deimos", "Triton",
     "Enceladus", "Ceres", "Eris", "Makemake", "Whirlpool Galaxy",
     "Sombrero Galaxy", "Triangulum Galaxy", "Large Magellanic Cloud",
     "Kuiper Belt", "Oort Cloud", "Gravitational Waves", "Sunspot",
     "Mangalyaan", "Gaganyaan", "Aditya-L1", "Halley's Comet", "Dark Energy"],
]


def build_ordered_words():
    ordered = [w for tier in TIERS for w in tier]
    input_words = json.loads(INPUT_PATH.read_text())["astronomy"]
    ordered_set, input_set = set(ordered), set(input_words)
    assert ordered_set == input_set, (
        f"TIERS/input mismatch. Missing from TIERS: {input_set - ordered_set}. "
        f"Extra in TIERS: {ordered_set - input_set}."
    )
    assert len(ordered) == len(set(ordered)), "duplicate word in TIERS"
    return ordered


def batch_cache_key(words):
    return hashlib.sha256("|".join(words).encode()).hexdigest()[:16]


def fetch_batch(pytrends, words):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pytrends.build_payload(words, timeframe=TIMEFRAME)
            df = pytrends.interest_over_time()
            if df.empty:
                raise RuntimeError("empty response")
            maxes = df[words].max()
            return {w: float(maxes[w]) for w in words}
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = REQUEST_DELAY_SECONDS * attempt
            print(f"  batch failed (attempt {attempt}/{MAX_RETRIES}): {e} "
                  f"— retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"batch permanently failed after {MAX_RETRIES} attempts: {last_err}")


def get_batch(pytrends, words):
    cache_file = CACHE_DIR / f"{batch_cache_key(words)}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    scores = fetch_batch(pytrends, words)
    cache_file.write_text(json.dumps(scores, indent=2))
    time.sleep(REQUEST_DELAY_SECONDS)
    return scores


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ordered = build_ordered_words()
    print(f"Loaded {len(ordered)} words across {len(TIERS)} tiers")

    pytrends = TrendReq(hl="en-US", tz=360)

    global_scores = {}

    # First batch: 5 words, establishes the baseline scale (100 = its own peak).
    first_batch = ordered[:5]
    print(f"[1] baseline batch: {first_batch}")
    raw = get_batch(pytrends, first_batch)
    for w in first_batch:
        global_scores[w] = raw[w]

    bridge = first_batch[-1]
    i = 5
    batch_num = 2
    while i < len(ordered):
        new_words = ordered[i:i + 4]
        batch = [bridge] + new_words
        print(f"[{batch_num}] batch: {batch}")
        raw = get_batch(pytrends, batch)

        bridge_raw = raw[bridge]
        if bridge_raw <= 0:
            # Degenerate batch (shouldn't happen often given tiered ordering).
            # Fall back to carrying the bridge's existing global score forward
            # unscaled, rather than dividing by zero.
            print(f"  WARNING: bridge '{bridge}' scored 0 in this batch, "
                  f"using scale factor 1.0", file=sys.stderr)
            scale = 1.0
        else:
            scale = global_scores[bridge] / bridge_raw

        for w in new_words:
            global_scores[w] = raw[w] * scale

        bridge = new_words[-1] if new_words else bridge
        i += 4
        batch_num += 1

    OUTPUT_PATH.write_text(json.dumps(
        {w: {"category": "astronomy", "score": global_scores[w]} for w in ordered},
        indent=2, sort_keys=True,
    ))
    print(f"\nWrote {len(global_scores)} scores to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
