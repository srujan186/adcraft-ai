"""P0-7 guard: seeded inventory names must not use (or imitate) real media brands."""
import json
import re
from pathlib import Path

from app import cli

SEED = Path(cli.__file__).resolve().parents[2] / "seed" / "channels.json"

# Real streaming / TV brands and their distinctive marks. Word-boundary, case-insensitive.
BRANDS = [
    "netflix", "hulu", "disney", "magic kingdom", "espn", "sportscenter", "max", "hbo", "peacock", "paramount",
    "pluto", "tubi", "roku", "sling", "fubo", "philo", "youtube", "prime video", "apple tv", "freevee", "xumo",
    "crackle", "plex", "vizio", "samsung tv", "spectrum", "xfinity", "comcast", "directv", "discovery", "warner",
    "showtime", "starz", "amc", "tbs", "tnt", "nbc", "cbs", "abc", "fox", "cnn", "msnbc", "pbs", "bravo",
    "hgtv", "tlc", "mtv", "nickelodeon", "cartoon network", "telemundo", "univision", "bloomberg", "a&e",
]


def _names():
    data = json.loads(SEED.read_text(encoding="utf-8"))
    yield from (c["name"] for c in data["named"])
    yield from cli._FILLER_PREFIX
    for nouns in cli._CAT_NOUN.values():
        yield from nouns


def test_no_seeded_channel_name_uses_a_real_media_brand():
    pattern = re.compile(r"\b(" + "|".join(re.escape(b) for b in BRANDS) + r")\b", re.IGNORECASE)
    offenders = [n for n in _names() if pattern.search(n)]
    assert offenders == [], offenders
