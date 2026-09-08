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

`.site-header` uses `backdrop-filter: blur(14px)`, which makes it a containing
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

**Client state** — `lib/clientStore.ts` holds sessionStorage-backed stores.
`bannerStore` is deliberately shared between `BottomBanner.tsx` and the video
editor's Banner tab; they're two views of one value and previously diverged.

**Styling** — `app/globals.css` only. Tokens on `:root`. Breakpoints at 768px
and 1024px. Reuse existing classes before writing new ones.

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
drawer is the only navigation below that. Assert zero console errors. Keep
throwaway scripts in the scratchpad, never in the repo.
