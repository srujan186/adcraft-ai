# services/video_assembler.py
# ONE job: assemble all assets into a finished video ad
# Uses FFmpeg for all video processing

import os
import uuid
import subprocess
import asyncio
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from services.tts   import generate_voiceover, wav_to_mp3, adjust_voiceover_speed
from services.music import get_music_path, prepare_music

load_dotenv()

# Base directories
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR   = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Video settings
VIDEO_WIDTH  = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS    = 30


# ═══════════════════════════════════════════════════════
# SECTION 1 — HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def generate_id() -> str:
    """Generate a unique ID for each render job."""
    return str(uuid.uuid4())[:8]


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple.
    "#38BDF8" → (56, 189, 248)
    PIL uses RGB tuples, not hex strings.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    """
    Convert hex color to RGBA tuple with alpha.
    "#38BDF8", 180 → (56, 189, 248, 180)
    Alpha 0 = transparent, 255 = fully opaque.
    """
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)


def run_ffmpeg(command: list) -> bool:
    """
    Run an FFmpeg command and wait for it to complete.
    FFmpeg returns 0 on success, non-zero on failure.
    """
    print(f"  🎬 FFmpeg: {' '.join(command[:5])}...")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        error = result.stderr[-500:] if result.stderr else "Unknown error"
        raise Exception(f"FFmpeg failed:\n{error}")

    return True


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.Draw,
    max_width: int
) -> str:
    """
    Wraps text to fit within max_width pixels.
    PIL doesn't auto-wrap — we do it manually word by word.
    """
    words        = text.split()
    lines        = []
    current_line = []

    for word in words:
        test_line  = " ".join(current_line + [word])
        bbox       = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# SECTION 2 — ASSET CREATORS
# Each function creates ONE visual element
# ═══════════════════════════════════════════════════════

def create_overlay_image(
    width:       int,
    height:      int,
    color:       str,
    alpha:       int,
    output_path: str
) -> str:
    """
    Creates a semi-transparent color overlay PNG.
    Placed over background video to make text readable.
    """
    rgba = hex_to_rgba(color, alpha)
    img  = Image.new("RGBA", (width, height), rgba)
    img.save(output_path, "PNG")
    print(f" Overlay created: {color} alpha={alpha}")
    return output_path


def create_text_image(
    text:        str,
    width:       int,
    height:      int,
    font_size:   int,
    text_color:  str,
    output_path: str,
    bold:        bool = False,
    align:       str  = "center"
) -> str:
    """
    Creates a transparent PNG with text on it.
    We use Pillow instead of FFmpeg drawtext for better
    font control, text wrapping, and cross-platform rendering.
    """
    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font       = None
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/verdana.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()
        print(f"Using default font")

    color_rgb    = hex_to_rgb(text_color)
    wrapped_text = wrap_text(text, font, draw, width - 80)

    bbox        = draw.textbbox((0, 0), wrapped_text, font=font)
    text_width  = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width  - text_width)  // 2
    y = (height - text_height) // 2

    shadow_offset = max(2, font_size // 20)
    draw.multiline_text(
        (x + shadow_offset, y + shadow_offset),
        wrapped_text,
        font=font,
        fill=(0, 0, 0, 120),
        align=align
    )
    draw.multiline_text(
        (x, y),
        wrapped_text,
        font=font,
        fill=(*color_rgb, 255),
        align=align
    )

    img.save(output_path, "PNG")
    return output_path


def create_cta_image(
    text:        str,
    width:       int,
    height:      int,
    bg_color:    str,
    text_color:  str,
    output_path: str
) -> str:
    """
    Creates a CTA button — rounded rectangle with text.
    """
    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding_x     = 40
    padding_y     = 20
    font_size     = 32
    corner_radius = 12

    font = None
    for font_path in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    bbox       = draw.textbbox((0, 0), text, font=font)
    text_w     = bbox[2] - bbox[0]
    text_h     = bbox[3] - bbox[1]

    btn_width  = text_w + (padding_x * 2)
    btn_height = text_h + (padding_y * 2)

    btn_x = (width  - btn_width)  // 2
    btn_y = (height - btn_height) // 2

    bg_rgb = hex_to_rgb(bg_color)
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_width, btn_y + btn_height],
        radius=corner_radius,
        fill=(*bg_rgb, 240)
    )

    text_rgb = hex_to_rgb(text_color)
    draw.text(
        (btn_x + padding_x, btn_y + padding_y),
        text,
        font=font,
        fill=(*text_rgb, 255)
    )

    img.save(output_path, "PNG")
    print(f"  🔘 CTA button created: '{text}'")
    return output_path


async def download_logo(logo_url: str, output_path: str) -> str:
    """
    Download logo from URL. Converts SVG to PNG if needed.
    FFmpeg cannot use SVG files directly.
    """
    if not logo_url:
        return ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                logo_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    return ""
                content = await response.read()

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(content)

        if logo_url.lower().endswith('.svg') or b'<svg' in content[:100]:
            png_path = output_path.replace('.svg', '.png')
            try:
                import cairosvg
                cairosvg.svg2png(
                    url=output_path,
                    write_to=png_path,
                    output_width=200,
                    output_height=200
                )
                return png_path
            except ImportError:
                print("  ⚠️  SVG logo — cairosvg not installed, skipping logo")
                return ""

        print(f"  🖼️  Logo downloaded: {output_path}")
        return output_path

    except Exception as e:
        print(f"  ⚠️  Logo download failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# SECTION 3 — SCREENSHOT CAPTURE
# Uses Playwright to take real website screenshots
# ═══════════════════════════════════════════════════════

async def capture_website_screenshots(
    url:       str,
    render_id: str
) -> list:
    """
    Takes 3 screenshots of the website using Playwright.
    Hero section, features section, and lower content.
    Runs in a thread pool to avoid Windows asyncio issues.
    """

    def take_screenshots_sync(url: str, render_id: str) -> list:
        from playwright.sync_api import sync_playwright

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        screenshot_paths = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)

                clip = {"x": 0, "y": 0, "width": 1280, "height": 720}

                # Screenshot 1 — Hero (top of page)
                path1 = os.path.join(TEMP_DIR, f"{render_id}_screen1.png")
                page.screenshot(path=path1, clip=clip)
                screenshot_paths.append(path1)
                print(f"  📸 Screenshot 1: hero section")

                # Screenshot 2 — Features (scroll down one viewport)
                page.evaluate("window.scrollTo(0, window.innerHeight)")
                page.wait_for_timeout(1000)
                path2 = os.path.join(TEMP_DIR, f"{render_id}_screen2.png")
                page.screenshot(path=path2, clip=clip)
                screenshot_paths.append(path2)
                print(f"  📸 Screenshot 2: features section")

                # Screenshot 3 — More content (scroll down two viewports)
                page.evaluate("window.scrollTo(0, window.innerHeight * 2)")
                page.wait_for_timeout(1000)
                path3 = os.path.join(TEMP_DIR, f"{render_id}_screen3.png")
                page.screenshot(path=path3, clip=clip)
                screenshot_paths.append(path3)
                print(f"  📸 Screenshot 3: lower content")

            except Exception as e:
                print(f"  ⚠️ Screenshot failed: {e}")
            finally:
                browser.close()

        return screenshot_paths

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        paths = await loop.run_in_executor(
            pool,
            take_screenshots_sync,
            url,
            render_id
        )

    print(f"  ✅ Got {len(paths)} screenshots")
    return paths


# ═══════════════════════════════════════════════════════
# SECTION 4 — FFMPEG VIDEO BUILDERS
# ═══════════════════════════════════════════════════════

def screenshots_to_video(
    screenshot_paths: list,
    output_path:      str,
    duration:         int
) -> str:
    """
    Converts website screenshots into a smooth video.
    
    Approach:
    - Each screenshot gets equal screen time
    - Simple crossfade transition between screenshots
    - No complex zoompan (too slow, unreliable)
    - Each screenshot scales to 1280x720
    """
    if not screenshot_paths:
        raise Exception("No screenshots provided")

    num_shots     = len(screenshot_paths)
    time_per_shot = duration / num_shots

    print(f"  🎬 Building video from {num_shots} screenshots")
    print(f"  ⏱️  Each screenshot shows for {time_per_shot:.1f} seconds")

    # ── Step 1: Convert each screenshot to a short video clip ──
    # We turn each PNG into an MP4 clip first
    # Then concatenate the clips together
    # This is more reliable than complex filter_complex

    clip_paths = []
    for i, screenshot_path in enumerate(screenshot_paths):
        clip_path = screenshot_path.replace('.png', '_clip.mp4')
        clip_paths.append(clip_path)

        command = [
            "ffmpeg", "-y",
            "-loop", "1",              # loop the image
            "-i", screenshot_path,     # input image
            "-t", str(time_per_shot),  # duration
            "-vf", (
                "scale=1280:720:"
                "force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1"
                # scale to fit 1280x720
                # pad with black if aspect ratio differs
                # setsar fixes pixel aspect ratio
            ),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", "30",                # 30fps
            "-an",                     # no audio
            clip_path
        ]

        run_ffmpeg(command)
        print(f"  ✅ Clip {i+1} created: {time_per_shot:.1f}s")

    # ── Step 2: Create concat list file ──
    # FFmpeg concat demuxer needs a text file listing all clips
    # Format:
    #   file 'path/to/clip1.mp4'
    #   file 'path/to/clip2.mp4'
    #   file 'path/to/clip3.mp4'

    concat_list_path = output_path.replace('.mp4', '_concat.txt')

    with open(concat_list_path, 'w') as f:
        for clip_path in clip_paths:
            # Use forward slashes and escape special chars
            safe_path = clip_path.replace('\\', '/')
            f.write(f"file '{safe_path}'\n")

    print(f"  📝 Concat list created with {len(clip_paths)} clips")

    # ── Step 3: Concatenate all clips into final video ──
    command = [
        "ffmpeg", "-y",
        "-f", "concat",           # use concat demuxer
        "-safe", "0",             # allow absolute paths
        "-i", concat_list_path,   # input is the list file
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),      # trim to exact duration
        "-an",
        output_path
    ]

    run_ffmpeg(command)

    # ── Step 4: Clean up clip files ──
    for clip_path in clip_paths:
        try:
            if os.path.exists(clip_path):
                os.remove(clip_path)
        except Exception:
            pass
    try:
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
    except Exception:
        pass

    print(f"  Screenshot video created: {output_path}")
    return output_path


def mix_audio(
    voiceover_path: str,
    music_path:     str,
    output_path:    str,
    duration:       int
) -> str:
    """
    Mixes voiceover and background music into one audio track.

    Why mix separately?
    It's cleaner to mix audio first, then add to video.
    Gives us better control over levels.

    Final mix:
    - Voiceover: 100% volume (clearly audible)
    - Music: 15% volume (subtle background)
    """
    if not voiceover_path or not os.path.exists(voiceover_path):
        print("  No voiceover — using music only")
        if music_path and os.path.exists(music_path):
            import shutil
            shutil.copy(music_path, output_path)
            return output_path
        return ""

    if not music_path or not os.path.exists(music_path):
        print(" No music — using voiceover only")
        import shutil
        shutil.copy(voiceover_path, output_path)
        return output_path

    print(" Mixing voiceover + music...")

    command = [
        "ffmpeg", "-y",
        "-i", voiceover_path,   # input 1: voiceover
        "-i", music_path,       # input 2: music
        "-filter_complex",
        (
            "[0:a]volume=1.0[voice];"      # voiceover at full volume
            "[1:a]volume=1.0[music];"      # music already at 15% from prepare_music — keep as-is
            "[voice][music]amix="          # mix both together
            "inputs=2:"
            "duration=longest:"            # use longest input (music = full ad duration)
            "dropout_transition=2"         # smooth dropout at end
            "[mixed]"
        ),
        "-map", "[mixed]",
        "-t", str(duration),
        "-acodec", "libmp3lame",
        "-q:a", "2",
        output_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Audio mix failed — using voiceover only")
        import shutil
        shutil.copy(voiceover_path, output_path)

    print(" Audio mixed successfully")
    return output_path


def assemble_with_ffmpeg(
    bg_video_path: str,
    overlay_path:  str,
    headline_path: str,
    subtext_path:  str,
    cta_path:      str,
    logo_path:     str,
    output_path:   str,
    duration:      int,
    audio_path:    str = ""
) -> str:
    """
    Combines all PNG layers + background video into final MP4.
    Uses FFmpeg filter_complex to stack layers like Photoshop.

    Layer order (bottom to top):
    [0] background video
    [1] dark overlay     → makes text readable
    [2] headline text
    [3] subtext
    [4] CTA button
    [5] logo (optional)
    [6 or 5] audio (if present)
    """
    inputs = [
        "-i", bg_video_path,
        "-i", overlay_path,
        "-i", headline_path,
        "-i", subtext_path,
        "-i", cta_path,
    ]

    has_logo  = logo_path  and os.path.exists(logo_path)
    has_audio = audio_path and os.path.exists(audio_path)

    if has_logo:
        inputs += ["-i", logo_path]
    if has_audio:
        inputs += ["-i", audio_path]

    if has_logo:
        filter_complex = (
            "[0:v]scale=1280:720,setsar=1[bg];"
            "[bg][1:v]overlay=0:0[with_overlay];"
            "[with_overlay][2:v]overlay=0:180[with_headline];"
            "[with_headline][3:v]overlay=0:340[with_subtext];"
            "[with_subtext][4:v]overlay=0:520[with_cta];"
            "[with_cta][5:v]overlay=(W-w)/2:30[final]"
        )
        audio_index = 6
    else:
        filter_complex = (
            "[0:v]scale=1280:720,setsar=1[bg];"
            "[bg][1:v]overlay=0:0[with_overlay];"
            "[with_overlay][2:v]overlay=0:200[with_headline];"
            "[with_headline][3:v]overlay=0:360[with_subtext];"
            "[with_subtext][4:v]overlay=0:520[final]"
        )
        audio_index = 5

    command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
    ]

    if has_audio:
        command += ["-map", f"{audio_index}:a", "-c:a", "aac", "-b:a", "128k"]
        print(f"  🔊 Audio will be stitched from: {audio_path}")
    else:
        command += ["-an"]

    command += [output_path]

    run_ffmpeg(command)
    print(f"  ✅ Video assembled: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════
# SECTION 5 — MAIN FUNCTION
# Orchestrates everything — called by routers/generate.py
# ═══════════════════════════════════════════════════════

async def assemble_video(
    script:        dict,
    business_name: str,
    colors:        dict,
    logo_url:      str,
    duration:      int = 15,
    website_url:   str = ""
) -> dict:
    """
    Main entry point for video assembly.

    Flow:
    1. Get background (website screenshots OR Pexels fallback)
    2. Download logo
    3. Create visual layers (overlay, headline, subtext, CTA)
    4. Assemble with FFmpeg
    5. Clean up temp files
    6. Return render result
    """

    # Defensive — never crash on None inputs
    script        = script        or {}
    colors        = colors        or {}
    logo_url      = logo_url      or ""
    website_url   = website_url   or ""
    business_name = business_name or "Business"

    render_id = generate_id()
    print(f"\n🎬 Starting video assembly: {render_id}")
    print("─" * 50)

    # File paths for this render job
    bg_path       = os.path.join(TEMP_DIR,   f"{render_id}_bg.mp4")
    overlay_path  = os.path.join(TEMP_DIR,   f"{render_id}_overlay.png")
    headline_path = os.path.join(TEMP_DIR,   f"{render_id}_headline.png")
    subtext_path  = os.path.join(TEMP_DIR,   f"{render_id}_subtext.png")
    cta_path      = os.path.join(TEMP_DIR,   f"{render_id}_cta.png")
    logo_path     = os.path.join(TEMP_DIR,   f"{render_id}_logo.png")
    output_path   = os.path.join(OUTPUT_DIR, f"{render_id}_ad.mp4")

    for f in [bg_path, overlay_path, headline_path,
              subtext_path, cta_path, logo_path, output_path]:
        try:
            if os.path.exists(f):
                os.remove(f)
                print(f"  🗑️  Cleaned old file: {os.path.basename(f)}")
        except Exception:
            pass
    # Extract values from script and colors
    headline          = script.get("headline",          business_name)
    subtext           = script.get("subtext",           "")
    cta               = script.get("cta",               "Learn More")
    scene_description = script.get("scene_description", "business professional")
    primary_color     = colors.get("primary",           "#1a1a2e")

    # ── Step 1: Get background video ─────────────────
    print("\n📥 Step 1: Getting background video...")

    if website_url:
        # Ensure URL has https://
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url

        print(f"  📸 Capturing screenshots from: {website_url}")
        screenshot_paths = await capture_website_screenshots(
            url=website_url,
            render_id=render_id
        )

        if screenshot_paths:
            # Turn screenshots into background video with Ken Burns zoom
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool,
                    screenshots_to_video,
                    screenshot_paths,
                    bg_path,
                    duration
                )
            print(f"  ✅ Website screenshots used as background")
        else:
            # Screenshots failed — fall back to Pexels stock footage
            print(f"  ⚠️ No screenshots — falling back to Pexels")
            from services.pexels import get_background_video
            await get_background_video(
                scene_description=scene_description,
                output_path=bg_path
            )
    else:
        # No URL — use Pexels stock footage directly
        from services.pexels import get_background_video
        await get_background_video(
            scene_description=scene_description,
            output_path=bg_path
        )

    # ── Step 2: Download logo ─────────────────────────
    print("\n Step 2: Downloading logo...")
    actual_logo_path = ""
    if logo_url:
        actual_logo_path = await download_logo(logo_url, logo_path)

    # ── Step 3: Create visual layers ─────────────────
    print("\n Step 3: Creating visual layers...")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:

        await loop.run_in_executor(
            pool, create_overlay_image,
            VIDEO_WIDTH, VIDEO_HEIGHT, "#000000", 150, overlay_path
        )

        await loop.run_in_executor(
            pool, create_text_image,
            headline, VIDEO_WIDTH, 160, 64, "#ffffff",
            headline_path, True, "center"
        )

        await loop.run_in_executor(
            pool, create_text_image,
            subtext, VIDEO_WIDTH, 100, 36, "#eeeeee",
            subtext_path, False, "center"
        )

        await loop.run_in_executor(
            pool, create_cta_image,
            cta, VIDEO_WIDTH, 100,
            primary_color, "#ffffff", cta_path
        )
    # ── Step 3.5: Generate audio ──────────────────────
    print("\n🔊 Step 3.5: Generating audio...")
    print(f"  DEBUG: voiceover = {script.get('voiceover', 'MISSING')[:50]}")

    voiceover_wav  = os.path.join(TEMP_DIR, f"{render_id}_voice.wav")
    voiceover_mp3  = os.path.join(TEMP_DIR, f"{render_id}_voice.mp3")
    music_prepared = os.path.join(TEMP_DIR, f"{render_id}_music.mp3")
    final_audio    = os.path.join(TEMP_DIR, f"{render_id}_audio.mp3")
    audio_path     = ""

    try:
        voiceover_text = script.get("voiceover", "")
        music_style    = script.get("music_style", "upbeat")

        if voiceover_text:
            # Generate speech at natural Kokoro pace (no speed adjustment)
            # The LLM writes a short enough script so no stretching is needed.
            await generate_voiceover(
                text=voiceover_text,
                output_path=voiceover_wav
            )

            # Convert WAV → MP3 (no atempo, preserves pitch perfectly)
            wav_to_mp3(voiceover_wav, voiceover_mp3)
            voiceover_final = voiceover_mp3  # use as-is at natural speed

            # Get and prepare music
            raw_music_path = get_music_path(music_style)
            if raw_music_path:
                prepare_music(
                    music_path=raw_music_path,
                    output_path=music_prepared,
                    duration=duration
                )

            # Mix voiceover + music
            audio_path = mix_audio(
                voiceover_path=voiceover_final,
                music_path=music_prepared,
                output_path=final_audio,
                duration=duration
            )
            print(f"   Audio ready: {audio_path}")
        else:
            print("    No voiceover text — skipping audio")

    except Exception as e:
        import traceback
        print(f"\n   AUDIO FAILED: {e}")
        traceback.print_exc()
        audio_path = ""

    # ── Step 4: Assemble with FFmpeg ──────────────────
    print("\n🎬 Step 4: Assembling video with FFmpeg...")
    print(f"  DEBUG: audio_path passed = '{audio_path}'")

    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(
            pool, assemble_with_ffmpeg,
            bg_path, overlay_path, headline_path,
            subtext_path, cta_path, actual_logo_path,
            output_path, duration, audio_path
        )

    # ── Step 5: Cleanup temp files ────────────────────
    print("\n🧹 Step 5: Cleaning up temp files...")
    for f in [bg_path, overlay_path, headline_path, subtext_path, cta_path]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    print(f"\n✅ Video assembly complete!")
    print(f"   Output: {output_path}")
    print(f"   Render ID: {render_id}")

    return {
        "render_id":     render_id,
        "video_path":    output_path,
        "url":           f"/api/output/{render_id}_ad.mp4",
        "status":        "done",
        "thumbnail_url": ""
    }