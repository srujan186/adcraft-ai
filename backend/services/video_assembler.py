# services/video_assembler.py
# ONE job: assemble all assets into a finished video ad
# Uses FFmpeg for all video processing

import os
import uuid
import hashlib
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

# How many distinct shots an ad is cut from. Three meant a short site gave
# three near-identical screenshots — the ad looked like one static image.
# This is the 15s default; longer ads get more via scenes_for_duration so a
# 30s ad is not six images held 5s each.
TARGET_SCENES = 6


def scenes_for_duration(duration: int) -> int:
    """
    How many scenes to cut an ad of this length into.

    Roughly one shot per 3 seconds — a 15s ad stays at its established 6 (2.5s
    each), a 30s ad gets 10 (~3s each) so it feels like an ad and not a
    slideshow. Capped at MAX_SCENES; the model rejects more than that anyway.
    """
    if duration <= 15:
        return TARGET_SCENES
    return max(TARGET_SCENES, min(MAX_SCENES, round(duration / 3)))


# The editor and the request model share this ceiling; past it each shot is too
# brief to register.
MAX_SCENES = 12

# ── Caption layout ───────────────────────────────────────────────────────────
# A lower-third, not a full-screen takeover. The old layout put a 64px headline
# across the full 1280px width with a flat black wash over the whole frame, so
# the picture the ad was built from was barely visible behind its own captions.
SAFE_X          = 72     # left margin for every text element
TEXT_BLOCK_W    = 760    # captions wrap inside this, leaving the right clear
HEADLINE_SIZE   = 42
HEADLINE_Y      = 392
HEADLINE_H      = 124
SUBTEXT_SIZE    = 24
SUBTEXT_Y       = 520
SUBTEXT_H       = 64
CTA_SIZE        = 22
CTA_Y           = 596
CTA_H           = 60
# The scrim fades in from here down, instead of dimming the whole frame.
SCRIM_START     = 0.30
SCRIM_MAX_ALPHA = 238

# ── End card ───────────────────────────────────────────────────────────
# The closing scene: logo, company name and contact details on a brand card.
# It covers the frame for the last ENDCARD_SECONDS, and the captions stop when
# it starts so the two never share a frame.
ENDCARD_SECONDS  = 3.0
ENDCARD_FADE     = 0.35   # dissolve from the footage into the card
ENDCARD_LOGO_BOX = (300, 120)   # logo is fitted inside this, aspect preserved
ENDCARD_NAME_SIZE    = 58
ENDCARD_CONTACT_SIZE = 27
ENDCARD_GAP          = 22       # vertical space between stacked blocks

# Anything smaller than this is a truncated or empty container, not an ad.
MIN_OUTPUT_BYTES = 20_000

# Video settings
VIDEO_WIDTH  = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS    = 30


# ═══════════════════════════════════════════════════════
# SECTION 1 — HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════


# Font lookup. The list used to hold Windows paths only, so on Linux every
# os.path.exists missed and the code fell through to ImageFont.load_default()
# *without a size* — which is ~10px tall regardless of the size asked for, so a
# 64px headline rendered illegibly small and nothing detected it.
#
# Order: a bold face first (headlines want weight), then regular, then Pillow's
# own bundled face at the right size as a guaranteed last resort.
FONT_CANDIDATES = [
    # Linux / Docker
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/verdana.ttf",
]

_font_warned = False


def load_font(size: int):
    """A TrueType face at `size`, whatever platform we are on."""
    global _font_warned

    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Let Pillow search its own configured font dirs by family name.
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue

    # Pillow >= 10.1 scales its bundled face when given a size. Without the
    # size argument this returns a ~10px font and the ad looks broken.
    if not _font_warned:
        _font_warned = True
        print("   No system font found — falling back to Pillow's bundled face")
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


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


def relative_luminance(hex_color: str) -> float:
    """0 (black) to 1 (white). Used to keep the CTA readable."""
    try:
        r, g, b = hex_to_rgb(hex_color)
    except (ValueError, TypeError):
        return 0.0
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def pick_cta_colors(primary: str, accent: str) -> tuple:
    """
    Choose a (background, text) pair for the CTA pill.

    The pill used to take the brand's primary colour unconditionally. Plenty of
    brands are near-black, so the button vanished into the scrim it sat on.
    Prefer a brand colour with enough lift; otherwise fall back to white.
    """
    for candidate in (accent, primary):
        lum = relative_luminance(candidate)
        if lum > 0.30:
            return candidate, ("#0b0d14" if lum > 0.62 else "#ffffff")
    return "#ffffff", "#0b0d14"


def sanitize_for_render(text: str) -> str:
    """
    Replace typographic characters the render font may not carry.

    The script model likes non-breaking hyphens, curly quotes and ellipses.
    Arial and DejaVu do not all cover them, and a missing glyph draws as a
    tofu box — "real‑time" came out as "real[]time" on screen.
    """
    if not text:
        return ""

    swaps = {
        "‐": "-", "‑": "-", "‒": "-", "–": "-",
        "—": "-", "―": "-", "−": "-",
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"',
        "…": "...", "•": "-", " ": " ",
        " ": " ", " ": " ", "​": "",
    }
    for bad, good in swaps.items():
        text = text.replace(bad, good)
    return text


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
        # ffmpeg reports the cause near the top of stderr and the symptom
        # at the bottom, so a tail-only excerpt showed 'Could not open
        # encoder' while hiding the input or filter that actually broke.
        stderr = (result.stderr or "").strip()
        if not stderr:
            error = "Unknown error (ffmpeg wrote nothing to stderr)"
        elif len(stderr) <= 2000:
            error = stderr
        else:
            error = (
                stderr[:1200]
                + "\n  ... [trimmed] ...\n"
                + stderr[-800:]
            )
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
    A scrim that fades in towards the bottom of the frame.

    This used to be a flat rectangle at one alpha across the whole frame, which
    dimmed the photography evenly and made every ad look muddy. A gradient
    keeps the top of the shot clean and only darkens where the captions sit.

    Built from a 1px-wide ramp and resized — per-pixel Python over 1280x720
    would be ~900k iterations.
    """
    from PIL import ImageChops

    # Vertical: clear at the top, solid at the bottom.
    vert    = Image.new("L", (1, height), 0)
    start_y = int(height * SCRIM_START)
    # By the time the headline starts the scrim has to be doing real work. A
    # single eased ramp to the bottom was only ~12% opaque up here, so white
    # text sat on bright photography and vanished.
    knee_y  = max(start_y + 1, HEADLINE_Y - 48)

    for y in range(start_y, height):
        if y < knee_y:
            # Ease in above the captions so there is no visible edge.
            progress = (y - start_y) / max(1, knee_y - start_y)
            value    = alpha * 0.78 * (progress ** 1.4)
        else:
            # Caption band: dark enough to read on, still not solid.
            progress = (y - knee_y) / max(1, height - knee_y)
            value    = alpha * (0.78 + 0.22 * progress)
        vert.putpixel((0, y), int(value))

    # Horizontal: heaviest on the left, where the captions are, easing off to
    # the right so the picture keeps some air. Without this the scrim had to be
    # uniformly dark to keep white text legible over a light photo.
    horiz = Image.new("L", (width, 1), 255)
    for x in range(width):
        progress = x / max(1, width - 1)
        horiz.putpixel((x, 0), int(255 - (255 - 150) * (progress ** 1.3)))

    mask = ImageChops.multiply(
        vert.resize((width, height)),
        horiz.resize((width, height)),
    )

    img = Image.new("RGBA", (width, height), (*hex_to_rgb(color), 255))
    img.putalpha(mask)
    img.save(output_path, "PNG")
    print(f"  Scrim created: {color}, fades in from {int(SCRIM_START * 100)}%")
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
    text = sanitize_for_render(text)

    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = load_font(font_size)

    color_rgb = hex_to_rgb(text_color)

    # Left-aligned captions wrap to the full box; centred ones keep a margin.
    wrap_width   = width if align == "left" else width - 80
    wrapped_text = wrap_text(text, font, draw, wrap_width)

    bbox        = draw.textbbox((0, 0), wrapped_text, font=font)
    text_width  = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = 0 if align == "left" else (width - text_width) // 2
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
    output_path: str,
    align:       str = "center"
) -> str:
    """
    Creates a CTA button — rounded rectangle with text.
    """
    text = sanitize_for_render(text)

    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding_x     = 28
    padding_y     = 14
    font_size     = CTA_SIZE
    corner_radius = 999   # fully rounded pill

    font = None
    font = load_font(font_size)

    bbox       = draw.textbbox((0, 0), text, font=font)
    text_w     = bbox[2] - bbox[0]
    text_h     = bbox[3] - bbox[1]

    btn_width  = text_w + (padding_x * 2)
    btn_height = text_h + (padding_y * 2)

    btn_x = 0 if align == "left" else (width - btn_width) // 2
    btn_y = (height - btn_height) // 2

    bg_rgb = hex_to_rgb(bg_color)
    draw.rounded_rectangle(
        [btn_x, btn_y, btn_x + btn_width, btn_y + btn_height],
        radius=min(corner_radius, btn_height // 2),
        fill=(*bg_rgb, 245)
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


def create_endcard_image(
    details:     dict,
    primary:     str,
    accent:      str,
    output_path: str,
    logo_path:   str = ""
) -> str:
    """
    The ad's closing frame: logo, company name, then contact rows.

    Laid out as a measured stack rather than at fixed offsets -- a card with a
    logo and four contact rows and one with a name alone both need to sit
    optically centred, and hard-coded positions only ever suit one of them.

    Heights come from the font's ascent+descent, not from each string's own
    bounding box: a bbox carries that particular string's ascender offset, so
    measuring rows individually spaced them unevenly depending on whether the
    text happened to contain a tall glyph.
    """
    bg_rgb = hex_to_rgb(primary)

    # A flat brand colour across 1280x720 reads as a placeholder. A gentle
    # darkening towards the bottom gives it depth without inventing a second
    # colour to explain.
    card = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), bg_rgb)
    shade = Image.new("L", (1, VIDEO_HEIGHT), 0)
    for y in range(VIDEO_HEIGHT):
        shade.putpixel((0, y), int(70 * (y / VIDEO_HEIGHT) ** 1.4))
    card = Image.composite(
        Image.new("RGB", card.size, (0, 0, 0)),
        card,
        shade.resize(card.size),
    )

    draw = ImageDraw.Draw(card)

    # White on a dark brand colour, near-black on a light one.
    light_bg     = relative_luminance(primary) > 0.55
    name_fill    = (11, 13, 20)  if light_bg else (255, 255, 255)
    contact_fill = (54, 58, 72)  if light_bg else (223, 230, 242)

    name_font    = load_font(ENDCARD_NAME_SIZE)
    contact_font = load_font(ENDCARD_CONTACT_SIZE)

    def line_height(font) -> int:
        ascent, descent = font.getmetrics()
        return ascent + descent

    # \u2500\u2500 build the stack: (kind, payload, height, gap_after) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    blocks = []

    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_img.thumbnail(ENDCARD_LOGO_BOX, Image.LANCZOS)
            blocks.append(("logo", logo_img, logo_img.height, 40))
        except (OSError, ValueError) as e:
            print(f"  \u26a0\ufe0f  End card: logo unusable ({e}), skipping it")

    name = sanitize_for_render(details.get("company_name", "") or "").strip()
    if name:
        blocks.append(("name", name, line_height(name_font), 20))
        blocks.append(("rule", None, 4, 34))

    # The order a viewer would read them off the screen.
    for key in ("phone", "email", "website", "address"):
        value = sanitize_for_render(details.get(key, "") or "").strip()
        if value:
            blocks.append(("contact", value, line_height(contact_font), 14))

    if not blocks:
        return ""

    # The trailing gap is not part of the stack.
    total = sum(b[2] for b in blocks) + sum(b[3] for b in blocks[:-1])
    y     = (VIDEO_HEIGHT - total) // 2
    mid_x = VIDEO_WIDTH // 2

    for kind, payload, height, gap in blocks:
        if kind == "logo":
            card.paste(payload, ((VIDEO_WIDTH - payload.width) // 2, y), payload)

        elif kind == "name":
            # anchor="ma" = horizontally middle, vertically ascender-top, so the
            # line sits exactly in the slot measured for it.
            draw.text((mid_x, y), payload, font=name_font,
                      fill=name_fill, anchor="ma")

        elif kind == "rule":
            rule_w = 96
            draw.rounded_rectangle(
                [mid_x - rule_w // 2, y, mid_x + rule_w // 2, y + 4],
                radius=2, fill=hex_to_rgb(accent),
            )

        else:  # contact
            draw.text((mid_x, y), payload, font=contact_font,
                      fill=contact_fill, anchor="ma")

        y += height + gap

    card.save(output_path, "PNG")
    print(f"  \u2705 End card created: {len(blocks)} block(s)")
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

        # Whatever came back is now sitting in a file called .png. That does not
        # make it one: plenty of sites point logo_url at a favicon.ico, and a
        # 404 HTML page arrives the same way. ffmpeg cannot decode either, and
        # it only finds out at the final assembly step -- so the render died
        # after paying for the scrape, the script, the narration and every
        # encode. Re-save through Pillow, which both proves it decodes and
        # hands ffmpeg a format it definitely understands.
        try:
            with Image.open(output_path) as im:
                im.convert("RGBA").save(output_path, "PNG")
        except Exception as e:
            print(f"  ⚠️  Logo is not a usable image ({e}) — rendering without it")
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
    render_id: str,
    wanted:    int = TARGET_SCENES
) -> list:
    """
    Screenshot the page at `wanted` points spread down its full height.
    Identical frames are dropped, so the returned list can be shorter.
    Runs in a thread pool to avoid Windows asyncio issues.
    """

    def take_screenshots_sync(url: str, render_id: str, wanted: int) -> list:
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

                # Spread the captures over the real page height instead of a
                # fixed 0 / 1x / 2x viewport. A page shorter than two viewports
                # used to produce three identical shots, and the finished ad
                # looked like a single frozen image.
                page_height = page.evaluate(
                    "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
                ) or 720
                view = 720
                scrollable = max(0, page_height - view)

                seen_hashes = set()
                for i in range(wanted):
                    offset = 0 if wanted == 1 else int(scrollable * i / (wanted - 1))
                    page.evaluate(f"window.scrollTo(0, {offset})")
                    page.wait_for_timeout(700 if i else 0)

                    path = os.path.join(TEMP_DIR, f"{render_id}_screen{i+1}.png")
                    page.screenshot(path=path, clip=clip)

                    # Identical frames add nothing; skip them so the ad does not
                    # sit on the same picture for two scenes running.
                    with open(path, "rb") as fh:
                        digest = hashlib.md5(fh.read()).hexdigest()
                    if digest in seen_hashes:
                        os.remove(path)
                        print(f"  📸 Shot {i+1} at y={offset}: duplicate, skipped")
                        continue

                    seen_hashes.add(digest)
                    screenshot_paths.append(path)
                    print(f"  📸 Shot {i+1} at y={offset}")

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
            render_id,
            wanted
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
        # Index in the name, not just the source: a long ad reuses a good shot
        # in more than one scene, and a source-derived name would make those
        # clips overwrite each other.
        clip_path = screenshot_path.replace('.png', f'_clip{i}.mp4')
        clip_paths.append(clip_path)

        command = [
            "ffmpeg", "-y",
            "-loop", "1",              # loop the image
            "-i", screenshot_path,     # input image
            "-t", str(time_per_shot),  # duration
            "-vf", (
                # Fill the frame, don't letterbox it. `decrease` + pad fitted
                # the whole image inside 16:9, so a portrait product shot came
                # out as a small picture in a wide black box. Cover-crop
                # instead: scale until it covers, then trim the overflow.
                "scale=1280:720:"
                "force_original_aspect_ratio=increase,"
                "crop=1280:720,"
                "setsar=1"
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
        # This used to fall through to an unconditional "Audio mixed
        # successfully". stdout is the only debugging surface this pipeline
        # has, so a log line that lies about a failed mix is worse than none.
        error = (result.stderr or "").strip()[-400:] or "no stderr"
        print(f"  ⚠️  Audio mix failed, using voiceover only:\n{error}")
        import shutil
        try:
            shutil.copy(voiceover_path, output_path)
        except OSError as copy_err:
            print(f"  ❌ Voiceover fallback also failed: {copy_err}")
            return ""
        print("  ✅ Voiceover-only audio ready (no music bed)")
        return output_path

    print("  ✅ Audio mixed successfully (voiceover + music)")
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
    audio_path:    str = "",
    endcard_path:  str = ""
) -> str:
    """
    Combines all PNG layers + background video into the final MP4.

    Layer order (bottom to top):
      background video
      scrim            -> makes the captions readable
      headline, subtext, CTA
      logo             (optional)
      end card         (optional) -- opaque, covers everything for the last
                       ENDCARD_SECONDS, while every layer above stops

    The graph used to be two hard-coded strings selected by `if has_logo`, each
    with the audio input index written in by hand. A third optional input made
    that untenable, so inputs are appended in order and their indices recorded.
    """
    inputs = []
    index = {}

    def add_input(path: str, name: str):
        """Append an input and remember which ffmpeg index it landed on."""
        index[name] = len(index)
        inputs.extend(["-i", path])

    # Loop the background so it can never run out before -t duration. The
    # per-scene encodes can land a few frames short when the split is not a
    # whole number of frames, which truncated the video against a full-length
    # audio track.
    inputs.extend(["-stream_loop", "-1"])
    add_input(bg_video_path, "bg")
    add_input(overlay_path,  "scrim")
    add_input(headline_path, "headline")
    add_input(subtext_path,  "subtext")
    add_input(cta_path,      "cta")

    has_logo    = bool(logo_path)    and os.path.exists(logo_path)
    has_audio   = bool(audio_path)   and os.path.exists(audio_path)
    has_endcard = bool(endcard_path) and os.path.exists(endcard_path)

    if has_logo:
        add_input(logo_path, "logo")
    if has_endcard:
        # -loop 1 gives the still its own timeline. Without it the input is a
        # single frame pinned at t=0, and the fade below -- which runs on the
        # overlay's own clock, not the main video's -- would never fire.
        inputs.extend(["-loop", "1"])
        add_input(endcard_path, "endcard")
    if has_audio:
        add_input(audio_path, "audio")

    # When the card is showing, nothing else should be: the captions belong to
    # the footage, not to the contact details.
    card_at = max(0.0, duration - ENDCARD_SECONDS)
    if has_endcard:
        # The comma inside the expression has to be escaped or ffmpeg reads it
        # as the end of this filter in the chain.
        gate = f":enable=lt(t\\,{card_at:.2f})"
    else:
        gate = ""

    steps = ["[0:v]scale=1280:720,setsar=1[bg]"]
    stage = "bg"

    def overlay(src_name: str, x, y, out: str, extra: str = ""):
        nonlocal stage
        steps.append(
            f"[{stage}][{index[src_name]}:v]overlay={x}:{y}{extra}[{out}]"
        )
        stage = out

    overlay("scrim",    0,      0,          "s",  gate)
    overlay("headline", SAFE_X, HEADLINE_Y, "h",  gate)
    overlay("subtext",  SAFE_X, SUBTEXT_Y,  "sb", gate)
    overlay("cta",      SAFE_X, CTA_Y,      "c",  gate)

    if has_logo:
        # The logo used to be overlaid at its native size, so a 512x512
        # apple-touch-icon covered the frame from y=30 past the headline. Fit
        # it inside a 180x48 box and tuck it top-left, clear of the captions.
        steps.append(
            f"[{index['logo']}:v]scale=180:48:"
            "force_original_aspect_ratio=decrease[lg]"
        )
        steps.append(f"[{stage}][lg]overlay={SAFE_X}:40{gate}[wl]")
        stage = "wl"

    if has_endcard:
        # Fade the card up over a third of a second. A straight cut from
        # footage to a flat colour card reads as a glitch; the short
        # dissolve is what makes it read as the end of an ad.
        steps.append(
            f"[{index['endcard']}:v]format=yuva420p,"
            f"fade=t=in:st={card_at:.2f}:d={ENDCARD_FADE:.2f}:alpha=1[ec]"
        )
        steps.append(
            f"[{stage}][ec]overlay=0:0:enable=gte(t\\,{card_at:.2f})[final]"
        )
    else:
        steps.append(f"[{stage}]null[final]")

    filter_complex = ";".join(steps)

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
        command += ["-map", f"{index['audio']}:a", "-c:a", "aac", "-b:a", "128k"]
        print(f"  \U0001f50a Audio will be stitched from: {audio_path}")
    else:
        command += ["-an"]

    if has_endcard:
        print(f"  \U0001f3ac End card shows from {card_at:.1f}s to {duration}s")

    command += [output_path]

    run_ffmpeg(command)
    print(f"  \u2705 Video assembled: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════
# SECTION 5 — MAIN FUNCTION
# Orchestrates everything — called by routers/generate.py
# ═══════════════════════════════════════════════════════


# Caller-supplied scene images (the editor's scene picker). Each entry is either
# a data: URL from an upload or an https URL from stock search. Capped hard:
# this is a server fetching a URL a client chose, so it must not be a way to
# stream something unbounded into our temp dir.
MAX_SCENE_BYTES = 8 * 1024 * 1024


def classify_scene_image(path: str) -> dict:
    """Describe one candidate image: {is_face, tone, ui_ness, detail}.

    Cheap, on a 64x64 downsample. Nothing here needs to be exact -- it feeds a
    ranking, not a hard gate, and the worst outcome of a misread is a scene in
    a slightly less ideal order.
    """
    import numpy as np

    try:
        with Image.open(path) as im:
            small = im.convert("RGB").resize((64, 64), Image.BILINEAR)
    except Exception:
        return {"is_face": False, "tone": "mid", "ui_ness": 0.0, "detail": 0.0}

    a = np.asarray(small, dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Skin in the centre -> a portrait. YCbCr skin range, weighted to the middle
    # third where a head sits; a tan UI background in the corners does not count.
    y  = lum
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    skin = (y > 40) & (cb > 77) & (cb < 127) & (cr > 133) & (cr < 173)
    cx = slice(18, 46)
    centre_skin = float(skin[cx, cx].mean())
    is_face = centre_skin > 0.30

    # UI-ness: large flat areas (panels, backgrounds) in 8x8 blocks. A photo is
    # busy everywhere; an app screenshot has big uniform regions.
    flat = 0
    for by in range(8):
        for bx in range(8):
            blk = lum[by * 8:(by + 1) * 8, bx * 8:(bx + 1) * 8]
            if blk.std() < 8:
                flat += 1
    ui_ness = flat / 64.0

    mean_lum = float(lum.mean())
    tone = "light" if mean_lum > 150 else "dark" if mean_lum < 95 else "mid"
    detail = float(lum.std())

    return {"is_face": is_face, "tone": tone, "ui_ness": ui_ness, "detail": detail}


def select_scenes(candidates: list, intent: str, wanted: int) -> list:
    """Pick and order the best `wanted` of the resolved page images.

    `candidates` is [(path, src, rank)] where rank is the scrape's own priority
    position (0 = the owner's og:image/hero). Returns the chosen subset as
    [(path, src)], best-opening-scene first.
    """
    if not candidates:
        return []

    scored = []
    for path, src, rank in candidates:
        f = classify_scene_image(path)
        # Start from the owner's own ranking: earlier is better.
        score = -float(rank)

        # Faces are down-ranked, harder for a product/dev-tool ad than for a
        # site that might legitimately be about people. Never dropped outright
        # -- a low score just means "only if nothing better fills the slot".
        if f["is_face"]:
            score -= 40 if intent in ("saas", "commerce") else 22

        # Intent nudges: a dev-tool's product is its UI; a store's is its goods.
        if intent == "saas" and f["ui_ness"] > 0.40:
            score += 10
        if intent == "commerce" and not f["is_face"] and f["ui_ness"] < 0.35:
            score += 8  # a real photograph, not a screenshot

        # A near-empty frame (almost all one flat tone) is dull footage.
        if f["detail"] < 10:
            score -= 8

        scored.append({"path": path, "src": src, "rank": rank, "score": score, **f})

    scored.sort(key=lambda s: -s["score"])

    # Coherence: anchor on the best non-face image's tone and prefer matches, so
    # the ad does not lurch between a white UI and a dark office portrait.
    anchor = next((s for s in scored if not s["is_face"] and s["tone"] != "mid"), scored[0])
    target = anchor["tone"]
    for s in scored:
        if s["tone"] == target:
            s["score"] += 6
    scored.sort(key=lambda s: -s["score"])

    # Return every candidate, ranked, flagged face/not. The caller decides how
    # many to use and how to fill a shortfall — reusing good footage beats
    # padding a long ad with faces or footer screenshots.
    print(
        f"  🎯 Ranked {len(scored)} page image(s) for intent '{intent}', "
        f"tone '{target}' ({sum(1 for s in scored if not s['is_face'])} non-face)"
    )
    return [(s["path"], s["src"], s["is_face"]) for s in scored]


def _flatten_for_render(im: "Image.Image") -> "Image.Image":
    """RGBA/paletted -> RGB over a near-white ground.

    convert("RGB") composites transparency over black, which left the
    transparent UI exports and badges on light-themed sites floating in a void.
    These pages are light, so near-white is what they were designed against.
    """
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (245, 246, 248))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def _vet_scene_image(im: "Image.Image") -> str:
    """Why this PAGE image makes poor footage, or "" if it is fine.

    A scrape pulls in award badges, compliance marks, logo walls and icon
    strips next to real photography. On a 16:9 frame those read as meaningless
    fragments. Only page images pass through here; uploads and screenshots do
    not.
    """
    w, h = im.size
    # Resolution floor, two ways. A scene is cover-cropped up to 1280x720, so a
    # small image is scaled 2-3x and looks blurry on screen. min < 300 is an
    # icon/badge; a long side under 700 means even a well-proportioned shot
    # upscales past ~1.8x — visibly soft.
    if min(w, h) < 300:
        return f"too small ({w}x{h}) -- an icon or badge"
    if max(w, h) < 700:
        return f"low resolution ({w}x{h}) -- would be blurry at 720p"

    ar = w / h if h else 0
    if ar > 2.6 or ar < 0.42:
        return f"aspect {ar:.1f}:1 -- a banner or logo strip"

    # Downsample before measuring: per-pixel stats over a 3000px banner would
    # be hundreds of thousands of Python iterations.
    small = im.convert("RGBA").resize((48, 48), Image.BILINEAR)
    px = list(small.getdata())
    transparent = sum(1 for q in px if q[3] < 24) / len(px)
    if transparent > 0.55:
        return f"{transparent*100:.0f}% transparent -- a logo or badge"

    opaque = [(r, g, b) for r, g, b, a in px if a > 24]
    if opaque:
        lum = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in opaque]
        m = sum(lum) / len(lum)
        sd = (sum((x - m) ** 2 for x in lum) / len(lum)) ** 0.5
        if sd < 8:
            return f"near-flat (sd {sd:.0f}) -- a solid colour block"

    return ""


async def resolve_scene_images(
    sources: list, render_id: str, vet: bool = False
) -> list:
    """Turn scene image sources into local file paths, position-preserving.

    Returns a list the same length as `sources`, holding a path or None. Keeping
    the positions matters: the editor sends one entry per scene and only some of
    them are user replacements, so collapsing the gaps would shift every scene
    after the first swap. A source that fails costs that scene, not the render.

    `vet=True` additionally drops images that make poor footage (badges, logo
    strips, flat colour blocks). Pass it for PAGE images only -- never for
    editor uploads, which the user chose on purpose.
    """
    import base64
    import binascii

    paths = [None] * len(sources)
    for i, src in enumerate(sources):
        if not src or not isinstance(src, str):
            continue

        out = os.path.join(TEMP_DIR, f"{render_id}_scene{i}.png")
        try:
            if src.startswith("data:"):
                header, _, payload = src.partition(",")
                if "base64" not in header:
                    print(f"  ⚠️  Scene {i+1}: only base64 data URLs are accepted")
                    continue
                raw = base64.b64decode(payload, validate=False)
                if len(raw) > MAX_SCENE_BYTES:
                    print(f"  ⚠️  Scene {i+1}: image over {MAX_SCENE_BYTES // 1024 // 1024}MB, skipped")
                    continue
                with open(out, "wb") as fh:
                    fh.write(raw)

            elif src.startswith(("http://", "https://")):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        src, timeout=aiohttp.ClientTimeout(total=20)
                    ) as response:
                        if response.status != 200:
                            print(f"  ⚠️  Scene {i+1}: fetch returned {response.status}")
                            continue
                        # read(n) returns *up to* n bytes, not n — a single
                        # call truncates any response that arrives in more
                        # than one chunk. Drain it, with the cap enforced.
                        raw = b""
                        async for chunk in response.content.iter_chunked(65536):
                            raw += chunk
                            if len(raw) > MAX_SCENE_BYTES:
                                break
                        if len(raw) > MAX_SCENE_BYTES:
                            print(f"  ⚠️  Scene {i+1}: image too large, skipped")
                            continue
                with open(out, "wb") as fh:
                    fh.write(raw)
            else:
                print(f"  ⚠️  Scene {i+1}: unsupported source, skipped")
                continue

            # Normalise through Pillow: proves it decodes, and hands ffmpeg a
            # format it understands. Flatten over white, not convert("RGB")'s
            # black default, so transparent exports are readable not voids.
            with Image.open(out) as im:
                im.load()
                if vet:
                    reason = _vet_scene_image(im)
                    if reason:
                        print(f"  ⏭️  Scene image skipped: {reason}")
                        try:
                            os.remove(out)
                        except OSError:
                            pass
                        continue
                _flatten_for_render(im).save(out, "PNG")

            # Assign by index, not append: the list is pre-sized to one slot
            # per scene so a partial swap keeps its positions.
            paths[i] = out
            print(f"  ✅ Scene {i+1} image ready")

        except (OSError, ValueError, binascii.Error, aiohttp.ClientError) as e:
            print(f"  ⚠️  Scene {i+1}: {e}")
            continue

    return paths


def _sweep_temp(render_id: str) -> int:
    """
    Delete every scratch file this render wrote.

    The old cleanup named five paths while a render creates about a dozen --
    the logo, one PNG per scene, the gap-filler's "{id}_fill_*" images, the
    screenshots, and four audio files. Matching on the render id catches all of
    them and cannot drift out of sync with the code that creates them.
    """
    removed = 0
    try:
        entries = os.listdir(TEMP_DIR)
    except OSError:
        return 0

    for name in entries:
        if not name.startswith(render_id):
            continue
        try:
            os.remove(os.path.join(TEMP_DIR, name))
            removed += 1
        except OSError:
            pass       # still held open on Windows; the next render retries
    return removed


async def assemble_video(
    script:        dict,
    business_name: str,
    colors:        dict,
    logo_url:      str,
    duration:      int = 15,
    website_url:   str = "",
    scene_images:  list | None = None,
    content_images: list | None = None,
    end_card:      dict | None = None,
    scene_count:   int | None = None,
    site_intent:   str = "unknown",
) -> dict:
    """
    Render an ad. See _assemble_render for the pipeline itself.

    This wrapper exists for the finally: assembly has no shortage of ways to
    raise, and every one of them used to leave that render's scratch files
    behind in temp/ forever.
    """
    render_id = generate_id()
    try:
        return await _assemble_render(
            render_id,
            script=script,
            business_name=business_name,
            colors=colors,
            logo_url=logo_url,
            duration=duration,
            website_url=website_url,
            scene_images=scene_images,
            content_images=content_images,
            end_card=end_card,
            scene_count=scene_count,
            site_intent=site_intent,
        )
    finally:
        swept = _sweep_temp(render_id)
        if swept:
            print(f"\n🧹 Cleaned up {swept} temp file(s) for {render_id}")


async def _assemble_render(
    render_id:     str,
    script:        dict,
    business_name: str,
    colors:        dict,
    logo_url:      str,
    duration:      int = 15,
    website_url:   str = "",
    scene_images:  list | None = None,
    content_images: list | None = None,
    end_card:      dict | None = None,
    scene_count:   int | None = None,
    site_intent:   str = "unknown",
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
    accent_color      = colors.get("accent",            "#6c63ff")

    # ── Step 1: Get background video ─────────────────
    print("\n📥 Step 1: Getting background video...")

    # Scene images supplied by the caller (the editor's scene picker) replace
    # the screenshot capture entirely — they are already the frames we want,
    # and skipping Playwright makes a re-render markedly faster.
    # Bound up-front. The Pexels-only branch below never assigned this, so a
    # render with no site URL and no page images raised UnboundLocalError on
    # the final return, after every expensive step had already run.
    screenshot_paths: list = []

    # Where each finished scene's picture came from: a URL when we can name it,
    # "" for a scene cut from a screenshot or stock footage, which the editor
    # cannot ask for again by name.
    scene_sources: list = []

    # How many scenes this ad is cut into — scales with its length, so a 30s ad
    # is not the same six shots a 15s ad has, each held twice as long.
    target_scenes = scenes_for_duration(duration)
    if target_scenes != TARGET_SCENES:
        print(f"  🎬 {duration}s ad → {target_scenes} scenes")

    # A card with nothing on it is not a card. Only a real value counts, so an
    # untouched Banner panel does not cost the ad three seconds of footage.
    wants_endcard = bool(end_card) and any(
        str(v or "").strip() for v in (end_card or {}).values()
    )

    # The footage is squeezed into the time before the card so every scene
    # still gets its full share on screen. Without this the last image would be
    # hidden underneath the card and effectively wasted.
    bg_seconds = (duration - ENDCARD_SECONDS) if wants_endcard else duration
    if wants_endcard:
        print(f"  🎬 Footage runs {bg_seconds:.1f}s, then the end card")

    supplied = await resolve_scene_images(scene_images or [], render_id)

    # An explicit count wins. The editor sends it when scenes have been added
    # beyond what the site yielded, and those new slots start empty -- so
    # inferring the count from "entries that carry an image" would drop them.
    if scene_count:
        if len(supplied) < scene_count:
            supplied.extend([None] * (scene_count - len(supplied)))
        else:
            supplied = supplied[:scene_count]

    # Take this path whenever the caller said how many scenes it wants, even if
    # it filled none of them in -- the gap-filler below sources those from the
    # page's own photos.
    if supplied and (any(supplied) or scene_count):
        # Fill any scene the caller did not replace, so a partial swap keeps
        # the other scenes instead of dropping them. Prefer the site's own
        # photos — those are what the ad was cut from — and only fall back to
        # a fresh capture if we have none.
        # What the caller asked for, slot by slot, padded to match `supplied`.
        asked = list(scene_images or [])
        asked = (asked + [""] * len(supplied))[: len(supplied)]

        if not all(supplied):
            filler, filler_src = [], []
            if content_images:
                print(f"  🖼️  Filling un-replaced scenes from {len(content_images)} page image(s)")
                pool_srcs = list(content_images)[: target_scenes * 2]
                resolved = await resolve_scene_images(pool_srcs, f"{render_id}_fill", vet=True)
                for src, path in zip(pool_srcs, resolved):
                    if path:
                        filler.append(path)
                        filler_src.append(src)

            if not filler and website_url:
                if not website_url.startswith(('http://', 'https://')):
                    website_url = 'https://' + website_url
                print("  📸 Capturing screenshots for the scenes not replaced...")
                filler = await capture_website_screenshots(
                    url=website_url, render_id=render_id, wanted=len(supplied)
                )
                # A screenshot lives in temp/ and is deleted with the render,
                # so there is no source the editor could name later.
                filler_src = [""] * len(filler)

            for i, item in enumerate(supplied):
                if item is None and filler:
                    j = i if i < len(filler) else len(filler) - 1
                    supplied[i] = filler[j]
                    asked[i] = filler_src[j]

        final_paths = [s for s in supplied if s]
        scene_sources = [src or "" for pth, src in zip(supplied, asked) if pth]
        if final_paths:
            print(f"  🖼️  Background from {len(final_paths)} scene image(s)")
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, screenshots_to_video, final_paths, bg_path, bg_seconds
                )
            screenshot_paths = final_paths

    elif website_url or content_images:
        # Ensure URL has https://
        if website_url and not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url

        # The site's own photography first. A page's hero and product shots
        # make far better footage than pictures of its own layout, and they are
        # genuinely different from each other — three screenshots of a short
        # page are often the same image three times.
        gathered, gathered_src = [], []
        if content_images:
            print(f"  🖼️  Trying {len(content_images)} image(s) from the page")
            pool_srcs = list(content_images)[: target_scenes * 2]
            resolved = await resolve_scene_images(pool_srcs, render_id, vet=True)
            # Classify every survivor and pick the best, coherent set -- not
            # just the first N in scrape order. This is what keeps a dev-tool's
            # founder headshots out of the ad in favour of its product UI.
            cands = [
                (path, src, idx)
                for idx, (src, path) in enumerate(zip(pool_srcs, resolved))
                if path
            ]
            ranked = select_scenes(cands, site_intent, target_scenes)
            good  = [(p, s) for p, s, is_face in ranked if not is_face]
            faces = [(p, s) for p, s, is_face in ranked if is_face]

            if len(good) >= target_scenes:
                picks = good[:target_scenes]
            elif len(good) >= 3:
                # Enough good footage to carry the ad, but fewer than a long ad
                # wants. Reuse the good shots to reach the count rather than
                # padding with founder faces or footer/cookie-banner
                # screenshots — the exact scrappiness this is here to avoid.
                # Repeats land ~len(good) apart, never back to back.
                picks = [good[i % len(good)] for i in range(target_scenes)]
                if len(good) < target_scenes:
                    print(f"  🔁 Reusing {len(good)} good shot(s) to reach {target_scenes} scenes")
            else:
                # Genuinely image-poor: take what there is (faces included) and
                # let the screenshot top-up below fill the rest.
                picks = (good + faces)[:target_scenes]

            gathered     = [p for p, s in picks]
            gathered_src = [s for p, s in picks]
            print(f"  ✅ {len(gathered)} content scene(s) "
                  f"({len(good)} distinct good, {len(faces)} face(s) available)")

        # Top up with screenshots if the page gave us too few.
        if len(gathered) < target_scenes and website_url:
            need = target_scenes - len(gathered)
            print(f"  📸 Topping up with {need} screenshot(s) from: {website_url}")
            shots = await capture_website_screenshots(
                url=website_url,
                render_id=render_id,
                wanted=need,
            )
            taken = shots[:need]
            gathered.extend(taken)
            # Screenshots are scratch files; nothing to name them by later.
            gathered_src.extend([""] * len(taken))

        screenshot_paths = gathered
        scene_sources = gathered_src

        if screenshot_paths:
            # Turn screenshots into background video with Ken Burns zoom
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool,
                    screenshots_to_video,
                    screenshot_paths,
                    bg_path,
                    bg_seconds
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

    # ── Step 2.5: Build the end card ──────────────────
    # After the logo, because the card puts the logo at the top of itself.
    endcard_path = ""
    if wants_endcard:
        print("\n🎬 Step 2.5: Building the end card...")
        endcard_path = os.path.join(TEMP_DIR, f"{render_id}_endcard.png")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            endcard_path = await loop.run_in_executor(
                pool, create_endcard_image,
                end_card, primary_color, accent_color,
                endcard_path, actual_logo_path,
            )

    # ── Step 3: Create visual layers ─────────────────
    print("\n Step 3: Creating visual layers...")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:

        await loop.run_in_executor(
            pool, create_overlay_image,
            VIDEO_WIDTH, VIDEO_HEIGHT, "#000000", SCRIM_MAX_ALPHA, overlay_path
        )

        # Captions live in a left column, so each layer is only as wide as the
        # text block. The right of the frame stays clear for the imagery.
        await loop.run_in_executor(
            pool, create_text_image,
            headline, TEXT_BLOCK_W, HEADLINE_H, HEADLINE_SIZE, "#ffffff",
            headline_path, True, "left"
        )

        await loop.run_in_executor(
            pool, create_text_image,
            subtext, TEXT_BLOCK_W, SUBTEXT_H, SUBTEXT_SIZE, "#dfe3ea",
            subtext_path, False, "left"
        )

        cta_bg, cta_fg = pick_cta_colors(primary_color, accent_color)
        await loop.run_in_executor(
            pool, create_cta_image,
            cta, TEXT_BLOCK_W, CTA_H,
            cta_bg, cta_fg, cta_path, "left"
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
            # Generate speech at the calm base pace (tts.DEFAULT_SPEED).
            await generate_voiceover(
                text=voiceover_text,
                output_path=voiceover_wav
            )

            # Fit the narration inside the ad so its final line always lands.
            # mix_audio hard-cuts at -t duration, so a voiceover even slightly
            # longer than the ad loses its last words — which is exactly what a
            # calm (slower) pace plus an over-length script produced. Leave a
            # short tail, and only ever speed up: a short script is left calm,
            # never stretched into a drag.
            import wave
            import contextlib
            try:
                with contextlib.closing(wave.open(voiceover_wav, "rb")) as w:
                    vo_dur = w.getnframes() / float(w.getframerate() or 1)
            except Exception:
                vo_dur = 0.0

            fit_target = max(1.0, duration - 0.4)
            if vo_dur > fit_target + 0.05:
                factor = vo_dur / fit_target            # > 1 → speed up
                if factor <= 2.0:
                    afilter = f"atempo={factor:.3f}"
                else:                                   # atempo caps at 2x each
                    half = factor ** 0.5
                    afilter = f"atempo={half:.3f},atempo={half:.3f}"
                print(f"  🗣️  Narration {vo_dur:.1f}s > {fit_target:.1f}s — "
                      f"nudging {factor:.2f}x so the full script is heard")
                r = subprocess.run(
                    ["ffmpeg", "-y", "-i", voiceover_wav, "-filter:a", afilter,
                     "-codec:a", "libmp3lame", "-qscale:a", "2", voiceover_mp3],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print("  ⚠️  Fit failed — using natural pace")
                    wav_to_mp3(voiceover_wav, voiceover_mp3)
            else:
                wav_to_mp3(voiceover_wav, voiceover_mp3)
            voiceover_final = voiceover_mp3

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
            output_path, duration, audio_path, endcard_path
        )

    # ── Step 5: Cleanup temp files ────────────────────
    # Temp files are swept by assemble_video's finally, so they go away on
    # the error paths too -- this used to be a bare loop right here that only
    # ran when nothing had raised.
    #
    # Verify the render actually produced something first. Every step above
    # could fail softly (mix_audio falls back, the Pillow layers swallow
    # errors), and handing back a URL for a file that is not there shows the
    # user a broken player instead of an error.
    if not os.path.isfile(output_path):
        raise RuntimeError(
            "Render finished but wrote no output file -- see the FFmpeg log above."
        )

    size = os.path.getsize(output_path)
    if size < MIN_OUTPUT_BYTES:
        raise RuntimeError(
            f"Render wrote only {size} bytes, too small to be a playable "
            f"{duration}s video -- see the FFmpeg log above."
        )

    print(f"\n✅ Video assembly complete!")
    print(f"   Output: {output_path} ({size // 1024} KB)")
    print(f"   Render ID: {render_id}")

    return {
        "render_id":     render_id,
        "video_path":    output_path,
        "url":           f"/api/output/{render_id}_ad.mp4",
        "status":        "done",
        # How many shots the ad was actually cut from. The editor needs this to
        # lay out its scene list — a page that yields four usable images makes a
        # four-scene ad, not six.
        "scene_count":   len(screenshot_paths) or target_scenes,
        # One entry per scene: the URL it was built from, or "" for a scene cut
        # from a screenshot or stock clip. The editor sends these back so that
        # deleting one scene does not reshuffle the others.
        "scene_sources": scene_sources,
        # The editor draws its timeline from this: the card is a real segment
        # of the video, not another replaceable scene.
        "has_end_card":  bool(endcard_path),
        "end_card_at":   round(duration - ENDCARD_SECONDS, 2) if endcard_path else None,
        "thumbnail_url": ""
    }