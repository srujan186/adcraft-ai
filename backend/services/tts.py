import os
import asyncio
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR , "models")
TEMP_DIR = os.path.join(BASE_DIR ,"temp")

MODEL_PATH  = os.path.join(MODELS_DIR, "kokoro-v1.0.int8.onnx")
VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

# We load it ONCE when the module is first imported
# Loading takes ~2 seconds — we don't want to reload every request
_kokoro = None


def get_kokoro():
    """
    Returns the Kokoro instance.
    Loads it on first call, reuses on subsequent calls.

    Why global singleton?
    Loading the model takes 2-3 seconds and uses ~200MB RAM.
    Loading once and reusing is much more efficient.
    This pattern is called a singleton.
    """
    global _kokoro

    if _kokoro is None:
        print(" Loading Kokoro TTS model (first time only)...")
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
        print(" Kokoro model loaded")

    return _kokoro

VOICES = {
    "female_warm":         "af_heart",
    "female_professional": "af_bella",
    "male":                "am_adam",
    "female_british":      "bf_emma",
}

# Default voice for ads
DEFAULT_VOICE = "af_heart"

# Synthesis speed. Kokoro's native speed param (not post-processing atempo),
# so pitch stays natural. 1.3x delivered ~3.6 words/sec, which read as rushed
# and still left a music-only tail; 0.95x (~2.86 words/sec) is calm, confident
# and deliberate. The script word budget in script_generator.py is calibrated
# to THIS rate — change one without the other and narration over/under-runs.
DEFAULT_SPEED = 0.95

# SECTION 1 — CORE TTS FUNCTION
# ═══════════════════════════════════════════════════════

def generate_speech_sync(
    text:        str,
    output_path: str,
    voice:       str   = DEFAULT_VOICE,
    speed:       float = DEFAULT_SPEED
) -> str:
    """
    Synchronous speech generation.
    Runs in a thread pool to avoid blocking FastAPI.

    Why sync?
    Kokoro's API is synchronous (not async).
    We wrap it in run_in_executor to make it non-blocking.

    Returns path to generated WAV file.
    """
    print(f" Generating voiceover...")
    print(f" Text: {text[:60]}...")
    print(f" Voice: {voice} | Speed: {speed}")

    kokoro = get_kokoro()

    samples, sample_rate = kokoro.create(
        text,
        voice=voice,
        speed=speed,
        lang="en-us"
    )

    # Save as WAV file
    sf.write(output_path, samples, sample_rate)

    duration = len(samples) / sample_rate
    print(f" Voiceover generated: {duration:.1f}s")

    return output_path


async def generate_voiceover(
    text:        str,
    output_path: str,
    voice:       str   = DEFAULT_VOICE,
    speed:       float = DEFAULT_SPEED
) -> str:
    """
    Async wrapper for speech generation.
    Runs Kokoro in a thread pool so FastAPI stays responsive.

    Why run_in_executor?
    Kokoro is CPU-bound work.
    Running it directly would block ALL other requests.
    Thread pool keeps FastAPI free to handle other requests.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        path = await loop.run_in_executor(
            pool,
            generate_speech_sync,
            text,
            output_path,
            voice,
            speed
        )
    return path

# SECTION 2 — AUDIO PROCESSING
# ═══════════════════════════════════════════════════════

def wav_to_mp3(wav_path: str, mp3_path: str) -> str:
    """
    Convert WAV to MP3 using FFmpeg.

    Why convert?
    Kokoro outputs WAV (uncompressed, large files).
    MP3 is much smaller and works better in videos.
    FFmpeg handles the conversion.
    """
    import subprocess

    command = [
        "ffmpeg", "-y",
        "-i", wav_path,        # input WAV
        "-codec:a", "libmp3lame",  # MP3 encoder
        "-qscale:a", "2",      # quality (0=best, 9=worst)
        mp3_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"WAV to MP3 conversion failed: {result.stderr[-200:]}")

    print(f"  ✅ Converted to MP3: {mp3_path}")
    return mp3_path


def adjust_voiceover_speed(
    audio_path:      str,
    output_path:     str,
    target_duration: float
) -> str:
    """
    Adjusts voiceover speed to fit the ad duration.

    Why needed?
    AI might generate 18 seconds of speech for a 15s ad.
    We speed it up slightly to fit.
    Or slow it down if speech is too fast.

    Uses FFmpeg atempo filter — sounds natural up to 1.5x speed.
    """
    import subprocess
    import soundfile as sf
    import numpy as np

    # Get current duration
    data, sample_rate = sf.read(audio_path)
    current_duration  = len(data) / sample_rate

    if current_duration <= 0:
        raise Exception("Invalid audio duration")

    # Calculate required speed factor
    speed_factor = current_duration / target_duration

    print(f" Audio duration: {current_duration:.1f}s")
    print(f" Target duration: {target_duration:.1f}s")
    print(f" Speed factor: {speed_factor:.2f}x")

    # atempo filter only works between 0.5x and 2.0x
    # For larger changes we chain multiple atempo filters
    if 0.8 <= speed_factor <= 1.25:
        # Small adjustment — single atempo
        atempo_filter = f"atempo={speed_factor:.3f}"
    elif speed_factor > 1.25:
        # Speed up significantly — chain two atempo filters
        # e.g. 1.6x = atempo=1.265,atempo=1.265
        half = speed_factor ** 0.5
        atempo_filter = f"atempo={half:.3f},atempo={half:.3f}"
        print(f" Using chained atempo: {half:.3f}x twice")
    else:
        # Slow down — single atempo
        atempo_filter = f"atempo={max(speed_factor, 0.5):.3f}"

    command = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-filter:a", atempo_filter,
        output_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        # If speed adjustment fails, just use original
        print(f" Speed adjustment failed — using original speed")
        import shutil
        shutil.copy(audio_path, output_path)

    return output_path