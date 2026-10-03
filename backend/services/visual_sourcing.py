"""
Visual sourcing — deciding WHERE an ad's scenes come from, for any website.

The old pipeline was "scrape homepage <img>, else screenshot", and each new
kind of site broke it differently (a store worked; a dev-tool brought in
founder faces and badges; a customer-showcase like stripe.com filled the ad
with its clients). Patching per site does not scale.

This module separates the two concerns that were tangled together:

  * WHERE visuals come from  — "sources": the homepage, the site's own
    product/feature pages (found from its sitemap and nav, never a hardcoded
    path list), and (as a universal fallback) screenshots.
  * WHAT makes a visual good — a "candidate" carries provenance (which page,
    the section heading it sat under, its alt text) so one universal scorer can
    judge it the same way on every site.

The pixel-level judgement (face / UI / logo, tone, coherence) stays in
video_assembler, which runs after these URLs are downloaded. This module is the
text-and-structure half: it decides which URLs are worth downloading, and in
what order, using only signals the site provides about itself.

Ownership is the signal that generalises the two old hacks. An image is a
third party's (a customer, a partner logo) when the section it lives under reads
like a case study — "Hertz unifies commerce with Stripe", "Trusted by…",
"Our customers" — rather than the company describing its own product. That is
discovered from each site's own headings; it needs no list of brand names.
"""
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

_CRAWL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


# ─── Ownership / section semantics ───────────────────────────────────────────
# A section that is about the company's OWN product — up-rank.
_PRODUCT_SECTION_CUES = (
    "product", "feature", "how it works", "how it works", "platform",
    "capabilit", "built for", "what you can", "dashboard", "workflow",
    "everything you need", "one place", "tools", "get started", "build",
)
# A section that showcases OTHER companies — down-rank hard.
_CUSTOMER_SECTION_CUES = (
    "customer", "trusted by", "trusted the world", "case stud", "testimonial",
    "success stor", "our clients", "who use", "companies", "brands", "logos",
    "loved by", "powering", "join thousands", "join millions",
)
# Case-study headings read "{external company} {verb} with/on/using {business}".
_CASE_STUDY_VERBS = (
    "with", "using", "on", "powered by", "chose", "switched to", "trusts",
    "builds on", "runs on", "grows", "scales", "unifies", "improves",
)
# Filename / alt cues that mark third-party or decorative material.
_THIRD_PARTY_URL_CUES = (
    "customer", "testimonial", "case-study", "casestudy", "-logo", "logo-",
    "/logos/", "accordion", "partner", "press", "award", "badge", "review",
)


def _nearest_heading(img) -> str:
    """The heading text that best describes the section this image sits in."""
    prev = img.find_previous(["h1", "h2", "h3", "h4"])
    if prev:
        txt = prev.get_text(" ", strip=True)
        if txt:
            return txt[:120]
    # Fall back to an ancestor's aria-label / section label.
    node = img
    for _ in range(6):
        node = getattr(node, "parent", None)
        if node is None:
            break
        label = node.get("aria-label") if hasattr(node, "get") else None
        if label:
            return label[:120]
    return ""


def classify_ownership(url: str, alt: str, heading: str, business: str) -> str:
    """
    "own" | "third_party" | "neutral" — who the image is really about.

    Only site-provided text is used: the section heading, the alt text, and the
    filename. No list of brand names — a case study is recognised by its shape
    ("… with {business}"), not by knowing the customer.
    """
    h = (heading or "").lower()
    a = (alt or "").lower()
    u = (url or "").lower()
    biz = (business or "").strip().lower()

    # A heading that credits the business for someone else's achievement:
    # "<external company> <verb> ... with <business>". The telltale is the
    # business name appearing *after* an action, not as the subject.
    if biz and len(biz) > 2:
        for verb in _CASE_STUDY_VERBS:
            if f"{verb} {biz}" in h or h.endswith(biz) and verb in h:
                # Make sure the business is not simply the subject of the hero.
                if not h.startswith(biz):
                    return "third_party"

    if any(c in h for c in _CUSTOMER_SECTION_CUES):
        return "third_party"
    if any(c in u for c in _THIRD_PARTY_URL_CUES):
        return "third_party"
    if a.startswith("logo") or " logo" in a:
        return "third_party"

    if any(c in h for c in _PRODUCT_SECTION_CUES):
        return "own"
    return "neutral"


# ─── Candidate extraction (homepage or any page), provenance-aware ───────────
def _biggest_srcset(srcset: str) -> str:
    best, best_w = "", -1
    for part in (srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        cand = bits[0]
        w = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                w = 0
        if w >= best_w:
            best, best_w = cand, w
    return best


def extract_candidates(soup, page_url: str, business: str, source: str) -> list:
    """
    Every plausible content image on a page, each tagged with where it came
    from and who it is about. Ordering/scoring happens later.
    """
    out, seen = [], set()

    def add(url: str, priority: int, alt: str, heading: str):
        if not url:
            return
        full = urljoin(page_url, url.strip())
        if not full.startswith(("http://", "https://")):
            return
        key = full.split("?")[0]
        if key in seen:
            return
        seen.add(key)
        # SVGs are vector art — logos, icons, flags, diagrams — almost never a
        # product shot or photo. Keep them only as a last resort so raster
        # footage always leads.
        if key.lower().endswith(".svg"):
            priority = min(priority, 1)
        own = classify_ownership(full, alt, heading, business)
        out.append({
            "url": full,
            "priority": priority,
            "alt": alt or "",
            "section": heading or "",
            "ownership": own,
            "source": source,
        })

    # Social preview — the owner's chosen representative image.
    for prop in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
        for tag in soup.find_all("meta", attrs={"property": prop}) + \
                   soup.find_all("meta", attrs={"name": prop}):
            add(tag.get("content", ""), 10, "", "")

    for img in soup.find_all("img"):
        src = _biggest_srcset(img.get("srcset", "")) or img.get("src") or \
            img.get("data-src") or img.get("data-lazy-src") or ""
        if not src:
            continue
        priority = 5
        try:
            w = int(str(img.get("width", "0")).replace("px", "") or 0)
            h = int(str(img.get("height", "0")).replace("px", "") or 0)
            if (w and w < 200) or (h and h < 150):
                continue
            if w >= 800:
                priority = 8
            elif w >= 400:
                priority = 6
        except ValueError:
            pass
        add(src, priority, img.get("alt", ""), _nearest_heading(img))

    for source_tag in soup.find_all("source"):
        add(_biggest_srcset(source_tag.get("srcset", "")), 4, "", "")

    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if "background-image" in style:
            m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", style)
            if m:
                add(m.group(1), 7, "", _nearest_heading(el))

    return out


# ─── Ordering ────────────────────────────────────────────────────────────────
# A product page is where the real product UI lives, so it outweighs a homepage
# "own" tag — that tag only means the image sits under a product-ish heading,
# which a decorative background can do too. Telling a product shot from a
# background is a pixel call, made later in assembly; here we just make sure
# product pages lead and third-party/customer material sinks to the bottom.
_OWNERSHIP_WEIGHT = {"own": 12, "neutral": 0, "third_party": -60}
_SOURCE_WEIGHT = {"product-page": 25, "homepage": 0, "screenshot": -5}


def order_candidates(cands: list) -> list:
    """
    Rank candidates best-first: the company's own product imagery, from its
    product pages, ahead of homepage brand art, with customer/partner material
    pushed to the very back (used only if nothing else fills the ad).
    """
    def score(c):
        return (
            _OWNERSHIP_WEIGHT.get(c["ownership"], 0)
            + _SOURCE_WEIGHT.get(c["source"], 0)
            + c["priority"]
        )

    return sorted(cands, key=score, reverse=True)


def summarise(cands: list) -> str:
    own = sum(1 for c in cands if c["ownership"] == "own")
    tp = sum(1 for c in cands if c["ownership"] == "third_party")
    return f"{len(cands)} candidate(s): {own} own-product, {tp} third-party/customer"


# ─── Internal-page discovery (sitemap + nav), no hardcoded paths ─────────────
_PAGE_PRODUCT_CUES = (
    "product", "feature", "platform", "solution", "payment", "billing",
    "checkout", "invoic", "subscription", "capabilit", "how-it-works",
    "use-case", "tour", "overview",
)
_PAGE_BLOCK_CUES = (
    "pricing", "customer", "about", "blog", "/doc", "career", "legal",
    "contact", "login", "sign", "register", "job", "news", "press", "partner",
    "support", "help", "security", "privacy", "term", "guide", "resource",
    "event", "community", "changelog", "status", "cookie", "developer",
    "compan", "startup", "download", "/in/", "gallery", "story", "stories",
)


def _page_score(path: str, text: str = "") -> int:
    p = path.lower()
    if any(b in p for b in _PAGE_BLOCK_CUES):
        return -100
    score = sum(2 for c in _PAGE_PRODUCT_CUES if c in p)
    score += sum(1 for c in _PAGE_PRODUCT_CUES if c in (text or "").lower())
    # Prefer shallow pages; a top-level /payments beats /a/b/c/payments.
    if p.strip("/"):
        score -= p.strip("/").count("/")
    return score


def discover_nav_links(soup, base_url: str) -> dict:
    """Same-domain links whose path or link text reads like a product page."""
    host = urlparse(base_url).netloc.replace("www.", "")
    found = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"].strip())
        pu = urlparse(full)
        if pu.netloc.replace("www.", "") != host:
            continue
        path = pu.path
        if not path.strip("/"):
            continue
        s = _page_score(path, a.get_text(" ", strip=True))
        if s > 0:
            clean = f"{pu.scheme}://{pu.netloc}{path.rstrip('/')}"
            found[clean] = max(found.get(clean, 0), s)
    return found


async def discover_sitemap_links(base_url: str) -> dict:
    """
    Product-ish pages from the site's own sitemap(s). This is what makes
    discovery general: a mega-menu (Stripe) hides its nav links from the static
    DOM, but almost every site publishes a sitemap that lists every page.
    """
    p = urlparse(base_url)
    root = f"{p.scheme}://{p.netloc}"
    found = {}
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=12,
            headers={"User-Agent": _CRAWL_UA},
        ) as c:
            # robots.txt often points at the real sitemap; fall back to the
            # conventional location.
            sitemaps = []
            try:
                rob = await c.get(f"{root}/robots.txt")
                sitemaps = re.findall(r"(?i)sitemap:\s*(\S+)", rob.text)
            except Exception:
                pass
            sitemaps.append(f"{root}/sitemap.xml")

            locs = []
            for sm in sitemaps[:3]:
                try:
                    r = await c.get(sm)
                    if r.status_code >= 400:
                        continue
                    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
                    # A sitemap index points at more sitemaps.
                    if urls and urls[0].endswith(".xml"):
                        for child in urls[:3]:
                            try:
                                rc = await c.get(child)
                                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", rc.text)
                            except Exception:
                                pass
                    else:
                        locs += urls
                except Exception:
                    continue
                if locs:
                    break

            for u in locs:
                pu = urlparse(u)
                if pu.netloc.replace("www.", "") != p.netloc.replace("www.", ""):
                    continue
                s = _page_score(pu.path)
                if s > 0:
                    found[f"{pu.scheme}://{pu.netloc}{pu.path.rstrip('/')}"] = s
    except Exception:
        pass
    return found


async def discover_product_pages(soup, base_url: str, limit: int = 2) -> list:
    """
    The site's own product/feature pages, best first — nav first (cheap), then
    the sitemap when the nav yields too few (mega-menu sites).
    """
    scored = discover_nav_links(soup, base_url)
    if len([u for u, s in scored.items() if s > 0]) < limit:
        for u, s in (await discover_sitemap_links(base_url)).items():
            scored[u] = max(scored.get(u, 0), s)
    ranked = sorted((u for u in scored if scored[u] > 0), key=lambda u: -scored[u])
    # Never re-crawl the homepage itself.
    base_path = urlparse(base_url).path.rstrip("/")
    ranked = [u for u in ranked if urlparse(u).path.rstrip("/") != base_path]
    return ranked[:limit]


# ─── Top-level: the ordered image URLs an ad should be built from ────────────
async def source_images_for_ad(
    url: str, html: str, business: str, intent: str, render_page=None
) -> list:
    """
    Gather and rank candidate image URLs for the ad, best (own product) first.

    Homepage always; the site's own product pages too when it is a dev-tool /
    SaaS, whose product UI reliably lives on sub-pages rather than the
    marketing homepage. `render_page(url) -> html` renders a sub-page (SaaS
    product pages are usually client-rendered); omit it to stay on the homepage.
    """
    soup = BeautifulSoup(html, "html.parser")
    cands = extract_candidates(soup, url, business, "homepage")
    print(f"  🔎 Homepage: {summarise(cands)}")

    if render_page and intent == "saas":
        pages = await discover_product_pages(soup, url, limit=2)
        if pages:
            print(f"  🧭 Product pages: {[urlparse(p).path for p in pages]}")
        for page in pages:
            try:
                phtml = await render_page(page)
                pc = extract_candidates(
                    BeautifulSoup(phtml, "html.parser"), page, business, "product-page"
                )
                print(f"  🧩 {urlparse(page).path}: {summarise(pc)}")
                cands.extend(pc)
            except Exception as e:
                print(f"  ⚠️  {urlparse(page).path}: {str(e)[:50]}")

    ordered = order_candidates(cands)
    # De-dup across sources, keep best order.
    seen, out = set(), []
    for c in ordered:
        k = c["url"].split("?")[0]
        if k not in seen:
            seen.add(k)
            out.append(c["url"])
    return out
