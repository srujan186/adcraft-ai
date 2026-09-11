# AdCraft backend — agent notes

Root context, glossary and product ground truth live in [`../CLAUDE.md`](../CLAUDE.md).
Read that first.

**Stack:** FastAPI · Python 3.11 · Groq (GPT-OSS 120B) · Kokoro ONNX TTS ·
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
2. **Script** (`services/script_generator.py`) — Groq, `openai/gpt-oss-120b`.
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

### Fixed (2026-09-11)

The seven issues previously listed here are done. Kept as a record of what
changed and why, since some of the fixes are load-bearing:

1. **`POST /api/scrape/debug` deleted.** Unauthenticated SSRF read primitive.
   Nothing called it — `frontend/lib/api.ts` only uses `/api/scrape`,
   `/api/generate/video`, `/api/health` and `/api/output/{filename}`.
2. **Blocking I/O moved off the event loop.** `parse_html` now runs via
   `_parse_html_off_loop` (`services/scraper.py`) at *both* call sites — the
   Playwright path had the same problem, which the old note missed, because
   only the browser work was in the executor, not the parsing. The stylesheet
   fetch is also now gated to `http`/`https`: `urllib.request.urlopen` supports
   `file://`, so a page could otherwise link a stylesheet at `file:///...`.
3. **Request bodies validated.** `models/generate.py` defines `AdStyle` and
   `Duration` as `Literal` types plus a `VideoRequest` model; both generate
   routes use it instead of a bare `dict`. The hand-written `if` checks in
   `/generate/script` were removed so there is one source of truth.
   `server.py` also flattens FastAPI's 422 body — the default puts a *list of
   objects* in `detail`, every other error here puts a string, and the frontend
   does `throw new Error(json.detail)`.
4. **`calm` music reachable.** `STYLE_KEYWORDS["calm"]` maps to `"soft"`, which
   matches `freemusicforvideo-soft-background-music-*.mp3`. All five styles now
   resolve to five distinct files. The frontend's music ids in
   `app/result/VideoEditor.tsx` were reconciled to match these five.
5. **Dead code removed** from `scrape_with_httpx`.
6. **`config/` deleted.** Nothing imported it — all eight settings were dead,
   not just the two API keys. Real config is read via `os.getenv` in
   `server.py` (`ALLOWED_ORIGINS`), `script_generator.py` (`GROQ_API_KEY`) and
   `pexels.py` (`PEXELS_API_KEY`).
7. **Model swapped — `llama-3.3-70b-versatile` was retired by Groq** (404
   `model_not_found`). Replaced with `openai/gpt-oss-120b`, chosen by
   benchmarking every candidate the key can reach against the real
   `build_prompt()`. Two settings had to move with it: `max_tokens` 1200 → 4000
   (gpt-oss emits reasoning tokens *before* the answer and they count against
   the budget — at 1200 the JSON came back truncated or empty) and
   `response_format={"type": "json_object"}`. The four User-facing claims
   naming the old model were updated in the same change.
8. **Duplicate `/api/output` route resolved.** The `StaticFiles` mount was
   removed; `include_router` ran first so the mount was already dead. This was
   **not** harmless: `StaticFiles` was doing the path-traversal check, and the
   handler that shadowed it did none. `..\server.py` reached the handler
   (Starlette's path param matches backslashes) and `os.path.join` resolved it
   to the real `backend/server.py`. The handler now does basename + `.mp4` +
   realpath containment.

### Open — blocking, not yet fixed

1. **Kokoro weights are git-lfs pointers, not weights.** `models/*.onnx` and
   `voices-v1.0.bin` are 133 bytes each and contain
   `version https://git-lfs.github.com/spec/v1`. Kokoro fails with
   `INVALID_PROTOBUF`, the audio block swallows it, and the render returns
   `"status": "done"` with **no audio stream at all** (verified with ffprobe).
   Every ad produced right now is silent and reported as a success. Run
   `git lfs pull`, and make Docker builds materialise LFS before `COPY . .`.
2. **Fonts are Windows-only.** `services/video_assembler.py` looks only in
   `C:/Windows/Fonts/`. On Linux it falls back to `ImageFont.load_default()`,
   a ~11px bitmap font that ignores the requested size — a 64px headline
   renders illegibly. The Dockerfile installs no font packages.
3. **Emoji prints crash on a non-UTF-8 stdout.** The pipeline's progress prints
   raise `UnicodeEncodeError` when stdout is cp1252 (Windows, redirected to a
   file), turning a clean 400 into a broken response. Run with
   `PYTHONIOENCODING=utf-8`, or reconfigure stdout in `server.py`.

A fuller ranked backlog (sync Groq call on the event loop, `mix_audio`
reporting success on failure, no temp cleanup on error paths, prompt injection
via scraped page content, 8 sequential ffmpeg passes) is in the audit plan.

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
