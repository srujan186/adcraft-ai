# services/scraper.py
# ONE job: visit a URL, extract brand information
# Complete file — all functions in correct order

import asyncio
import httpx
import re
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# ═══════════════════════════════════════════════════════
# SECTION 1 — HELPER FUNCTIONS
# Small utility functions used by everything below
# ═══════════════════════════════════════════════════════

def clean_url(url: str) -> str:
    """
    Make sure URL has https:// prefix.
    Handles: apple.com, www.apple.com, https://apple.com
    """
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def make_absolute(url: str, base_url: str) -> str:
    """
    Convert relative URLs to absolute URLs.
    /logo.png + https://apple.com → https://apple.com/logo.png
    //cdn.apple.com/logo.png     → https://cdn.apple.com/logo.png
    """
    if not url:
        return ""
    url = url.strip()
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('//'):
        return 'https:' + url
    return urljoin(base_url, url)


def is_valid_color(color: str) -> bool:
    """
    Check if a string is a valid CSS color.
    Handles: #fff, #ffffff, rgb(0,0,0)
    """
    if not color:
        return False
    color = color.strip()
    if re.match(r'^#[0-9a-fA-F]{3}$', color):
        return True
    if re.match(r'^#[0-9a-fA-F]{6}$', color):
        return True
    if re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', color):
        return True
    return False


def normalize_color(color: str) -> str:
    """
    Convert any valid color to 6-digit hex.
    #fff → #ffffff
    rgb(0,0,255) → #0000ff
    """
    color = color.strip()
    if re.match(r'^#[0-9a-fA-F]{3}$', color):
        r, g, b = color[1], color[2], color[3]
        return f"#{r}{r}{g}{g}{b}{b}"
    rgb_match = re.match(
        r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$', color
    )
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


def is_neutral_color(color: str) -> bool:
    """
    Returns True if color is a mid-range gray.
    We skip these when looking for brand colors.
    NOTE: We allow pure black and pure white —
    brands like Apple and Nike use these intentionally.
    """
    if not color.startswith('#') or len(color) < 7:
        return True
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        # Check if R, G, B are all very similar = gray
        max_diff = max(abs(r - g), abs(g - b), abs(r - b))
        if max_diff < 30:
            # It is a gray shade
            # But allow pure black and pure white
            is_pure_black = r < 10 and g < 10 and b < 10
            is_pure_white = r > 245 and g > 245 and b > 245
            if not is_pure_black and not is_pure_white:
                return True  # mid-gray — skip it
        return False
    except Exception:
        return True


def is_light_color(color: str) -> bool:
    """
    Returns True if the color is light (closer to white).
    Used to identify secondary/background colors.
    """
    if not color.startswith('#') or len(color) < 7:
        return False
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.6
    except Exception:
        return False


def build_fallback_data(url: str) -> dict:
    """
    When ALL scraping methods fail, return sensible defaults.
    The app NEVER crashes — always returns something usable.
    The scrape_failed flag tells the frontend to show
    a manual input form instead of auto-filled fields.
    """
    domain = urlparse(url).netloc.replace('www.', '')
    name = domain.split('.')[0].title()
    return {
        "business_name": name,
        "description":   f"{name} - providing quality products and services.",
        "tagline":       f"Welcome to {name}",
        "logo_url":      "",
        "colors": {
            "primary":   "#1a1a2e",
            "secondary": "#ffffff",
            "accent":    "#6c63ff"
        },
        "features":      [],
        "domain":        domain,
        "url":           url,
        "scrape_failed": True,
        "scrape_message": (
            "We couldn't automatically read this website. "
            "This happens with sites that have bot protection. "
            "You can still create an ad by filling in your "
            "business details below."
        )
    }


# ═══════════════════════════════════════════════════════
# SECTION 2 — EXTRACTOR FUNCTIONS
# Each one extracts ONE piece of brand data from HTML
# ═══════════════════════════════════════════════════════

def extract_business_name(soup, domain: str) -> str:
    """
    Try to find the business name.
    Strategy order: og:site_name → title tag → domain name
    """
    # Strategy 1: og:site_name — most reliable
    og_site = soup.find('meta', property='og:site_name')
    if og_site and og_site.get('content', '').strip():
        return og_site['content'].strip()

    # Strategy 2: Title tag — split on | or - to get brand name only
    title_tag = soup.find('title')
    if title_tag and title_tag.text.strip():
        name = re.split(r'[|\-–—]', title_tag.text)[0].strip()
        if name and len(name) < 60:
            return name

    # Strategy 3: Fall back to domain name
    return domain.split('.')[0].title()


def extract_description(soup) -> str:
    """
    Find the business description.
    Strategy order: meta description → og:description → first paragraph
    """
    # Strategy 1: meta description tag
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content', '').strip():
        return meta_desc['content'].strip()[:400]

    # Strategy 2: og:description
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content', '').strip():
        return og_desc['content'].strip()[:400]

    # Strategy 3: First meaningful paragraph
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if 50 < len(text) < 500:
            return text[:400]

    return "A business offering quality products and services."


def extract_tagline(soup) -> str:
    """
    Find the main headline/tagline.
    """
    # Strategy 1: Hero/banner section heading
    hero_words = ['hero', 'banner', 'jumbotron', 'masthead', 'headline']
    for section in soup.find_all(['div', 'section']):
        classes = ' '.join(section.get('class', [])).lower()
        if any(word in classes for word in hero_words):
            h = section.find(['h1', 'h2'])
            if h:
                text = h.get_text(strip=True)
                if text and len(text.split()) > 1 and len(text) < 120:
                    return text

    # Strategy 2: First h1 on page
    h1 = soup.find('h1')
    if h1:
        text = h1.get_text(strip=True)
        if text and len(text.split()) > 1 and len(text) < 120:
            return text

    # Strategy 3: og:title only if descriptive
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content', '').strip():
        title = og_title['content'].strip()
        if len(title.split()) > 2 and len(title) < 120:
            return title

    # Strategy 4: First sentence of meta description
    # Better than empty — gives Claude something to work with
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content', ''):
        desc = meta_desc['content'].strip()
        first_sentence = desc.split('.')[0].strip()
        if 10 < len(first_sentence) < 120:
            return first_sentence

    return ""

def extract_logo(soup, base_url: str) -> str:
    """
    Find the logo URL using 6 strategies.
    Actively rejects banner/hero images.
    Returns best candidate based on priority scoring.
    """

    # Images with these words in URL are banners, not logos
    banner_keywords = [
        'hero', 'banner', 'cover', 'background', 'bg-',
        'splash', 'header-image', 'feature', 'gallery',
        'tv-gallery', 'promo', 'campaign', 'masthead',
        'billboard', 'poster', 'thumbnail', 'preview',
        'og-image', 'social', 'share', 'card',
        '_hero_', '-hero-', '_banner_', '-banner-',
        'logo_hero',
    ]

    def is_likely_logo(url: str) -> bool:
        url_lower = url.lower()
        for keyword in banner_keywords:
            if keyword in url_lower:
                return False
        return True

    candidates = []

    # Strategy 1: og:image — only if it looks like a logo
    og_image = soup.find('meta', property='og:image')
    if og_image:
        url = og_image.get('content', '').strip()
        if url and is_likely_logo(url):
            candidates.append({
                "url":      make_absolute(url, base_url),
                "priority": 3,
                "source":   "og:image"
            })
        elif url:
            print(f"  ⏭️ Skipped og:image (banner): {url[:60]}")

    # Strategy 2: Apple touch icon — high quality square icon
    for rel in ['apple-touch-icon', 'apple-touch-icon-precomposed']:
        icons = soup.find_all('link', rel=rel)
        for icon in icons:
            href = icon.get('href', '').strip()
            if href:
                sizes = icon.get('sizes', '0x0')
                size = int(sizes.split('x')[0]) if sizes and 'x' in sizes else 0
                candidates.append({
                    "url":      make_absolute(href, base_url),
                    "priority": 5 + (size // 100),
                    "source":   f"apple-touch-icon ({sizes})"
                })

    # Strategy 3: Standard favicons — skip .ico files (too small)
    icons = soup.find_all('link', rel=lambda r: r and 'icon' in r)
    for icon in icons:
        href = icon.get('href', '').strip()
        if not href or href.endswith('.ico'):
            continue
        sizes = icon.get('sizes', '0x0')
        size = int(sizes.split('x')[0]) if sizes and 'x' in sizes else 16
        candidates.append({
            "url":      make_absolute(href, base_url),
            "priority": 2 + (size // 100),
            "source":   "link[rel=icon]"
        })

    # Strategy 4: img tags explicitly marked as logo
    logo_keywords = ['logo', 'brand', 'site-logo', 'company-logo']
    for img in soup.find_all('img'):
        src       = img.get('src', '').strip()
        alt       = img.get('alt', '').lower()
        css_class = ' '.join(img.get('class', [])).lower()
        img_id    = img.get('id', '').lower()

        if not src or src.startswith('data:'):
            continue
        if not is_likely_logo(src):
            continue

        is_logo = any(
            keyword in field
            for keyword in logo_keywords
            for field in [src.lower(), alt, css_class, img_id]
        )
        if is_logo:
            candidates.append({
                "url":      make_absolute(src, base_url),
                "priority": 6,
                "source":   f"img[logo] alt='{alt}'"
            })

    # Strategy 5: SVG images — logos are very often SVG
    for img in soup.find_all('img'):
        src = img.get('src', '').strip()
        if src.lower().endswith('.svg') and is_likely_logo(src):
            candidates.append({
                "url":      make_absolute(src, base_url),
                "priority": 7,
                "source":   "svg image"
            })

    # Strategy 6: Twitter card image
    twitter_img = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_img:
        url = twitter_img.get('content', '').strip()
        if url and is_likely_logo(url):
            candidates.append({
                "url":      make_absolute(url, base_url),
                "priority": 2,
                "source":   "twitter:image"
            })

    if not candidates:
        print("  ⚠️ No logo found")
        return ""

    # Pick highest priority candidate
    candidates.sort(key=lambda x: x['priority'], reverse=True)
    print(f"  🖼️ Found {len(candidates)} logo candidates")
    for c in candidates[:3]:
        print(f"     [{c['priority']}] {c['source']}: {c['url'][:60]}")

    best = candidates[0]
    print(f"  ✅ Logo selected: {best['source']}")
    return best['url']


def extract_colors_from_stylesheets(soup, base_url: str) -> list:
    """
    Fetch external CSS files and extract brand colors.
    Only checks first 2 stylesheets to stay fast.
    Called when all other color strategies find nothing.
    """
    found = []
    stylesheets = []

    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href', '').strip()
        if href:
            stylesheets.append(make_absolute(href, base_url))

    for css_url in stylesheets[:2]:
        try:
            # urlopen natively supports file:// and ftp:// — unlike httpx — so a
            # page linking <link rel="stylesheet" href="file:///..."> would
            # otherwise reach a local file read. Only http(s) is a stylesheet.
            if urlparse(css_url).scheme not in ("http", "https"):
                print(f"  ⚠️  Skipping non-http stylesheet: {css_url[:60]}")
                continue

            print(f"  📄 Fetching CSS: {css_url[:60]}")
            with urllib.request.urlopen(css_url, timeout=5) as response:
                css_text = response.read().decode('utf-8', errors='ignore')

            # Look for CSS variable declarations
            var_patterns = [
                r'--primary[^:]*:\s*(#[0-9a-fA-F]{3,6})',
                r'--brand[^:]*:\s*(#[0-9a-fA-F]{3,6})',
                r'--accent[^:]*:\s*(#[0-9a-fA-F]{3,6})',
                r'--color-primary[^:]*:\s*(#[0-9a-fA-F]{3,6})',
                r'--theme[^:]*:\s*(#[0-9a-fA-F]{3,6})',
            ]
            for pattern in var_patterns:
                matches = re.findall(pattern, css_text)
                for color in matches:
                    if is_valid_color(color) and not is_neutral_color(color):
                        found.append({
                            "color":    color,
                            "priority": 8,
                            "source":   "external-css-variable"
                        })
                        print(f"  🎨 external CSS var: {color}")

            # Count most used non-neutral colors in CSS
            all_colors = re.findall(r'#([0-9a-fA-F]{6})\b', css_text)
            color_counts = {}
            for c in all_colors:
                full = f"#{c}"
                if not is_neutral_color(full):
                    color_counts[full] = color_counts.get(full, 0) + 1

            sorted_colors = sorted(
                color_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for color, count in sorted_colors[:2]:
                if count >= 3:
                    found.append({
                        "color":    color,
                        "priority": 6,
                        "source":   f"external-css-frequent ({count}x)"
                    })
                    print(f"  🎨 CSS frequent: {color} ({count}x)")

        except Exception as e:
            print(f"  ⚠️ Could not fetch CSS: {e}")
            continue

    return found


def extract_colors(soup, base_url: str = "", html: str = "") -> dict:
    """
    Extract brand colors using 6 strategies.
    Builds a primary + secondary + accent color palette.
    """
    colors = {
        "primary":   "#1a1a2e",
        "secondary": "#ffffff",
        "accent":    "#6c63ff"
    }
    found_colors = []

    # Strategy 1: theme-color meta tag
    theme = soup.find('meta', attrs={'name': 'theme-color'})
    if theme:
        color = theme.get('content', '').strip()
        if is_valid_color(color):
            found_colors.append({
                "color":    normalize_color(color),
                "priority": 10,
                "source":   "theme-color"
            })
            print(f"  🎨 theme-color: {color}")

    # Strategy 2: msapplication TileColor
    tile = soup.find('meta', attrs={'name': 'msapplication-TileColor'})
    if tile:
        color = tile.get('content', '').strip()
        if is_valid_color(color):
            found_colors.append({
                "color":    normalize_color(color),
                "priority": 8,
                "source":   "tile-color"
            })
            print(f"  🎨 tile-color: {color}")

    # Strategy 3: Inline styles on header, nav, body
    for selector in ['header', 'nav', 'body']:
        element = soup.find(selector)
        if not element:
            continue
        style = element.get('style', '')
        if not style:
            continue
        color_patterns = [
            r'background-color:\s*(#[0-9a-fA-F]{3,6})',
            r'background:\s*(#[0-9a-fA-F]{3,6})',
            r'color:\s*(#[0-9a-fA-F]{3,6})',
        ]
        for pattern in color_patterns:
            match = re.search(pattern, style)
            if match:
                color = match.group(1)
                if is_valid_color(color):
                    found_colors.append({
                        "color":    normalize_color(color),
                        "priority": 7,
                        "source":   f"inline-{selector}"
                    })
                    print(f"  🎨 inline {selector}: {color}")

    # Strategy 4: CSS variables inside <style> tags
    for style_tag in soup.find_all('style'):
        css_text = style_tag.string or ''
        if not css_text:
            continue
        css_var_patterns = [
            r'--primary[^:]*:\s*(#[0-9a-fA-F]{3,6})',
            r'--brand[^:]*:\s*(#[0-9a-fA-F]{3,6})',
            r'--accent[^:]*:\s*(#[0-9a-fA-F]{3,6})',
            r'--color-primary[^:]*:\s*(#[0-9a-fA-F]{3,6})',
            r'--main-color[^:]*:\s*(#[0-9a-fA-F]{3,6})',
        ]
        for pattern in css_var_patterns:
            matches = re.findall(pattern, css_text)
            for color in matches:
                if is_valid_color(color):
                    found_colors.append({
                        "color":    color,
                        "priority": 9,
                        "source":   "css-variable"
                    })
                    print(f"  🎨 CSS variable: {color}")

    # Strategy 5: Most frequently used colors in raw HTML
    if html:
        all_hex = re.findall(r'#([0-9a-fA-F]{6})\b', html)
        color_counts = {}
        for c in all_hex:
            full = f"#{c}"
            if not is_neutral_color(full):
                color_counts[full] = color_counts.get(full, 0) + 1
        sorted_colors = sorted(
            color_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for color, count in sorted_colors[:3]:
            if count >= 2:
                found_colors.append({
                    "color":    color,
                    "priority": 3,
                    "source":   f"frequent ({count}x)"
                })
                print(f"  🎨 frequent: {color} ({count}x)")

    # Strategy 6: External CSS files — only if nothing found yet
    if base_url and not found_colors:
        print("  🔍 No colors found — checking external CSS...")
        css_colors = extract_colors_from_stylesheets(soup, base_url)
        found_colors.extend(css_colors)

    # Build final color palette from all candidates
    if found_colors:
        found_colors.sort(key=lambda x: x['priority'], reverse=True)

        # Remove duplicates, keep highest priority
        seen = set()
        unique_colors = []
        for item in found_colors:
            if item['color'] not in seen:
                seen.add(item['color'])
                unique_colors.append(item)

        if len(unique_colors) >= 1:
            colors['primary'] = unique_colors[0]['color']

        if len(unique_colors) >= 2:
            colors['accent'] = unique_colors[1]['color']

        # Secondary should be WHITE or very light neutral
        # NOT the same as primary
        # We only override white if we found a genuinely
        # different light color
        light_colors = [
            c for c in unique_colors
            if is_light_color(c['color'])
            and c['color'] != colors['primary']  # ← must be different from primary
            and c['color'] != colors['accent']   # ← must be different from accent
        ]
        if light_colors:
            colors['secondary'] = light_colors[0]['color']

    return colors


def extract_features(soup) -> list:
    """
    Extract key features or services.
    Aggressively filters noise.
    """
    noise_keywords = [
        # Navigation
        'home', 'about', 'contact', 'login', 'signup',
        'sign in', 'sign up', 'menu', 'search', 'cart',
        'account', 'help', 'support', 'faq', 'blog',
        # Streaming / media noise
        'stream now', 'watch now', 'listen now',
        'play now', 'apple tv', 'apple music',
        'grand prix', 'season long',
        # Video player accessibility noise
        'captions', 'subtitles', 'descriptions',
        'selected', 'settings dialog', 'opens captions',
        'audio track', 'playback', 'full screen',
        # Generic noise
        'click here', 'read more', 'learn more',
        'find out', 'discover', 'cookie', 'privacy',
        'terms', 'policy',
    ]

    noise_first_words = [
        'a', 'an', 'the', 'watch', 'stream',
        'get', 'play', 'listen', 'download',
        'ok', 'yes', 'no', 'cancel',
    ]

    # Track nav/header li items — skip those
    nav_elements = soup.find_all(['nav', 'header'])
    nav_li_ids = set()
    for nav in nav_elements:
        for li in nav.find_all('li'):
            nav_li_ids.add(id(li))

    # Also skip li items inside video/media elements
    media_elements = soup.find_all([
        'video', 'figure',
        lambda tag: tag.name == 'div' and any(
            word in ' '.join(tag.get('class', [])).lower()
            for word in ['player', 'video', 'media']
        )
    ])
    media_li_ids = set()
    for media in media_elements:
        for li in media.find_all('li'):
            media_li_ids.add(id(li))

    features = []
    for li in soup.find_all('li'):
        # Skip nav and media items
        if id(li) in nav_li_ids:
            continue
        if id(li) in media_li_ids:
            continue

        text = li.get_text(strip=True)

        # Length check
        if not (20 < len(text) < 120):
            continue

        # Noise keyword check
        text_lower = text.lower()
        if any(kw in text_lower for kw in noise_keywords):
            continue

        # First word check
        first_word = text.split()[0].lower()
        if first_word in noise_first_words:
            continue

        # Must have at least 3 words
        if len(text.split()) < 3:
            continue

        features.append(text)
        if len(features) >= 5:
            break

    return features


# ═══════════════════════════════════════════════════════
# SECTION 3 — HTML PARSER
# Calls all extractors, returns structured brand data
# ═══════════════════════════════════════════════════════

def parse_html(html: str, url: str) -> dict:
    """
    Takes raw HTML string.
    Returns structured brand data dictionary.
    Calls every extractor function above.
    """
    soup   = BeautifulSoup(html, 'html.parser')
    domain = urlparse(url).netloc.replace('www.', '')

    business_name = extract_business_name(soup, domain)
    description   = extract_description(soup)
    tagline       = extract_tagline(soup)
    logo_url      = extract_logo(soup, url)
    colors        = extract_colors(soup, url, html)
    features      = extract_features(soup)

    return {
        "business_name": business_name,
        "description":   description,
        "tagline":       tagline,
        "logo_url":      logo_url,
        "colors":        colors,
        "features":      features,
        "domain":        domain,
        "url":           url,
        "scrape_failed": False
    }


# ═══════════════════════════════════════════════════════
# SECTION 4 — SCRAPING METHODS
# Two methods: fast (httpx) and powerful (Playwright)
# ═══════════════════════════════════════════════════════

async def _parse_html_off_loop(html: str, url: str) -> dict:
    """
    parse_html is CPU-bound (BeautifulSoup over the whole document) and can
    additionally make *blocking* network calls: when no colours are found
    inline it falls through to extract_colors_from_stylesheets, which uses
    urllib.request.urlopen (up to 2 stylesheets, 5s socket timeout each).

    Both call sites are inside async handlers, so running it inline stalled the
    whole event loop — every other in-flight request with it. Hand it to the
    default executor instead.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, parse_html, html, url)


async def scrape_with_httpx(url: str) -> dict:
    """
    Fast scraper using httpx.
    Uses maximum realistic headers to avoid bot detection.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "none",
        "Sec-Fetch-User":            "?1",
        "Cache-Control":             "max-age=0",
        "sec-ch-ua": (
            '"Chromium";v="122", '
            '"Not(A:Brand";v="24", '
            '"Google Chrome";v="122"'
        ),
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers=headers,
        http2=False,   # ← disable HTTP/2 for compatibility
    ) as client:
        response = await client.get(url)

        if response.status_code == 403:
            raise Exception("Site blocked our request (403 Forbidden)")
        if response.status_code == 429:
            raise Exception("Rate limited (429 Too Many Requests)")

        response.raise_for_status()
        html = response.text

    if len(html) < 2000:
        raise Exception(
            f"Too little HTML ({len(html)} chars) — JS-only or bot detection"
        )
    
    print(f"  📄 httpx got {len(html)} chars")
    return await _parse_html_off_loop(html, url)

async def scrape_with_playwright(url: str) -> dict:
    """
    Full browser scraper using Playwright.
    Runs in a separate thread to avoid Windows asyncio issues.
    Handles HTTP/2 protocol errors with fallback to HTTP/1.1
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def run_playwright_sync(url: str) -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Try with HTTP/2 first
            # If that fails we catch and retry with HTTP/1.1
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-http2',  # ← fixes ERR_HTTP2_PROTOCOL_ERROR
                ]
            )

            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                # Realistic browser extra headers
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept":          (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/avif,"
                        "image/webp,*/*;q=0.8"
                    ),
                    "sec-ch-ua": (
                        '"Chromium";v="122", '
                        '"Not(A:Brand";v="24", '
                        '"Google Chrome";v="122"'
                    ),
                    "sec-ch-ua-mobile":   "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
            )

            page = context.new_page()

            # Hide automation fingerprint
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3]
                });
            """)

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",  # less strict than networkidle
                    timeout=30000
                )
                # Wait a bit for JS to render content
                page.wait_for_timeout(3000)

            except Exception as e:
                error_msg = str(e)
                print(f"  ⚠️ First attempt failed: {error_msg[:80]}")

                # Retry with more relaxed settings
                print("  🔄 Retrying with relaxed wait conditions...")
                try:
                    page.goto(
                        url,
                        wait_until="load",  # even less strict
                        timeout=30000
                    )
                    page.wait_for_timeout(3000)
                except Exception as e2:
                    browser.close()
                    raise Exception(f"Both goto attempts failed: {str(e2)}")

            html = page.content()
            browser.close()
            return html

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            html = await loop.run_in_executor(
                pool,
                run_playwright_sync,
                url
            )

        if len(html) < 2000:
            raise Exception(
                f"Got too little content ({len(html)} chars)"
            )

        print(f"  📄 Playwright got {len(html)} chars of HTML")
        return await _parse_html_off_loop(html, url)

    except Exception as e:
        raise Exception(f"Playwright failed: {str(e)}")

def calculate_completeness_score(data: dict) -> int:
    """
    Scores scraped data from 0 to 100.
    Higher score = more complete data.

    Used to decide whether to upgrade from httpx to Playwright.
    If score is below 70, we try Playwright for better data.

    Scoring breakdown:
    - business_name (real, not just domain): 20 points
    - description (real content):            25 points
    - tagline (found):                       20 points
    - logo_url (found):                      15 points
    - colors (not all defaults):             10 points
    - features (at least one):               10 points
    Total possible:                         100 points
    """
    score = 0

    # Business name — is it real or just the domain?
    name = data.get('business_name', '')
    domain = data.get('domain', '')
    domain_name = domain.split('.')[0].title()
    if name and name != domain_name and len(name) > 2:
        score += 20
        print(f"  +20 business_name: '{name}'")
    else:
        print(f"  +0  business_name looks like domain: '{name}'")

    # Description — is it real content or our default text?
    description = data.get('description', '')
    default_desc = f"{name} - providing quality products and services."
    if (description
            and description != default_desc
            and description != "A business offering quality products and services."
            and len(description) > 50):
        score += 25
        print(f"  +25 description: real content found")
    else:
        print(f"  +0  description: default/empty")

    # Tagline — any real tagline found?
    tagline = data.get('tagline', '')
    default_tagline = f"Welcome to {name}"
    if tagline and tagline != default_tagline and len(tagline.split()) > 1:
        score += 20
        print(f"  +20 tagline: '{tagline[:50]}'")
    else:
        print(f"  +0  tagline: empty or default")

    # Logo URL — any logo found?
    logo_url = data.get('logo_url', '')
    if logo_url and logo_url.startswith('http'):
        score += 15
        print(f"  +15 logo_url: found")
    else:
        print(f"  +0  logo_url: not found")

    # Colors — are they real or all defaults?
    colors = data.get('colors', {})
    default_colors = ["#1a1a2e", "#ffffff", "#6c63ff"]
    real_colors = [
        c for c in colors.values()
        if c not in default_colors
    ]
    if real_colors:
        score += 10
        print(f"  +10 colors: real colors found {real_colors}")
    else:
        print(f"  +0  colors: all defaults")

    # Features — at least one real feature found?
    features = data.get('features', [])
    if features and len(features) > 0:
        score += 10
        print(f"  +10 features: {len(features)} found")
    else:
        print(f"  +0  features: none found")

    return score    

# ═══════════════════════════════════════════════════════
# SECTION 5 — MAIN FUNCTION
# This is the only function routers/scrape.py calls
# Everything above feeds into this one function
# ═══════════════════════════════════════════════════════

async def scrape_business_url(url: str) -> dict:
    """
    Main entry point for scraping.

    Smart two-pass strategy:
    1. Try httpx first (fast — 1-2 seconds)
    2. Check if result is COMPLETE
       - If complete → return immediately
       - If incomplete → upgrade to Playwright
    3. If httpx fails entirely → go straight to Playwright
    4. If both fail → return fallback

    This gives us:
    - Speed of httpx for simple sites
    - Quality of Playwright for complex sites
    - No unnecessary 10-second waits
    """
    url = clean_url(url)
    print(f"\n🔍 Scraping: {url}")
    print("─" * 50)

    httpx_result = None

    # ── PASS 1: Try httpx ─────────────────────────────
    try:
        httpx_result = await scrape_with_httpx(url)
        print(f"✅ httpx succeeded")

        # Check how complete the result is
        score = calculate_completeness_score(httpx_result)
        print(f"📊 Completeness score: {score}/100")

        if score >= 70:
            # Good enough — return immediately
            print(f"✅ Data complete enough — returning httpx result")
            return httpx_result
        else:
            # Got something but it's incomplete
            # Upgrade to Playwright for better data
            print(f"⚠️  Data incomplete (score: {score}) — upgrading to Playwright")

    except Exception as e:
        print(f"⚠️  httpx failed: {e}")
        print("🔄 Trying Playwright...")

    # ── PASS 2: Try Playwright ────────────────────────
    try:
        playwright_result = await scrape_with_playwright(url)
        playwright_score  = calculate_completeness_score(playwright_result)
        print(f"📊 Playwright completeness score: {playwright_score}/100")

        # If Playwright got better data than httpx, use it
        # If httpx already had something, compare scores
        if httpx_result is not None:
            httpx_score = calculate_completeness_score(httpx_result)
            if playwright_score > httpx_score:
                print(f"✅ Playwright got better data ({playwright_score} vs {httpx_score})")
                return playwright_result
            else:
                print(f"✅ httpx data was better — keeping it ({httpx_score} vs {playwright_score})")
                return httpx_result
        else:
            print(f"✅ Playwright scraped: {playwright_result['business_name']}")
            return playwright_result

    except Exception as e:
        print(f"⚠️  Playwright failed: {e}")

    # ── PASS 3: Use whatever httpx got (even if incomplete) ──
    if httpx_result is not None:
        print("📦 Using incomplete httpx result — better than nothing")
        return httpx_result

    # ── PASS 4: Total failure — return fallback ───────
    print(f"⚠️  Both scrapers failed — using fallback")
    return build_fallback_data(url)