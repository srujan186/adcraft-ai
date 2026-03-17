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
async def capture_website_screenshots(
    url: str,
    render_id: str,
    count: int = 3
) -> list:
    """
    Takes real screenshots of the website using Playwright.
    Returns list of screenshot file paths.

    Why 3 screenshots?
    A 15s ad has 3 sections:
    - Opening (0-5s):  hero/homepage
    - Middle (5-10s):  features/product
    - Closing (10-15s): CTA/testimonials

    Each screenshot covers one section.
    """
    from concurrent.futures import ThreadPoolExecutor
    import asyncio

    def take_screenshots_sync(url: str, render_id: str) -> list:
        from playwright.sync_api import sync_playwright

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

                # Screenshot 1 — Hero section (top of page)
                path1 = os.path.join(TEMP_DIR, f"{render_id}_screen1.png")
                page.screenshot(path=path1, clip={
                    "x": 0, "y": 0,
                    "width": 1280, "height": 720
                })
                screenshot_paths.append(path1)
                print(f"  📸 Screenshot 1: hero section")

                # Screenshot 2 — Scroll down to features
                page.evaluate("window.scrollTo(0, window.innerHeight)")
                page.wait_for_timeout(1000)
                path2 = os.path.join(TEMP_DIR, f"{render_id}_screen2.png")
                page.screenshot(path=path2, clip={
                    "x": 0, "y": 0,
                    "width": 1280, "height": 720
                })
                screenshot_paths.append(path2)
                print(f"  📸 Screenshot 2: features section")

                # Screenshot 3 — Scroll down more
                page.evaluate("window.scrollTo(0, window.innerHeight * 2)")
                page.wait_for_timeout(1000)
                path3 = os.path.join(TEMP_DIR, f"{render_id}_screen3.png")
                page.screenshot(path=path3, clip={
                    "x": 0, "y": 0,
                    "width": 1280, "height": 720
                })
                screenshot_paths.append(path3)
                print(f"  📸 Screenshot 3: more content")

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


def generate_id() -> str:
    """Generate a unique ID for each render job."""
    return str(uuid.uuid4())[:8]


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple.
    "#38BDF8" → (56, 189, 248)

    PIL (Pillow) uses RGB tuples, not hex strings.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    """
    Convert hex color to RGBA tuple with alpha.
    "#38BDF8", 180 → (56, 189, 248, 180)

    Alpha 0 = transparent, 255 = fully opaque
    We use ~160 for overlays so background shows through.
    """
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)


def run_ffmpeg(command: list) -> bool:
    """
    Run an FFmpeg command and wait for it to complete.

    Why subprocess?
    FFmpeg is a command line tool — we launch it as a
    separate process and wait for it to finish.

    Why check_returncode?
    FFmpeg returns 0 on success, non-zero on failure.
    We raise an exception if it fails so we know immediately.
    """
    print(f"  🎬 FFmpeg: {' '.join(command[:5])}...")

    result = subprocess.run(
        command,
        capture_output=True,  # capture stdout and stderr
        text=True             # decode output as text
    )

    if result.returncode != 0:
        # FFmpeg puts errors in stderr
        error = result.stderr[-500:] if result.stderr else "Unknown error"
        raise Exception(f"FFmpeg failed:\n{error}")

    return True


# ═══════════════════════════════════════════════════════
# SECTION 2 — ASSET CREATORS
# Each function creates ONE visual element
# ═══════════════════════════════════════════════════════

def create_overlay_image(
    width: int,
    height: int,
    color: str,
    alpha: int,
    output_path: str
) -> str:
    """
    Creates a semi-transparent color overlay image.

    Why do we need this?
    Background video is colorful and busy.
    Text on top would be unreadable.
    A dark semi-transparent overlay makes text readable
    while still showing the background video underneath.

    Like putting a frosted glass layer over the video.
    """
    rgba = hex_to_rgba(color, alpha)
    img  = Image.new("RGBA", (width, height), rgba)
    img.save(output_path, "PNG")
    print(f"  🎨 Overlay created: {color} alpha={alpha}")
    return output_path


def create_text_image(
    text:        str,
    width:       int,
    height:      int,
    font_size:   int,
    text_color:  str,
    output_path: str,
    bold:        bool = False,
    align:       str = "center"
) -> str:
    """
    Creates a transparent PNG image with text on it.

    Why create images for text instead of FFmpeg drawtext?
    FFmpeg's drawtext filter needs fonts installed on system.
    Creating PNG images with Pillow gives us:
    - Better font control
    - Text wrapping
    - Transparent backgrounds (overlay on video)
    - Consistent cross-platform rendering
    """
    # Create transparent background
    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try to load a nice font
    # Falls back to default if font not found
    font = None
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
        "C:/Windows/Fonts/arial.ttf",     # Arial
        "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
        "C:/Windows/Fonts/calibri.ttf",   # Calibri
        "C:/Windows/Fonts/verdana.ttf",   # Verdana
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue

    if font is None:
        # Ultimate fallback — PIL default font
        font = ImageFont.load_default()
        print(f"  ⚠️  Using default font (no system font found)")

    # Get text color as RGB
    color_rgb = hex_to_rgb(text_color)

    # Word wrap text to fit width
    wrapped_text = wrap_text(text, font, draw, width - 80)

    # Calculate text position (centered)
    bbox        = draw.textbbox((0, 0), wrapped_text, font=font)
    text_width  = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Draw subtle shadow for depth
    shadow_offset = max(2, font_size // 20)
    draw.multiline_text(
        (x + shadow_offset, y + shadow_offset),
        wrapped_text,
        font=font,
        fill=(0, 0, 0, 120),  # semi-transparent black shadow
        align=align
    )

    # Draw main text
    draw.multiline_text(
        (x, y),
        wrapped_text,
        font=font,
        fill=(*color_rgb, 255),  # full opacity
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
    Creates a CTA button image.
    Rounded rectangle background with text on top.

    Why a separate function?
    CTA needs special styling — rounded corners,
    background fill, padding — different from plain text.
    """
    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Button dimensions
    padding_x  = 40
    padding_y  = 20
    font_size  = 32
    corner_radius = 12

    # Load font
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

    # Measure text size
    bbox       = draw.textbbox((0, 0), text, font=font)
    text_w     = bbox[2] - bbox[0]
    text_h     = bbox[3] - bbox[1]

    # Button size based on text
    btn_width  = text_w + (padding_x * 2)
    btn_height = text_h + (padding_y * 2)

    # Center button in image
    btn_x = (width  - btn_width)  // 2
    btn_y = (height - btn_height) // 2

    # Draw rounded rectangle background
    bg_rgb = hex_to_rgb(bg_color)
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_width, btn_y + btn_height],
        radius=corner_radius,
        fill=(*bg_rgb, 240)  # slightly transparent
    )

    # Draw text centered on button
    text_x = btn_x + padding_x
    text_y = btn_y + padding_y

    text_rgb = hex_to_rgb(text_color)
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=(*text_rgb, 255)
    )

    img.save(output_path, "PNG")
    print(f"  🔘 CTA button created: '{text}'")
    return output_path


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.Draw,
    max_width: int
) -> str:
    """
    Wraps text to fit within max_width pixels.

    Why manual wrapping?
    PIL doesn't auto-wrap text.
    We split by words and add newlines when a line
    would exceed max_width.
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
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


async def download_logo(logo_url: str, output_path: str) -> str:
    """
    Download logo from URL and save to local path.
    Converts SVG to PNG if needed (FFmpeg can't use SVG).
    """
    if not logo_url:
        return ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(logo_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return ""
                content = await response.read()

        # Save the raw file first
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(content)

        # If SVG, convert to PNG using Pillow
        # FFmpeg can't directly use SVG files
        if logo_url.lower().endswith('.svg') or b'<svg' in content[:100]:
            png_path = output_path.replace('.svg', '.png')
            try:
                # Try cairosvg if available
                import cairosvg
                cairosvg.svg2png(
                    url=output_path,
                    write_to=png_path,
                    output_width=200,
                    output_height=200
                )
                return png_path
            except ImportError:
                # cairosvg not installed
                # Return empty — logo won't show but ad still works
                print("  SVG logo found but cairosvg not installed")
                print("   Ad will be generated without logo")
                return ""

        print(f"  🖼️  Logo downloaded: {output_path}")
        return output_path

    except Exception as e:
        print(f"  ⚠️  Logo download failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# SECTION 3 — FFMPEG ASSEMBLER
# Combines all assets into final video
# ═══════════════════════════════════════════════════════

def assemble_with_ffmpeg(
    bg_video_path:  str,
    overlay_path:   str,
    headline_path:  str,
    subtext_path:   str,
    cta_path:       str,
    logo_path:      str,
    output_path:    str,
    duration:       int
) -> str:
    """
    The heart of the video assembler.
    Takes all PNG layers + background video
    and combines them into a final MP4.

    FFmpeg filter_complex explanation:
    filter_complex lets us chain multiple operations.
    We overlay each PNG layer on top of the video one by one.

    Think of it like Photoshop layers:
    [0] background video
    [1] dark overlay     ← overlaid on [0]
    [2] headline text    ← overlaid on result
    [3] subtext text     ← overlaid on result
    [4] CTA button       ← overlaid on result
    [5] logo             ← overlaid on result (optional)
    """

    # Build input list
    inputs = [
        "-i", bg_video_path,   # [0] background video
        "-i", overlay_path,    # [1] dark overlay
        "-i", headline_path,   # [2] headline text
        "-i", subtext_path,    # [3] subtext
        "-i", cta_path,        # [4] CTA button
    ]

    has_logo = logo_path and os.path.exists(logo_path)
    if has_logo:
        inputs += ["-i", logo_path]  # [5] logo

    # Build filter_complex string
    # Each step overlays one layer on the previous result
    if has_logo:
        filter_complex = (
            # Step 1: Resize background to 1280x720
            "[0:v]scale=1280:720,setsar=1[bg];"

            # Step 2: Overlay dark overlay on background
            "[bg][1:v]overlay=0:0[with_overlay];"

            # Step 3: Overlay headline (centered, upper area)
            "[with_overlay][2:v]overlay=0:180[with_headline];"

            # Step 4: Overlay subtext (centered, middle)
            "[with_headline][3:v]overlay=0:340[with_subtext];"

            # Step 5: Overlay CTA button (centered, lower area)
            "[with_subtext][4:v]overlay=0:520[with_cta];"

            # Step 6: Overlay logo (top center)
            "[with_cta][5:v]overlay=(W-w)/2:30[final]"
        )
        map_output = "[final]"
    else:
        filter_complex = (
            "[0:v]scale=1280:720,setsar=1[bg];"
            "[bg][1:v]overlay=0:0[with_overlay];"
            "[with_overlay][2:v]overlay=0:200[with_headline];"
            "[with_headline][3:v]overlay=0:360[with_subtext];"
            "[with_subtext][4:v]overlay=0:520[final]"
        )
        map_output = "[final]"

    command = [
        "ffmpeg",
        "-y",                  # overwrite output if exists
        *inputs,               # all input files
        "-filter_complex", filter_complex,
        "-map", map_output,    # use our composed video
        "-t", str(duration),   # trim to exact duration
        "-c:v", "libx264",     # encode with H.264
        "-preset", "fast",     # encoding speed vs quality
        "-crf", "23",          # quality (18=best, 28=worst)
        "-pix_fmt", "yuv420p", # pixel format for compatibility
        "-an",                 # no audio for now
        output_path
    ]

    run_ffmpeg(command)
    print(f"  ✅ Video assembled: {output_path}")
    return output_path


def screenshots_to_video(
    screenshot_paths: list,
    output_path:      str,
    duration:         int
) -> str:
    """
    Converts website screenshots into a smooth video.

    Each screenshot shows for equal time.
    Ken Burns effect (slow zoom) makes it dynamic.
    Crossfade transition between screenshots.

    Why Ken Burns?
    Static images look boring in a video.
    Slow zoom makes it feel cinematic and professional.
    """
    if not screenshot_paths:
        raise Exception("No screenshots provided")

    # How long each screenshot shows
    time_per_shot = duration / len(screenshot_paths)

    # Build FFmpeg inputs
    inputs = []
    for path in screenshot_paths:
        inputs += ["-loop", "1", "-t", str(time_per_shot), "-i", path]

    # Build filter for each screenshot
    # zoompan = Ken Burns slow zoom effect
    filters = []
    for i, _ in enumerate(screenshot_paths):
        filters.append(
            f"[{i}:v]scale=1280:720,"
            f"zoompan="
            f"z='min(zoom+0.0005,1.1)':"  # slowly zoom from 1.0 to 1.1
            f"x='iw/2-(iw/zoom/2)':"      # keep centered
            f"y='ih/2-(ih/zoom/2)':"      # keep centered
            f"d={int(time_per_shot * 30)}:"  # duration in frames
            f"s=1280x720,"
            f"fps=30"
            f"[v{i}]"
        )

    # Concatenate all clips
    concat_inputs = "".join([f"[v{i}]" for i in range(len(screenshot_paths))])
    filters.append(
        f"{concat_inputs}concat=n={len(screenshot_paths)}:v=1:a=0[final]"
    )

    filter_complex = ";".join(filters)

    command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    run_ffmpeg(command)
    print(f"  ✅ Screenshot video created: {output_path}")
    return output_path

# ═══════════════════════════════════════════════════════
# SECTION 4 — MAIN FUNCTION
# Orchestrates the entire assembly process
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
    Main video assembly function.
    Orchestrates all steps and returns video URL.

    Flow:
    1. Generate unique render ID
    2. Get background video (either from website screenshots or Pexels)
    3. Download logo
    4. Create overlay image
    5. Create text images (headline, subtext, CTA)
    6. Run FFmpeg to combine everything
    7. Return video path and render ID
    """
        # Defensive checks — never crash on None
    script        = script   or {}
    colors        = colors   or {}
    logo_url      = logo_url or ""
    website_url   = website_url or ""
    business_name = business_name or "Business"

    render_id = generate_id()
    print(f"\n🎬 Starting video assembly: {render_id}")
    print("─" * 50)

    # File paths for this render
    bg_path       = os.path.join(TEMP_DIR, f"{render_id}_bg.mp4")
    overlay_path  = os.path.join(TEMP_DIR, f"{render_id}_overlay.png")
    headline_path = os.path.join(TEMP_DIR, f"{render_id}_headline.png")
    subtext_path  = os.path.join(TEMP_DIR, f"{render_id}_subtext.png")
    cta_path      = os.path.join(TEMP_DIR, f"{render_id}_cta.png")
    logo_path     = os.path.join(TEMP_DIR, f"{render_id}_logo.png")
    output_path   = os.path.join(OUTPUT_DIR, f"{render_id}_ad.mp4")

    # Extract data from script and colors
    headline          = script.get("headline", business_name)
    subtext           = script.get("subtext", "")
    cta               = script.get("cta", "Learn More")
    scene_description = script.get("scene_description", "business professional")

    primary_color   = colors.get("primary", "#1a1a2e")
    secondary_color = colors.get("secondary", "#ffffff")

    # ── Step 1: Download background video ────────────
    print("\n📥 Step 1: Getting background video...")
    if website_url:
        # Capture screenshots from the website
        print(f"  📸 Capturing screenshots from: {website_url}")
        screenshot_paths = await capture_website_screenshots(
            url=website_url,
            render_id=render_id,
            count=3
        )
        # Convert screenshots to video
        await asyncio.get_event_loop().run_in_executor(
            None,
            screenshots_to_video,
            screenshot_paths,
            bg_path,
            duration
        )
    else:
        # Fall back to Pexels video if no website URL provided
        from services.pexels import get_background_video
        await get_background_video(
            scene_description=scene_description,
            output_path=bg_path
        )

    # ── Step 2: Download logo ─────────────────────────
    print("\n🖼️  Step 2: Downloading logo...")
    actual_logo_path = ""
    if logo_url:
        actual_logo_path = await download_logo(logo_url, logo_path)

    # ── Step 3: Create visual layers ─────────────────
    print("\n🎨 Step 3: Creating visual layers...")

    # Run PIL operations in thread pool
    # PIL is CPU-bound (not async) so we use threads
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:

        # Dark overlay — makes text readable over video
        await loop.run_in_executor(
            pool,
            create_overlay_image,
            VIDEO_WIDTH, VIDEO_HEIGHT,
            "#000000",  # black overlay
            150,        # alpha: 0=transparent, 255=opaque
            overlay_path
        )

        # Headline — large, bold, white text
        await loop.run_in_executor(
            pool,
            create_text_image,
            headline,
            VIDEO_WIDTH, 160,   # full width, 160px tall
            64,                 # font size
            "#ffffff",          # white text
            headline_path,
            True,               # bold
            "center"
        )

        # Subtext — smaller, slightly transparent
        await loop.run_in_executor(
            pool,
            create_text_image,
            subtext,
            VIDEO_WIDTH, 100,
            36,
            "#eeeeee",          # slightly off-white
            subtext_path,
            False,
            "center"
        )

        # CTA button
        await loop.run_in_executor(
            pool,
            create_cta_image,
            cta,
            VIDEO_WIDTH, 100,
            primary_color,      # brand color background
            "#ffffff",          # white text
            cta_path
        )

    # ── Step 4: Assemble with FFmpeg ──────────────────
    print("\n🎬 Step 4: Assembling video with FFmpeg...")

    # FFmpeg is CPU-bound — run in thread pool
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(
            pool,
            assemble_with_ffmpeg,
            bg_path,
            overlay_path,
            headline_path,
            subtext_path,
            cta_path,
            actual_logo_path,
            output_path,
            duration
        )

    # ── Step 5: Cleanup temp files ────────────────────
    print("\n🧹 Step 5: Cleaning up temp files...")
    temp_files = [
        bg_path, overlay_path, headline_path,
        subtext_path, cta_path
    ]
    for f in temp_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass  # cleanup failure is not critical

    print(f"\n✅ Video assembly complete!")
    print(f"   Output: {output_path}")
    print(f"   Render ID: {render_id}")

    return {
        "render_id":     render_id,
        "video_path":    output_path,
        "url":           f"/output/{render_id}_ad.mp4",
        "status":        "done",
        "thumbnail_url": ""
    }