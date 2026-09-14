# AdCraft AI — agent bootstrap

Read this before touching anything. Every command here has been run in this repo
and works; do not improvise alternatives.

---

## Glossary — who is who

Used consistently across all docs in this repo. When these docs say:

| Term | Means |
|---|---|
| **You** | The AI agent reading this and making changes. |
| **Me / Us / We** | The human developer(s) who own this repo. You act on our instructions. |
| **Users / visitors / customers** | End-users of AdCraft — business owners who paste a URL to get a video ad. They never see this file. |

Consequences that actually matter:

- "You built X" = the agent wrote it. "We decided X" = a human made the call.
- Copy written for **Users** goes in `frontend/app/content/`. Notes for **You**
  go in markdown files like this one. Never mix them.
- When a doc says "ask us first", that means stop and ask the human — not
  guess, and not proceed under an assumption.

---

## What this product is

Paste a business URL → get a finished, narrated MP4 video ad in under a minute.

Pipeline: **scrape the site → write a script with an LLM → synthesise narration
→ mix music → render with FFmpeg → serve the MP4.**

---

## Layout

```
adcraft-ai/
├── backend/          FastAPI. The whole generation pipeline.
│   ├── server.py     App entry. CORS, routers, static /api/output mount.
│   ├── routers/      scrape.py, generate.py
│   ├── services/     scraper, script_generator, tts, music, pexels, video_assembler
│   ├── models/       Pydantic schemas + Kokoro .onnx/.bin weights
│   ├── music/        5 royalty-free mp3 beds (git-lfs)
│   ├── output/       Rendered MP4s (gitignored)
│   └── temp/         Per-render scratch (gitignored)
└── frontend/         Next.js 16 App Router. See frontend/AGENTS.md.
```

---

## Commands

### Backend

```bash
cd backend
./venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000   # Windows
# Docker/prod equivalent: uvicorn server:app --host 0.0.0.0 --port ${PORT}
```

The venv already exists at `backend/venv/`. On Windows the interpreter is
`backend/venv/Scripts/python.exe` — use that path directly rather than trying to
activate the venv from the Bash tool.

**`requirements.txt` is UTF-16-LE with a BOM.** Plain `pip install -r` and `cat`
both misbehave on it. To read it, decode explicitly:

```bash
python -c "print(open('backend/requirements.txt',encoding='utf-16').read())"
```

If you ever regenerate it, write UTF-8 and say so — don't silently change the
encoding as a side effect of something else.

### Frontend

```bash
cd frontend
npm run dev            # http://localhost:3000
npm run build          # must pass before you claim anything is done
npx tsc --noEmit       # typecheck
npx eslint app lib     # lint — see the note below
```

**`next lint` no longer exists in Next 16** — `npx next lint` fails with
"Invalid project directory provided". `npm run lint` works (bare `eslint`; flat
config lints the project). `npx eslint app lib` is the targeted equivalent.

### Environment

`backend/.env` — copy from `.env.example`:

- `GROQ_API_KEY` — **required**, the LLM.
- `PEXELS_API_KEY` — **required**, stock-footage fallback.
- `ALLOWED_ORIGINS` — comma-separated CORS origins.

`frontend/.env.local`:

- `NEXT_PUBLIC_API_URL` — backend base URL, defaults to `http://localhost:8000`.

`backend/config/` has been deleted. It declared `ANTHROPIC_API_KEY`,
`CREATOMATE_API_KEY` and six other settings, and nothing in the repo imported
the module — all eight were dead. The LLM is Groq (`openai/gpt-oss-120b`, the
`MODEL` constant in `services/script_generator.py`). Every real setting is read
with `os.getenv` at its point of use: `ALLOWED_ORIGINS` in `server.py`,
`GROQ_API_KEY` in `script_generator.py`, `PEXELS_API_KEY` in `pexels.py`.

---

## Ground truth about the product

Get these wrong and we ship false claims to Users.

| Fact | Value | Source |
|---|---|---|
| Output resolution | **720p** (1280×720) | `services/video_assembler.py` `VIDEO_WIDTH/HEIGHT` |
| Codecs | H.264 video, AAC 128 kbps | `assemble_with_ffmpeg` |
| Frame rate | 30 fps | `VIDEO_FPS` |
| Ad lengths | 15s or 30s only | validated in `routers/generate.py` |
| Ad styles | modern, bold, minimal, playful | validated in `routers/generate.py` |
| Narration voices | 4 (Kokoro, local) | `services/tts.py` `VOICES` |
| Music beds | 5 mp3 files | `backend/music/` |
| LLM | GPT-OSS 120B via Groq | `services/script_generator.py` `MODEL` |

We advertised "1080p" once by mistake and it shipped to the landing page.
**If you state a spec on a User-facing page, read it out of the code first.**

---

## Content honesty rules

Non-negotiable, and they apply to anything Users will read.

- **Never invent testimonials, customer names, review scores, or metrics.** No
  fake "4.8 on G2", no "+200% conversions", no named customers. Fabricated
  endorsements are deceptive and, in most markets, illegal. If we ask for
  social proof and have no real data, build something honest instead (an FAQ, a
  spec table, real product output) and say why.
- **Don't claim capability the backend doesn't have.** The FAQ in
  `frontend/app/content/faq.ts` openly states that editor changes don't yet
  re-render the MP4. Keep that honest as the code changes.
- If a page must ship with unreal content, mark it visibly — the repo already
  has a `soon` flag on nav links and `.is-placeholder` styling that renders a
  loud `PLACEHOLDER` chip. Use those instead of quietly shipping filler.

---

## Conventions

**Styling** — one global stylesheet, `frontend/app/globals.css`, with CSS custom
properties on `:root`. Light theme, blue accent (`--accent: #2563eb`). Reuse the
existing classes (`.section`, `.card`, `.btn`, `.h1/.h2`, `.grid-3`, `.chip`)
rather than adding new ones. **There is no Tailwind** — don't introduce it.

**Marketing pages** — data lives in `frontend/app/content/*.ts` and renders
through `MarketingPage.tsx` via three dynamic routes. To add a page, add an
entry to the data file; the route and `generateStaticParams` pick it up.

**Navigation** — `frontend/app/components/nav-data.ts` is the single source for
both the desktop mega-menu (`SiteHeader.tsx`) and the mobile drawer
(`MobileNav.tsx`). Add a link once, it appears in both. Never fork the two.

**Verification** — before saying work is done, run typecheck, lint and build,
and drive the actual UI. There is no browser tool in this environment; use the
Playwright already installed in the backend venv:

```bash
cd backend && ./venv/Scripts/python.exe path/to/script.py
```

Screenshot and assert against the running dev server. Put throwaway scripts in
the scratchpad directory, never in the repo.

---

## Known open issues

The seven backend issues previously listed here are fixed, as is the frontend
re-render gap. `backend/AGENTS.md` carries the detail and the current list.

Items 1-4 of the old list are fixed too: the Groq call now runs via
`asyncio.to_thread` under a 45s `wait_for`, `mix_audio` logs what actually
happened, `assemble_video` sweeps its temp files in a `finally` and verifies the
MP4 exists before reporting done, and scraped text is sanitised and fenced
before it reaches the prompt. `backend/AGENTS.md` has the detail.

Still open, none of them blocking:

1. There are no tests. Everything above was verified against the running
   server, which means it can regress without anything noticing.
2. Render's disk is ephemeral, so a finished MP4 can 404 after a redeploy.
3. **Pushing to the Hugging Face Space is blocked**: old commits contain raw
   (non-LFS) binaries. The current tip is fine — history is not. Fixing needs
   `git filter-repo`/BFG or a fresh history. **Destructive — ask us first.**

**The media files are git-lfs.** `models/*.onnx`, `models/*.bin` and
`music/*.mp3` were sitting as 130-byte pointers, so Kokoro could not load and
every ad rendered silent while still reporting success. `git lfs pull` fixes a
checkout; `server.py` now checks at boot and says so loudly. A Docker build
needs LFS materialised in the build context or the image has the same problem.

---

## Working agreement

- **Don't commit or push unless we ask.** Long sessions here routinely end with
  a large uncommitted diff, and that's intentional.
- Frontend and backend are worked separately. We said "finish the frontend
  first, then backend and integration" — respect that split unless told otherwise.
- Report honestly. If tests fail, show the output. If you skipped something, say
  so. Don't claim verification you didn't run.
