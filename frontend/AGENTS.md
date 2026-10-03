<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- Everything below is hand-written. The block above is tool-managed —
     do not edit inside those markers; add new notes down here. -->

# AdCraft frontend — agent notes

Root context, glossary and product ground truth live in [`../CLAUDE.md`](../CLAUDE.md).
Read that too.

**Stack:** Next.js 16.2.1 (App Router, Turbopack) · React 19.2.4 · TypeScript ·
plain global CSS. **No Tailwind, no CSS-in-JS, no component library.**

---

## Traps we have already hit

Every one of these cost real debugging time in this repo. None are hypothetical.

### `params` is a Promise

Dynamic route segments are async in Next 16:

```tsx
type Props = { params: Promise<{ slug: string }> };

export default async function Page({ params }: Props) {
  const { slug } = await params;   // await it — destructuring directly fails
}
```

Same in `generateMetadata`. See `app/industries/[slug]/page.tsx`.

### `useSearchParams` needs a Suspense boundary

Without one, the client tree up to the nearest boundary drops out of static
prerendering. `app/generate/page.tsx` is a server page that wraps `GenerateForm`
(which reads `?url=`) in `<Suspense>` purely for this. Keep that shape.

### `next lint` is gone

`npx next lint` fails in Next 16 — the command was removed, so it parses `lint`
as a directory name and errors with "Invalid project directory provided".

`npm run lint` **does** work: it runs bare `eslint`, and ESLint 9's flat config
lints the project by default (verified, exit 0). For a targeted run use:

```bash
npx eslint app lib
```

### React Compiler lint rules are enforced

Two rules bite constantly:

- **`react-hooks/set-state-in-effect`** — reading `sessionStorage` in a
  `useEffect` and calling `setState` is an error. Use `useSyncExternalStore`
  against a small external store instead. `lib/clientStore.ts` exists for
  exactly this; `getSnapshot` must return a **referentially stable** value, so
  it caches the raw JSON string and callers `JSON.parse` behind a `useMemo`.
- **`react-hooks/preserve-manual-memoization`** — a `useCallback` closing over a
  non-memoized helper from the component body fails to compile. Inline what the
  callback needs (see `closeNow` in `SiteHeader.tsx`) so it only closes over
  refs and setters.

### `useSyncExternalStore` returns the *server* snapshot during hydration

This caused a real bug: the result page redirected away from valid data.

`getServerSnapshot()` returns `null` on the hydration pass, so an effect keyed
off the hook's value fires with `null` before the client snapshot lands.
**Don't branch on the hook's value inside a mount effect** — read the store
directly, where post-mount it reflects reality:

```tsx
useEffect(() => {
  if (resultStore.getSnapshot() === null) router.replace("/generate");
}, [router]);
```

### `backdrop-filter` traps `position: fixed` children

`.site-header` uses `backdrop-filter: blur(16px)`, which makes it a containing
block for fixed-position descendants. The mobile drawer rendered inside it was
clipped to the 68px header instead of filling the viewport.

**Portal any full-screen overlay to `document.body`** — see `MobileNav.tsx`.

### Browser extensions break hydration

Grammarly and password managers stamp attributes onto `<body>` before React
hydrates (`data-gr-ext-installed`, `data-new-gr-c-s-check-loaded`). That's a
false positive, not our bug. `app/layout.tsx` carries
`<body suppressHydrationWarning>`; it applies **one level deep only**, so real
mismatches inside the app still surface. Leave it.

### Fonts

Loaded via `next/font/google` in `app/layout.tsx`, exposed as CSS variables
(`--font-inter`, `--font-display`) and consumed by `--font-sans` / `--font-head`
in `globals.css`. Don't add `@import` font rules to the stylesheet.

---

## Architecture

**Routes** — `/`, `/generate`, `/result`, three data-driven dynamic routes
(`/industries/[slug]`, `/solutions/[slug]`, `/features/[slug]`), three resource
pages, plus `not-found.tsx` and `error.tsx`. `npm run build` should report
**34 prerendered routes**; a drop means `generateStaticParams` broke.

**Content** — all User-facing copy lives in `app/content/*.ts`, never inline in
components. Add an entry there and the route generates itself.

**Navigation** — `app/components/nav-data.ts` feeds both `SiteHeader.tsx`
(desktop mega-menu) and `MobileNav.tsx` (drawer). One source, two renderers —
never fork them. Setting `soon: true` on a link dims it, adds a marker dot, and
makes the "placeholders" footnote appear automatically.

**Generation overlay** — submitting the generate form mounts
`app/generate/GeneratingOverlay.tsx`, a full-screen portal (progress on the
left, a rotating card on the right). The form stays mounted underneath, so
cancelling returns the user to their existing settings. Its close button and
Escape call `AbortController.abort()`, which `generateVideo(…, signal)` passes
to `fetch` — an aborted request is deliberate, so `handleSubmit` returns
without setting an error. To drive it in Playwright, hold the request open with
`page.route("**/api/generate/video", lambda route: None)`.

**The result page IS the editor** — `/result` renders `VideoEditor` directly,
full-screen and dark (`.ve-shell` rescopes the global light tokens for its own
subtree, so the ~430 existing rules flip theme without being rewritten). There
is no read-only summary screen and no "Edit video" button any more;
`BottomBanner.tsx` was its panel and has been deleted.

**Scene thumbnails come from the MP4, not the backend.** The renderer's three
screenshots live in `backend/temp/` and are never served, so `useSceneThumbs`
seeks a detached `<video>` to each scene mid-point and draws it to a canvas.
That needs `crossOrigin="anonymous"` on the element *and* the CORS header the
API already sends — without both, `drawImage` taints the canvas and
`toDataURL` throws (the code falls back to a numbered placeholder tile).

**Scene images** — `ScenePicker.tsx` offers upload or Pexels search
(`GET /api/media/photos`, a thin server-side proxy that keeps the key off the
client). Uploads are downscaled to 960px JPEG data URLs *before* they reach
`scenesStore`; a raw phone photo would blow sessionStorage's quota and
`safeSet` would swallow the failure, so the override would vanish on reload.

**Client state** — `lib/clientStore.ts` holds sessionStorage-backed stores:
`resultStore`, `bannerStore` and `scenesStore`.

**These stores outlive a generation, and that leaked between ads.** They are
keyed by name, not by render, so an image uploaded for one brand reappeared as
a scene in the next ad, and the bottom banner kept the previous company's
details. `GenerateForm` now calls `resetEditorState()` before storing a new
result. Two traps if you touch this:

- `sessionStorage.removeItem` alone is **not** enough. `createStore` keeps a
  module-level `cache`, so `getSnapshot` would keep returning the old string
  for the life of the tab. Use the store's `clear()`.
- Scene overrides are stamped `{ renderId, scenes }` and ignored when the id
  does not match the current render — so even a missed reset cannot paste one
  ad's uploads into another.

**The player shows the rendered file, not your edits.** Text and scene changes
are invisible in it until a re-render, which reads as the editor being broken.
`.ve-live` overlays a live composition whenever `dirty` is true — the current
scene image plus the edited headline/subtext/CTA, positioned with `cq` units to
mirror `assemble_with_ffmpeg`'s geometry on a 1280x720 frame (scrim alpha 150,
headline 64px at y=180, subtext 36px at y=340, CTA at y=520). It hides while
playing so the real render stays watchable, and a successful re-render writes
the edited script back into `resultStore` so `dirty` resets — without that the
preview sits over a file that already matches it.

**The timeline is navigation, not decoration.** Each lane opens the panel that
edits it (`LANES` maps lane -> tab in `VideoEditor.tsx`): the gutter label and
the clip both switch tabs, a video clip additionally seeks to that scene, and
the ruler plus the empty lane background still scrub. Clips `stopPropagation`
so selecting one does not also move the playhead.

**`dirty` gates the Save button**, so anything the renderer consumes has to be
in it. `voiceover` was missing and a rewritten narration script left Save
disabled. The end card is in it too, now that it actually renders.

**The End Card tab is the ad's closing scene.** It used to be "Bottom Banner":
it collected a company name, phone, address and website, drew them over the
preview, and sent *nothing* to the renderer, so a downloaded MP4 never had
them. Those details now composite into the MP4 as its final
`ENDCARD_SECONDS` (3s) — logo, name, accent rule, then phone / email /
website / address — and the footage is squeezed into the time before it so no
scene is wasted underneath. Three things to know:

- **A company name alone does not make a card.** The name is pre-filled from
  the scrape, so counting it as content would bolt three seconds onto every
  re-render whether or not anyone opened the panel. `hasCardData` requires at
  least one of phone / email / website / address.
- **`.ve-endcard` previews it** with the same stack the renderer draws, in `cq`
  units. `showLiveCaptions` excludes the card's window, because the renderer
  stops the captions when the card starts — previewing both at once would show
  a frame that can never exist.
- **The lane sits at the end**, `ENDCARD_SECONDS / duration` wide, and is solid
  rather than dashed. Dashed meant "previewed here, never rendered".

**Scenes live in the footage window, not the whole video.** Every scene
calculation used to divide the full duration by the scene count, which broke
the moment an end card existed: the last clip ran 12.5s-15s while the card sat
at 12s-15s, so they overlapped in the timeline, and `useSceneThumbs` sampled
scene 6 at 13.75s — inside the card — so its thumbnail was a picture of the
contact card. `footageEnd` (`duration - renderedTail`) is the divisor for
`sceneRange`, `showScene`, `activeScene` and the clip geometry, and
`useSceneThumbs` takes the tail length so it samples before the cut.

Note the two different counts, and don't collapse them:

- `renderedScenes` — what the file on screen was cut into. Thumbnails, seeking
  and timecodes are all keyed off this, because they describe the real video.
- `sceneCount` — `renderedScenes + extraScenes`, what the *next* render will
  produce. The panel list, the timeline clips and the payload use this.

**The scene list is an ordered array of `SceneSlot`, not a map keyed by index.**
Index-keyed overrides could not express a deletion: remove scene 2 and every
override after it pointed at the wrong scene. `scenesStore` holds
`{ renderId, slots }`; absent means "no edits, use the render's own layout"
(`baseSlots`). Add, delete and replace are all list operations, and `slotsDirty`
is just the edited list differing from `baseSlots`.

Each slot carries two things that are easy to conflate:

- `src` — what to render: a data URL, an https URL, or `""` meaning "you
  choose", which the backend fills from the page's photography.
- `thumbIndex` — which scene of the **current** render it shows. After a delete
  the list index and the file's own scene order no longer agree, so the
  thumbnail, the seek target and the `activeScene` highlight all go through
  `thumbIndex`, never the loop index. A slot no render has produced has none.

**This needs `scene_sources` from the backend.** The editor could describe a
scene it had replaced itself, but for every other one it knew the picture and
not where the picture came from — so a delete could only send N-1 blanks, and
the backend refilled them from the top, silently shuffling the survivors. The
render now reports the source URL per scene (`""` for a screenshot or stock
clip, which cannot be asked for again by name), and the editor hands each
surviving scene back by name.

**"+" appends a scene**, on the video track after the last clip, plus an Add
scene button in the panel. It adds a slot and opens the picker straight away;
leaving it empty is fine. Appended slots render `.pending` (dashed) and clicking
one opens its picker rather than seeking. **The `×` on a scene thumbnail
deletes it** (hidden on the last remaining scene — an ad with no scenes is not
an ad), and **Reset all** drops the whole edit layer.

**The `+` is not on the track, and that is deliberate.** Putting it there
failed twice: at `left: footagePct%` it fell off the right edge whenever there
was no end card (the clips reach 100%, and no end card is the default state, so
the button was missing exactly when first needed), and at `right: 4px` it sat on
top of the last clip. It now lives in `.ve-tl-aside`, a 30px column beside the
scroller, aligned with the video lane. The track is a picture of the ad's
duration; an action button is not part of that. `MAX_SCENES` (12) mirrors the
backend's cap, and the button disables there.

**One layout, two time bases — do not reintroduce a second one.** The timeline
describes the render that is *coming*; the `<video>` plays the one that is
*here*. Those differ the moment anything is pending, and keeping two scales
caused two visible bugs at once: type a phone number into an ad with no card
and the end-card clip appeared at 80-100% while the scene clips still ran to
100% (a 20% overlap), and the playhead sat over a different clip from the frame
on screen — clicking scene 6 showed the end card.

Everything is now expressed in the projected layout, and two functions convert:

- `footagePct` — the share of the track the footage takes, from
  `duration - (hasCardData ? ENDCARD_SECONDS : 0)`. Driven by the **pending**
  card, not `result.has_end_card`. The end-card clip is `left: footagePct%`,
  `width: 100 - footagePct`, so it starts exactly where the last scene stops
  and cannot overlap it by construction.
- `timeToPct(t)` — video time to a position on the track. Used by the playhead
  and by `activeScene`, so the highlighted clip, the Scenes panel and the live
  preview always show the frame that is actually on screen.
- `pctToTime(pct)` — the inverse, used by `scrubTo`. Returns `null` for a slot
  no render has produced, so clicking a pending scene seeks nowhere rather than
  somewhere wrong.

Both route through `slot.thumbIndex`, so they stay correct after a scene is
deleted or added. **With nothing pending the two spaces are identical** —
verified: clicking 8.3% lands the playhead at 8.3% — so this costs the common
case nothing.

**The timeline zooms.** `.ve-tl-scroll` is a horizontal scroller holding
`.ve-tl-track`, whose width is `zoom * 100%`. Only the track scales, so clip
positions stay in `%` of real time and remain accurate at any magnification —
`scrubTo` measures the *track*, not the scroller. Zoom runs 1x to `MAX_ZOOM`
(8) in `ZOOM_STEP` (1.5) increments, with a Fit button back to 1x. While
playing, an effect scrolls the playhead back into view when it leaves the
visible slice; it does nothing at 1x, so it never fights a scroll you made
yourself.

Adding scenes narrows the clips — the ad's duration never changes — so clip
labels degrade in steps via container queries on `.ve-clip` itself: the word
"Scene" goes, then the number moves over the thumbnail, then the thumbnail goes,
then the label. **Read those thresholds against the text's share of the clip,
not the clip's width**: a video clip's label carries `margin-left: 56px` to
clear its thumbnail, so a 74px threshold left the twelve-scene case (78px clips)
still showing the word and ellipsising the number to "S...".

The count goes to the backend as an explicit `scene_count`, because inferring it
from "entries that carry an image" gave an added-but-empty slot no way to
exist.

**Save & re-render** posts to `POST /api/generate/rerender` with the edited
script, colours and one `scene_images` entry per scene (`""` = keep that scene,
and the backend re-captures it from the site). On success it writes the new
`video_url` into `resultStore`, which flows back down as a fresh `videoSrc`
without remounting the editor, so edit state survives. Takes 20-45s, so it puts
up `.ve-rerender-scrim`.

**Single origin.** `next.config.ts` rewrites `/api/*` (plus `/docs` and
`/openapi.json`) to `BACKEND_ORIGIN`, default `http://localhost:8000` — the
same shape `../nginx.conf` uses for docker-compose. So `lib/api.ts` defaults
`BASE` to `""` and the browser never makes a cross-origin request: no CORS
preflights, and the `<video>` behind the scene thumbnails is same-origin so its
canvas is never tainted. Two settings are load-bearing:

- `experimental.proxyTimeout: 300_000` — a generate runs 45-160s and Next kills
  a proxied request at **30s** by default, returning a 500 mid-render.
- `experimental.proxyClientMaxBodySize` — the editor posts scene images as
  base64 data URLs, so bodies reach a few MB.

Set `NEXT_PUBLIC_API_URL` to an absolute URL to bypass the proxy when the
backend lives on another host.

**Styling** — `app/globals.css` only. Tokens on `:root`. Breakpoints at 768px,
900px and 1024px. Reuse existing classes before writing new ones.

---

## Design language

Reworked to sit alongside vibe.co: dark indigo hero panels, huge tight display
type, flat tinted surfaces instead of bordered cards.

- **Palette** — one accent (`--accent` indigo `#4f46e5`) with `--violet` as its
  gradient partner and `--lime` `#d8f34e` as the single pop colour. Use lime at
  most once per screen (a highlighted headline word, one CTA). Everything dark
  is `--ink` `#0a0d18`, never `#000`. `--tint-ice/mint/lavender/butter` are
  *surfaces* for bento tiles, not accents — don't promote them to text colours.
- **Type** — `Inter_Tight` for display (`--font-head`), `Inter` for body,
  `--font-mono` for labels, specs and anything numeric. Headings run tight:
  `.h1` is -0.042em at up to 5rem. Numbers carry `tabular-nums`.
- **Chrome** — the header and footer are dark on every page. Don't add a
  full-bleed `.section-dark` band next to the footer; use the inset
  `.cta-panel` instead, or the two dark blocks merge into one shapeless mass.
- **Surfaces** — prefer no border. `.bento-tile`, `.marquee-card`, `.stat`,
  `.quote-card` and `.script-item` are all borderless tinted blocks. `.card`
  keeps its hairline for interior pages.
- **Bento** — `.bento` is a 12-column grid; children take `.b-wide` (7),
  `.b-mid` (5), `.b-half` (6) or `.b-full` (12). Put the span class on the
  `<Reveal>` wrapper — that's the grid item, not the `<article>` inside it.
  `.b-full` flips to a row with the visual trailing the copy.
- **Texture** — `.grain` adds an inline-SVG noise overlay via `::after`. It sets
  `isolation: isolate`, so don't put it on an element that needs to escape its
  own stacking context.
- **Motion** — `--spring` for interactive feedback, `--transition` for colour
  changes. Everything animates `transform`/`opacity` only.
- **Page shape** — every route except `/` opens with `.page-hero`, a dark block
  with a hard bottom edge, then runs white below it. Only the landing hero
  fades into the page; repeating that fade everywhere flattens the difference.
- **Dropdowns** — the mega-panel and mobile drawer are dark. `.mega-col-title`
  and `.mega-link-icon` are *also* used on light surfaces (`MarketingPage`, the
  API page), so their dark values are scoped to `.mega-panel` / `.drawer` —
  don't move those colours back onto the base rule.

---

## Definition of done

All three clean, every time:

```bash
npx tsc --noEmit      # clean
npx eslint app lib    # clean
npm run build         # 34 routes
```

...plus **drive the real UI**. There is no browser tool here — use the Playwright
already installed in the backend venv:

```bash
cd ../backend && ./venv/Scripts/python.exe <script>.py
```

Check 390px as well as desktop: the header nav collapses at 768px and the mobile
drawer is the only navigation below that. Assert zero console errors and zero
horizontal overflow (`scrollWidth - clientWidth`). Keep throwaway scripts in the
scratchpad, never in the repo.

The desktop mega-menu opens on **hover**, not click — a synthetic `click()` in
Playwright fires `mouseenter` first, which opens the panel, and the click then
toggles it straight back shut. Drive it with `page.hover()`.

`/result` reads its data from `sessionStorage["adcraft_result"]` and redirects to
`/generate` without it. To screenshot it, load any page first, seed the key with
a `VideoResult`-shaped object (see `lib/api.ts`), then navigate to `/result`.
