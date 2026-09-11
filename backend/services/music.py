import os
import subprocess

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(BASE_DIR, "music")


# ═══════════════════════════════════════════════════════
# SECTION 1 — MUSIC SELECTION
# ═══════════════════════════════════════════════════════

# Style keywords matched against filenames in the music/ folder.
# A file is used if its lowercase name contains the keyword.
# e.g. "nastelbom-upbeat-501716.mp3" matches "upbeat"
STYLE_KEYWORDS = {
    "upbeat":        "upbeat",
    # The calm bed is named "...-soft-background-music-...", so match "soft".
    # Mapping this to "calm" matched no file and silently fell back to upbeat.
    "calm":          "soft",
    "corporate":     "corporate",
    "dramatic":      "dramatic",
    "inspirational": "inspirational",
}

# Fallback priority order if requested style has no matching file
FALLBACK_ORDER = ["upbeat", "corporate", "calm", "inspirational", "dramatic"]


def _find_file_by_keyword(keyword: str) -> str:
    """
    Scans the music/ folder for any MP3 whose filename contains `keyword`.
    Returns the full path if found, empty string otherwise.
    Works with any download-named files — no renaming needed.
    """
    if not os.path.isdir(MUSIC_DIR):
        return ""
    for filename in os.listdir(MUSIC_DIR):
        if keyword.lower() in filename.lower() and filename.lower().endswith(".mp3"):
            full_path = os.path.join(MUSIC_DIR, filename)
            print(f"  🎵 Music matched '{keyword}' → {filename}")
            return full_path
    return ""


def get_music_path(music_style: str) -> str:
    """
    Returns path to a music file matching the requested style.

    How style is chosen:
    - The LLM picks one of: upbeat, calm, corporate, dramatic, inspirational
      based on the ad's tone and brand personality (see script_generator.py).
    - We scan the music/ folder for any MP3 filename containing that keyword.
    - If no match, we try the fallback order until we find something.
    - If still nothing, we skip music entirely (voice-only output).

    This means you can drop any named MP3 into backend/music/ and it will
    be picked up automatically as long as the style keyword is in the filename.
    """
    # Try the requested style first
    keyword = STYLE_KEYWORDS.get(music_style, music_style)
    path = _find_file_by_keyword(keyword)
    if path:
        return path

    print(f"  ⚠️  No music file found for style: '{music_style}' — trying fallbacks")

    # Try fallbacks in priority order
    for fallback in FALLBACK_ORDER:
        if fallback == music_style:
            continue
        fallback_keyword = STYLE_KEYWORDS.get(fallback, fallback)
        path = _find_file_by_keyword(fallback_keyword)
        if path:
            print(f"  🎵 Using fallback style: {fallback}")
            return path

    # Nothing at all in the folder
    print("  ⚠️  No music files found in backend/music/ — skipping music")
    return ""


# ═══════════════════════════════════════════════════════
# SECTION 2 — MUSIC PROCESSING
# ═══════════════════════════════════════════════════════

def prepare_music(
    music_path:  str,
    output_path: str,
    duration:    int,
    volume:      float = 0.15
) -> str:
    """
    Prepares music track for the ad:
    1. Loops it if shorter than ad duration
    2. Trims it to exact ad duration
    3. Fades in at start (0.5s) and out at end (1.5s)
    4. Lowers volume so voiceover is clearly audible

    Why 0.15 volume?
    Music should be background — not competing with voice.
    0.15 = 15% of original volume — subtle but present.
    """
    if not music_path or not os.path.exists(music_path):
        return ""

    print(f"  🎵 Preparing music track...")

    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",      # loop indefinitely
        "-i", music_path,          # input music
        "-t", str(duration),       # trim to ad duration
        "-af", (
            f"volume={volume},"    # reduce volume to 15%
            f"afade=t=in:st=0:d=0.5,"   # fade in over 0.5s
            f"afade=t=out:st={duration-1.5}:d=1.5"  # fade out last 1.5s
        ),
        "-acodec", "libmp3lame",
        "-q:a", "2",
        output_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠️  Music preparation failed: {result.stderr[-200:]}")
        return ""

    print(f"  ✅ Music prepared: {duration}s at {volume*100:.0f}% volume")
    return output_path