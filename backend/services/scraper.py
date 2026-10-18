# services/scraper.py
# ONE job: visit a URL, extract brand information
# Complete file — all functions in correct order

import asyncio
import httpx
import re
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse


# ═══════════════════════════════════════════════════════
# SECTION 1 — HELPER FUNCTIONS
# Small utility functions used by everything below
# ═══════════════════════════════════════════════════════

# Redirect wrappers people copy from search results and social feeds: host suffix → the
# query parameters that carry the real destination. Scraping the wrapper reads an empty
# redirect page ("loaded but had almost no readable content").
_REDIRECT_PARAMS = {
    "google.": ("adurl", "url", "q"),
    "facebook.com": ("u",),
    "bing.com": ("u", "url"),
}
_TRACKING_PARAMS = {"gclid", "gbraid", "wbraid", "dclid", "fbclid", "msclkid", "yclid", "_ga", "srsltid"}


def _unwrap_redirect(url: str) -> str:
    for _ in range(3):  # a wrapper can wrap another
        p = urlparse(url)
        host = p.netloc.lower()
        keys = next((v for k, v in _REDIRECT_PARAMS.items() if k in host), None)
        if not keys:
            break
        qs = parse_qs(p.query)
        target = next((qs[k][0] for k in keys if qs.get(k, [""])[0].startswith(("http://", "https://"))), None)
        if not target:
            break
        url = target
    return url


def _strip_tracking(url: str) -> str:
    p = urlparse(url)
    if not p.query:
        return url
    kept = [(k, v) for k, vs in parse_qs(p.query, keep_blank_values=True).items() for v in vs
            if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith(("utm_", "gad_"))]
    return urlunparse(p._replace(query=urlencode(kept)))


def clean_url(url: str) -> str:
    """
    Make sure URL has https:// prefix, unwrap ad/search redirect links to the site they
    point at, and drop ad-tracking parameters.
    Handles: brand.example, www.brand.example, https://brand.example,
             https://www.google.com/aclk?...&adurl=https://brand.example/
    """
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return _strip_tracking(_unwrap_redirect(url))


def make_absolute(url: str, base_url: str) -> str:
    """
    Convert relative URLs to absolute URLs.
    /logo.png + https://brand.example → https://brand.example/logo.png
    //cdn.brand.example/logo.png → https://cdn.brand.example/logo.png
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
    some large brands use these intentionally.
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


def explain_failure(url: str, reason: str) -> str:
    """A message that matches what actually went wrong.

    This used to claim bot protection no matter the cause, and offered a
    manual-entry form that does not exist — so a plain DNS or connection
    failure was reported as blocking, and the suggested fix led nowhere.
    """
    domain = urlparse(url).netloc or url
    low = (reason or "").lower()

    if any(k in low for k in ("connection_timed_out", "connecttimeout", "timed out", "timeout")):
        return (
            f"We couldn't reach {domain} — it didn't respond in time. "
            "Check the address is right, and try the full URL including www."
        )
    if any(k in low for k in ("name_not_resolved", "getaddrinfo", "nodename", "dns")):
        return (
            f"{domain} doesn't seem to exist. Check the spelling, "
            "or paste the full address from your browser."
        )
    if "403" in low or "blocked" in low or "429" in low or "rate limited" in low:
        return (
            f"{domain} blocked our request. Some sites refuse automated visits — "
            "try a different page on the same site, such as an about or product page."
        )
    if "too little" in low:
        return (
            f"{domain} loaded but showed us almost no content. Many large sites block "
            "automated visitors, and some only build their pages in the browser. "
            "Try a specific page on the site (such as an about or product page), or a different website."
        )
    return (
        f"We couldn't read {domain} automatically. "
        "Try the full URL from your browser's address bar, or a different page on the site."
    )


def build_fallback_data(url: str, reason: str = "") -> dict:
    """
    When every scraping attempt fails, return sensible defaults.
    The app NEVER crashes — always returns something usable.
    `scrape_failed` tells the caller this is placeholder data.
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
        "images":        [],
        "site_intent":   "unknown",
        "domain":        domain,
        "url":           url,
        "scrape_failed": True,
        "scrape_message": explain_failure(url, reason),
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


# ═══════════════════════════════════════════════════════
# CONTENT IMAGES
# The photos a site already uses to sell itself are far
# better ad footage than screenshots of its own layout.
# ═══════════════════════════════════════════════════════

# Anything whose URL smells like furniture rather than content.
_IMAGE_NOISE = (
    "logo", "icon", "favicon", "sprite", "avatar", "badge", "button",
    "arrow", "chevron", "bullet", "divider", "placeholder", "spacer",
    "pixel", "tracking", "analytics", "1x1", "blank", "loading",
    "spinner", "payment", "visa", "mastercard", "paypal", "apple-pay",
    "flag", "social", "facebook", "twitter", "instagram", "linkedin",
    "youtube", "tiktok", "whatsapp", "star", "rating",
)

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")


def _looks_like_content_image(url: str) -> bool:
    low = url.lower()
    if low.startswith("data:"):
        return False
    if any(n in low for n in _IMAGE_NOISE):
        return False
    if ".svg" in low or ".gif" in low:
        return False
    # Query strings are common on CDNs, so check the path only.
    path = low.split("?")[0]
    return path.endswith(_IMAGE_EXTS) or "image" in low or "/photo" in low


def _biggest_from_srcset(srcset: str) -> str:
    """Pick the widest candidate out of a srcset attribute."""
    best, best_w = "", -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        width = -1
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = -1
        if width > best_w:
            best, best_w = url, width
    return best


def extract_content_images(soup, base_url: str, limit: int = 12) -> list:
    """
    Collect the page's own photography, best first.

    Ranked: social preview images (hand-picked by the site owner, always
    representative), then large <img> elements, then anything else plausible.
    Screenshots of a website make dull footage and often look identical to each
    other once you scroll; real product and lifestyle shots do not.
    """
    found = []   # (priority, url)
    seen = set()

    def add(url: str, priority: int):
        if not url:
            return
        url = make_absolute(url.strip(), base_url)
        if not url.startswith(("http://", "https://")):
            return
        key = url.split("?")[0]
        if key in seen or not _looks_like_content_image(url):
            return
        seen.add(key)
        found.append((priority, url))

    # 1. Social preview images — the owner chose these to represent the page.
    for prop in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
        for tag in soup.find_all("meta", attrs={"property": prop}) + \
                   soup.find_all("meta", attrs={"name": prop}):
            add(tag.get("content", ""), 10)

    # 2. <img>, preferring the widest srcset candidate and honouring width hints.
    for img in soup.find_all("img"):
        src = _biggest_from_srcset(img.get("srcset", "")) or \
              img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        if not src:
            continue

        priority = 5
        try:
            w = int(str(img.get("width", "0")).replace("px", "") or 0)
            h = int(str(img.get("height", "0")).replace("px", "") or 0)
            if w and w < 200:      # thumbnails and icons
                continue
            if h and h < 150:
                continue
            if w >= 800:
                priority = 8
            elif w >= 400:
                priority = 6
        except ValueError:
            pass

        add(src, priority)

    # 3. <picture><source srcset>
    for source in soup.find_all("source"):
        add(_biggest_from_srcset(source.get("srcset", "")), 4)

    # 4. Inline background-image, which is how a lot of heroes are built.
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if "background-image" in style:
            m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", style)
            if m:
                add(m.group(1), 7)

    found.sort(key=lambda x: -x[0])
    urls = [u for _, u in found[:limit]]
    print(f"  🖼️  Found {len(urls)} content image(s)")
    return urls


# Keyword cues per intent. Matched against the rendered page text, lowercased.
_SAAS_CUES = (
    "free trial", "start free", "start for free", "book a demo", "request a demo",
    "get a demo", "sign up free", "pricing", "per month", "/mo", "dashboard",
    "workflow", "integrations", "api key", "documentation", "open source",
    "deploy", "sdk", "webhook",
)
_COMMERCE_CUES = (
    "add to cart", "add to bag", "shopping cart", "checkout", "free shipping",
    "in stock", "out of stock", "add to basket", "shop now", "buy now",
    "product details", "size guide", "add to wishlist", "order now",
)


def detect_site_intent(html: str) -> str:
    """
    "saas", "commerce", or "unknown".

    Used to bias scene selection: a dev-tool's product is its UI, a store's is
    its products. "unknown" is a safe default -- selection then just prefers
    photographic, visually consistent footage, which suits most sites.
    """
    t = (html or "").lower()
    saas     = sum(1 for c in _SAAS_CUES if c in t)
    commerce = sum(1 for c in _COMMERCE_CUES if c in t)

    if saas >= 3 and saas > commerce:
        return "saas"
    if commerce >= 2 and commerce >= saas:
        return "commerce"
    return "unknown"


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
    images        = extract_content_images(soup, url)
    site_intent   = detect_site_intent(html)
    print(f"  🧭 Site intent: {site_intent}")

    return {
        "business_name": business_name,
        "description":   description,
        "tagline":       tagline,
        "logo_url":      logo_url,
        "colors":        colors,
        "features":      features,
        "images":        images,
        "site_intent":   site_intent,
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
    result = await _parse_html_off_loop(html, url)
    result["_html"] = html   # for the product-page crawl; popped before return
    return result

# ─── Page render helper (used by the visual-sourcing product-page crawl) ─────
_CRAWL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _render_html_sync(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        try:
            page = browser.new_context(
                viewport={"width": 1280, "height": 900}, user_agent=_CRAWL_UA
            ).new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)
            return page.content()
        finally:
            browser.close()


async def _render_html(url: str) -> str:
    """Render a sub-page to HTML, off the event loop (Windows-safe)."""
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _render_html_sync, url)


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
        result = await _parse_html_off_loop(html, url)
        # Stash the homepage HTML so the product-page crawl can run later, at
        # the single success point in scrape_business_url — enriching here would
        # miss the httpx path, and enriching in both would crawl twice.
        result["_html"] = html
        return result

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

# httpx errors that mean "this host is not answering". Playwright cannot do
# better with any of them, so there is no point spending two 30s page loads to
# confirm it — the useful next move is the www. host.
UNREACHABLE_MARKERS = (
    "getaddrinfo",
    "nodename nor servname",
    "name or service not known",
    "connecttimeout",
    "connecterror",
    "connection refused",
    "connection timed out",
    "all connection attempts failed",
    "ssl",
)


def is_unreachable(error: str) -> bool:
    low = (error or "").lower()
    return any(m in low for m in UNREACHABLE_MARKERS)


def www_variant(url: str) -> str:
    """`https://brand.example` -> `https://www.brand.example`, or "" if not applicable.

    Plenty of sites only answer on the www host: the apex either has no A
    record or refuses the connection. Users type the bare domain, so without
    this a perfectly reachable site looks completely dead.
    """
    parsed = urlparse(url)
    host = parsed.netloc
    if not host or host.startswith("www.") or host.replace(".", "").isdigit():
        return ""
    # Only worth trying for a bare apex: something.tld
    if host.count(".") != 1:
        return ""
    return parsed._replace(netloc=f"www.{host}").geturl()


async def _scrape_one(url: str) -> dict:
    """
    One host, the two-pass strategy.

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
    print(f"\n🔍 Scraping: {url}")
    print("─" * 50)

    httpx_result = None
    httpx_error = ""
    playwright_error = ""

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
        httpx_error = f"{type(e).__name__}: {e}"
        print(f"⚠️  httpx failed: {httpx_error}")

        if is_unreachable(httpx_error):
            # Nothing to gain from a browser against a host that will not
            # answer — raise now so the caller can try the www. variant.
            raise Exception(httpx_error)

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
        playwright_error = str(e)
        print(f"⚠️  Playwright failed: {playwright_error}")

    # ── PASS 3: Use whatever httpx got (even if incomplete) ──
    if httpx_result is not None:
        print("📦 Using incomplete httpx result — better than nothing")
        return httpx_result

    # ── PASS 4: Total failure ─────────────────────────
    # Carry the underlying cause up: the caller turns it into the message the
    # user sees, and "ERR_NAME_NOT_RESOLVED" vs "403" lead to different advice.
    raise Exception(playwright_error or httpx_error or f"Could not reach {url}")


async def _finalize_result(result: dict, url: str) -> dict:
    """
    Source the ad's candidate images, then drop internal keys.

    The whole visual-sourcing flow (homepage + product-page crawl, ownership
    ranking) runs here — the single success point — so it fires whichever
    scraper produced the result, exactly once. `_html` is popped so it never
    reaches the API response.
    """
    from services import visual_sourcing as vs

    html = result.pop("_html", "")
    if html and not result.get("scrape_failed"):
        try:
            ordered = await vs.source_images_for_ad(
                url,
                html,
                result.get("business_name", ""),
                result.get("site_intent", "unknown"),
                render_page=_render_html,
            )
            if ordered:
                result["images"] = ordered[:16]
        except Exception as e:
            print(f"  ⚠️  visual sourcing skipped: {str(e)[:80]}")
    return result


async def scrape_business_url(url: str) -> dict:
    """
    Main entry point for scraping.

    Tries the URL as given, then the www. host if the apex was unreachable.
    Only falls back to placeholder data when every candidate fails, so the
    caller can tell "site is unreadable" from "site needs www".
    """
    url = clean_url(url)
    candidates = [url]

    alt = www_variant(url)
    if alt:
        candidates.append(alt)

    last_error = ""
    for i, candidate in enumerate(candidates):
        try:
            return await _finalize_result(await _scrape_one(candidate), candidate)
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {candidate} failed: {last_error[:120]}")
            if i + 1 < len(candidates):
                print(f"🔄 Retrying on {candidates[i + 1]}")

    print("⚠️  Every candidate failed — using fallback")
    return build_fallback_data(url, last_error)