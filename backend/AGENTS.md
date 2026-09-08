# AdCraft backend — agent notes

Root context, glossary and product ground truth live in [`../CLAUDE.md`](../CLAUDE.md).
Read that first.

**Stack:** FastAPI · Python 3.11 · Groq (Llama 3.3 70B) · Kokoro ONNX TTS ·
Playwright · FFmpeg · Pillow.

---

## Running it

```bash
cd backend
./venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000
```

The venv already exists. On Windows call `venv/Scripts/python.exe` directly —
don't try to `activate` it from the Bash tool.

**External binaries that must be on PATH:** `ffmpeg` (all rendering and audio),
and Playwright's Chromium (`playwright install chromium`). Neither is a pip
dependency; if rendering fails with a confusing error, check these first.

**`requirements.txt` is UTF-16-LE with a BOM.** `cat` and plain `pip install -r`
both misbehave. Read it with:

```bash
python -c "print(open('requirements.txt',encoding='utf-16').read())"
```

Docs: `http://localhost:8000/docs` (FastAPI auto-generated).

---

## Pipeline

`POST /api/generate/video` runs the whole thing:

1. **Scrape** (`services/scraper.py`) — two-pass. Fast `httpx` fetch first; score
   the result 0–100 for completeness; if it scores **< 70**, escalate to
   Playwright and keep whichever pass scored higher. Total failure returns
   `build_fallback_data()` with `scrape_failed: true` rather than raising, so
   the frontend can show a manual-entry path.
2. **Script** (`services/script_generator.py`) — Groq, `llama-3.3-70b-versatile`.
   Returns a *structured* script; every field maps to something the renderer
   uses. The Groq client is synchronous.
3. **Narration** (`services/tts.py`) — Kokoro ONNX, local, no API cost. Model
   weights are git-lfs files in `models/`. Loaded once as a module singleton.
4. **Music** (`services/music.py`) — picks an mp3 from `music/` by **filename
   keyword match** against the style the LLM chose, loops/trims to length, fades
   both ends, drops to ~15% volume.
5. **Render** (`services/video_assembler.py`) — Playwright screenshots the site
   (3 viewports) → per-image clips → concat → composite overlay, headline,
   subtext, CTA and logo → mux audio. All FFmpeg.

Output lands in `output/<render_id>_ad.mp4`, served at
`/api/output/<filename>`. `render_id` is `uuid4()[:8]`.

`output/` and `temp/` are gitignored. Temp files are cleaned per render.

---

## Windows specifics

`server.py` sets `WindowsProactorEventLoopPolicy` at import time — **before**
anything else runs. FFmpeg subprocesses need it. Don't reorder those lines.

Playwright is invoked through a `ThreadPoolExecutor` (in both `scraper.py` and
`video_assembler.py`) rather than directly, to dodge Windows asyncio breakage.
Keep that wrapper if you touch either call site.

---

## Known open issues

We know about all of these. Don't silently "discover" and fix them — ask first,
and prefer one focused change over a sweep.

1. **`POST /api/scrape/debug` is a live SSRF-shaped hole.** It fetches any
   user-supplied URL server-side and echoes headers/HTML back, unauthenticated.
   Its own comment says delete before production. Still routed.
2. **Blocking I/O in an async handler.** `extract_colors_from_stylesheets` uses
   synchronous `urllib.request.urlopen` (5s timeout × 2 stylesheets) and is
   called from `async def scrape_with_httpx`. It stalls the whole event loop.
   Fix by moving to `httpx.AsyncClient` or a thread pool.
3. **Unvalidated request bodies.** `/api/generate/from-url` and
   `/api/generate/video` take a bare `dict`, so `ad_style` and `duration` are
   never checked — unlike `/api/generate/script`, which validates both. Bad
   values propagate deep before failing.
4. **`calm` music is unreachable.** `STYLE_KEYWORDS` maps `calm → "calm"`, but no
   file in `music/` contains that substring, so it always falls back. Either
   rename `freemusicforvideo-soft-background-music-*.mp3` to include `calm`, or
   drop `calm` from the map.
5. **Dead code.** `scrape_with_httpx` has an unreachable `return parse_html(...)`
   after it already returns.
6. **Dead config.** `config/settings.py` declares `ANTHROPIC_API_KEY` and
   `CREATOMATE_API_KEY`; nothing reads either. The LLM is Groq.
7. **Duplicate output route.** `server.py` mounts `StaticFiles` at
   `/api/output`, and `routers/generate.py` also defines
   `GET /api/output/{filename}`. The router wins. Harmless, but redundant.

---

## The main integration gap

The frontend video editor lets Users rewrite the headline, subtext, CTA,
voiceover, colours and contact banner — and **none of it re-renders the MP4**.
Edits persist in the browser and preview live; Download still returns the
original render.

Closing this is the next significant piece of work. It needs an endpoint that
accepts an existing `render_id` plus an edited script and re-runs assembly
without re-scraping.

The FAQ at `frontend/app/content/faq.ts` currently tells Users this plainly.
**When you fix it, update that answer in the same change** — leaving it stale
would make us honest in the wrong direction.

---

## Conventions

- Services are single-purpose modules with no shared mutable state beyond the
  Kokoro singleton. Keep it that way.
- The pipeline prints progress to stdout with emoji prefixes. It's the primary
  debugging surface — keep new steps consistent with it.
- Failures degrade rather than crash wherever a User is waiting: scraping falls
  back to defaults, music falls back across styles, audio failure still renders
  a silent video. Preserve that when adding steps.
- **Don't commit or push unless we ask.**
