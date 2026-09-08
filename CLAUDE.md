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

`backend/config/settings.py` still declares `ANTHROPIC_API_KEY` and
`CREATOMATE_API_KEY`. **Both are dead** — nothing reads them. The real LLM is
Groq (`llama-3.3-70b-versatile` in `services/script_generator.py`). Don't wire
anything new to those two without asking us.

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
| LLM | Llama 3.3 70B via Groq | `services/script_generator.py` |

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

Do not "discover" and silently fix these — we know. Ask before touching them.

**Backend (deferred by us — frontend was finished first):**

1. `POST /api/scrape/debug` fetches any user-supplied URL server-side and echoes
   headers/HTML back. Unauthenticated, comment says "DELETE before production".
   Still wired up.
2. `services/scraper.py` `extract_colors_from_stylesheets` uses **blocking**
   `urllib.request.urlopen` inside an `async` handler — stalls the event loop
   for up to 10s per scrape.
3. `/api/generate/from-url` and `/api/generate/video` accept raw `dict`, so
   `ad_style` and `duration` are unvalidated (unlike `/generate/script`).
4. The `calm` music style has no matching file in `backend/music/`, so it
   silently falls back. Either rename the soft-background mp3 to contain
   `calm`, or drop `calm` from `STYLE_KEYWORDS` in `services/music.py`.
5. `scrape_with_httpx` has unreachable code after its `return`.

**Frontend:**

6. The video editor previews edits and persists them, but **nothing re-renders
   the MP4** — Download still returns the original. This is the main
   integration gap. The FAQ discloses it honestly; keep that in sync when fixed.

**Repo:**

7. Pushing to the Hugging Face Space is blocked: old commits contain raw
   (non-LFS) binaries. The current tip is fine — history is not. Fixing needs
   `git filter-repo`/BFG or a fresh history. **Destructive — ask us first.**

---

## Working agreement

- **Don't commit or push unless we ask.** Long sessions here routinely end with
  a large uncommitted diff, and that's intentional.
- Frontend and backend are worked separately. We said "finish the frontend
  first, then backend and integration" — respect that split unless told otherwise.
- Report honestly. If tests fail, show the output. If you skipped something, say
  so. Don't claim verification you didn't run.
