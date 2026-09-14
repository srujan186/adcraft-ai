# AdCraft backend — agent notes

Root context, glossary and product ground truth live in [`../CLAUDE.md`](../CLAUDE.md).
Read that first.

**Stack:** FastAPI · Python 3.11 · Groq (GPT-OSS 120B) · Kokoro ONNX TTS ·
Playwright · FFmpeg · Pillow.

---

## Running it

**`pkill -f "uvicorn server:app"` does not kill the server on Windows.** The old
process keeps the port, the new one fails to bind with `[Errno 10048]` and
exits, and you spend the next twenty minutes testing stale code. Kill by port:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```


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

1. **Scrape** (`services/scraper.py`) — tries the URL as given, then the
   `www.` host if the apex was unreachable (`nike.in` refuses connections;
   `www.nike.in` answers, and users type the bare domain). A connection-level
   httpx failure skips Playwright for that host — a browser cannot reach a host
   that is not answering, and trying cost two 30s page loads. A typo'd domain
   now fails in ~1s instead of 60s+. `explain_failure()` turns the underlying
   error into advice that matches the cause: DNS vs timeout vs 403 vs empty
   page. Per host it is two-pass. Fast `httpx` fetch first; score
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
5. **Render** (`services/video_assembler.py`) — `TARGET_SCENES` (6) shots →
   per-image clips → concat → composite overlay, headline, subtext, CTA and
   logo → mux audio. All FFmpeg.

   **Scene sources, in order:** the page's own photos
   (`extract_content_images`, returned as `images` on the scrape result), then
   screenshots to top up. A site's hero and product shots are better ad footage
   than pictures of its own layout, and they differ from each other — three
   screenshots of a short page were often the *same image three times*, which
   is what "only one image throughout the video" looked like.

   Screenshots are now spread over the real document height rather than fixed
   0/1x/2x viewport offsets, and identical frames are dropped by md5, so the
   returned list can be shorter than requested. `assemble_video` reports
   `scene_count` so the editor lays out the right number of scenes.

   Clips **cover-crop** (`force_original_aspect_ratio=increase` + `crop`). They
   used to `decrease` + pad, which put a portrait product shot in a small box
   surrounded by black.

   **Caption layout is a lower-third, not a full-screen takeover.** The
   constants live together at the top of `video_assembler.py` (`SAFE_X`,
   `TEXT_BLOCK_W`, `HEADLINE_SIZE/Y`, `SUBTEXT_*`, `CTA_*`, `SCRIM_*`) so the
   editor's live preview can mirror them — if you move one, move
   `.ve-live-*` in `frontend/app/result/editor.css` with it. A 64px headline
   used to run the full 1280px width over a flat black wash across the whole
   frame, so the photography the ad was cut from was barely visible.

   The scrim is a gradient, weighted to the bottom-left. It has to be ~75%
   opaque *by the headline* — a single eased ramp to the bottom left that zone
   at ~12% and white text vanished on bright shots.

   `pick_cta_colors` keeps the button readable: a near-black brand colour
   disappeared into the scrim, so it falls back to a white pill.
   `sanitize_for_render` maps typographic characters to ASCII — the script
   model emits non-breaking hyphens and curly quotes that render as tofu.

   The logo is scaled into a 180x48 box and placed top-left. It used to be
   overlaid at native size, so a 512x512 apple-touch-icon covered the frame
   from y=30 down past the headline.

`POST /api/generate/rerender` re-runs step 5 only — see below.

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

7. **`screenshot_paths` could be unbound.** The background step is an
   if/elif/else; the final `else` (no site URL and no page images, so Pexels
   stock only) never assigned it, and the function's `return` reads it for
   `scene_count`. Any such render died with `UnboundLocalError` *after* paying
   for the whole pipeline. Now bound to `[]` before the branch.
8. **`mix_audio` told the truth.** It bypasses `run_ffmpeg` so it never raises,
   and the "Audio mixed successfully" print sat outside the failure branch —
   a silent fallback to voiceover-only was logged as a clean mix. It now logs
   the ffmpeg stderr, says which path it took, and returns `""` if even the
   fallback copy fails.
9. **Temp files are swept on every path.** `assemble_video` is now a thin
   wrapper whose `finally` calls `_sweep_temp(render_id)`; the pipeline itself
   moved to `_assemble_render`. The old cleanup named five paths inline and ran
   only when nothing raised — a render writes about 22. Measured: 34 orphans
   from two renders before, 0 after.
10. **The render is verified before it is called done.** `assemble_video`
    returned `"status": "done"` with no check that the MP4 existed. It now
    raises unless the file is present and over `MIN_OUTPUT_BYTES`.
11. **The Groq call is off the event loop, with a timeout.** The synchronous
    client ran inside `async def`, which FastAPI does *not* offload — measured
    at a 4.06s stall on `/api/health` during one script call, versus 3.4ms
    after. Now `asyncio.to_thread` inside `asyncio.wait_for`
    (`LLM_TIMEOUT_SECONDS`, 45s).
12. **Scraped text is fenced before it reaches the prompt.** `business_name`,
    `description` and `tagline` go through `sanitize_for_prompt` (control
    characters to spaces, whitespace collapsed, length capped, `<<<`/`>>>`
    neutralised) and are wrapped in `<<< >>>` with both the system message and
    the prompt telling the model that fenced text is material, never
    instructions.
13. **Handlers no longer return `str(e)` to the browser.** Three sites in
    `routers/generate.py` did, and the frontend renders `detail` verbatim — so
    users saw ffmpeg stderr and absolute Windows paths. `_fail()` logs the
    traceback and returns a sentence instead.

### Scene sources

Each render reports `scene_sources`: one entry per scene naming the URL it was
built from, or `""` for a scene cut from a screenshot or a stock clip, which
lives in `temp/` and cannot be asked for again. The editor sends those back so
that deleting one scene removes exactly that scene — before this it could only
send N-1 blanks, and the gap-filler refilled them from the top, so removing
scene 2 of 6 quietly shuffled 3-6 into different positions.

Verified by rendering `[0,1,2]` and `[0,2]` and comparing frames between the two
renders (comparing a frame to its *source* image does not work — the scrim and
the cover-crop dominate any downscaled fingerprint).

### Scene count

`RerenderRequest.scene_count` (1..`MAX_SCENES`, 12) says outright how many
scenes to cut the footage into. Without it the count came from however many
`scene_images` entries resolved to an image, so a slot the editor added but
left empty simply vanished. `_assemble_render` pads or trims `supplied` to that
length and takes the supplied-images path whenever the count is given, even
when every entry is blank — the gap-filler sources those from `content_images`.

### End card

`create_endcard_image` draws the ad's closing frame — logo, company name, an
accent rule, then phone / email / website / address — on the brand colour, and
`assemble_with_ffmpeg` overlays it for the last `ENDCARD_SECONDS` (3s) with a
`ENDCARD_FADE` (0.35s) dissolve. The captions, scrim and logo are gated
`enable=lt(t,card_at)` so they stop when it starts, and the background footage
is built to `duration - ENDCARD_SECONDS` so every scene still gets its full
share on screen.

Two things worth knowing if you touch it:

- **The stack is measured from font metrics, not per-string bboxes.**
  `textbbox()[3]` carries that particular string's ascender offset, so
  measuring each contact row individually spaced them visibly unevenly.
  Ascent+descent is the same for every row; `anchor="ma"` centres each line
  without measuring its width.
- **The still needs `-loop 1`.** Without it the input is one frame pinned at
  t=0, and `fade`, which runs on the *overlay's* clock rather than the main
  video's, never fires.

`assemble_with_ffmpeg` builds its filter graph from a list with input indices
tracked as they are appended. It used to be two hard-coded strings chosen by
`if has_logo`, each with the audio index written in by hand; a third optional
input made that untenable.

### Open

1. **Groq rate limit is the throughput ceiling.** `openai/gpt-oss-120b` costs
   ~3.6k tokens per script against an 8k TPM allowance — roughly two scripts a
   minute before 429s. Re-renders do **not** call the LLM, so they are exempt.
2. **No tests.** `test_tts.py` is a smoke script with no assertions. Everything
   below was verified by driving the running server, not by a suite, so it can
   regress silently.
3. **Ephemeral disk.** Renders are written to `output/` and served from local
   disk. Render's filesystem does not survive a restart or redeploy, so a
   finished video can 404 later. Needs object storage before that host is real.
4. **Render holds Chromium + Kokoro + ffmpeg resident** for a single job, and
   launches Chromium twice against the same URL (scrape, then screenshots).
   Size the instance against that before picking a plan.

---

## Re-rendering (the old integration gap, now closed)

`POST /api/generate/rerender` rebuilds an ad from edited copy. It deliberately
skips both the scrape and the LLM — the editor is holding the final text, and
re-deriving it would risk changing what the user just wrote. Takes 20-45s
against ~60s for a full generate.

Body is `RerenderRequest` (`models/generate.py`): `business_name`, `script`
(headline / subtext / cta / voiceover / music_style / scene_description),
`duration`, `url`, `logo_url`, `colors`, `scene_images`.

**`scene_images` is position-significant.** One entry per scene: a base64
`data:` URL (editor upload), an `https` URL (stock pick), or `""` meaning "leave
this scene alone". `resolve_scene_images` returns a list of the *same length*
with `None` in the gaps, and `assemble_video` fills those from a fresh capture
of `url`. Collapsing the gaps instead would shift every scene after the first
swap. Sources are capped at 8MB and re-encoded through Pillow before ffmpeg
sees them.

Two things that bit during this work, both easy to repeat:

- **`response.content.read(n)` returns *up to* n bytes, not n.** A single call
  truncated any image that arrived in more than one chunk, and the failure
  surfaced as a confusing "image file is truncated" from Pillow. Drain with
  `iter_chunked` and enforce the cap as you go.
- **The background is looped (`-stream_loop -1`) into the final composite.** A
  scene split that is not a whole number of frames left the background a few
  frames short, which truncated the video against a full-length audio track.

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
