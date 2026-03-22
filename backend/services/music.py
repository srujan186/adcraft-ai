import os
import subprocess

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(BASE_DIR, "music")


# ═══════════════════════════════════════════════════════
# SECTION 1 — MUSIC SELECTION
# ═══════════════════════════════════════════════════════

# Maps music style to filename
MUSIC_FILES = {
    "upbeat":        "upbeat.mp3",
    "calm":          "calm.mp3",
    "corporate":     "corporate.mp3",
    "dramatic":      "dramatic.mp3",
    "inspirational": "inspirational.mp3",
}

# Fallback order if a file is missing
FALLBACK_ORDER = ["upbeat", "corporate", "calm", "inspirational", "dramatic"]


def get_music_path(music_style: str) -> str:
    """
    Returns path to music file for given style.
    Falls back to other styles if requested file missing.
    Returns empty string if NO music files exist at all.
    """
    # Try requested style first
    if music_style in MUSIC_FILES:
        path = os.path.join(MUSIC_DIR, MUSIC_FILES[music_style])
        if os.path.exists(path):
            print(f" Music selected: {music_style} ({path})")
            return path
        else:
            print(f" Music file missing: {MUSIC_FILES[music_style]}")

    # Try fallbacks
    for fallback in FALLBACK_ORDER:
        if fallback == music_style:
            continue
        path = os.path.join(MUSIC_DIR, MUSIC_FILES[fallback])
        if os.path.exists(path):
            print(f"  🎵 Using fallback music: {fallback}")
            return path

    # No music files at all
    print("  No music files found in music/ folder")
    print("  Add MP3 files to backend/music/ folder")
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