# 05 — Design system

Look & feel: clean, light B2B SaaS. White canvas, dark navy top nav, slate text, one saturated
indigo/violet accent, rounded cards with hairline borders, generous whitespace, Inter font.
(Values below were measured from the reference app and rounded — they are generic Tailwind-like values.)

## Tokens (`web/src/app/globals.css`, Tailwind v4 `@theme`)
```css
@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;

  --color-bg: #ffffff;
  --color-bg-subtle: #f8fafc;      /* page sections, table header, wizard canvas */
  --color-surface: #ffffff;        /* cards */
  --color-border: #e2e8f0;         /* hairlines */
  --color-border-strong: #cbd5e1;

  --color-text: #0f172b;           /* headings (slate-900) */
  --color-text-body: #314158;      /* body (slate-700) */
  --color-text-muted: #62748e;     /* helper text (slate-500) */

  --color-nav: #1d293d;            /* top nav background (dark navy) */
  --color-nav-text: #e2e8f0;
  --color-nav-active: #ffffff;     /* + 2px underline in primary-300 */

  --color-primary: #4f39f6;        /* buttons, active step, links, selected radio */
  --color-primary-hover: #432dd7;
  --color-primary-50: #eef2ff;     /* selected option background */
  --color-primary-300: #a3b3ff;

  --color-success: #00a63e;  --color-success-50: #f0fdf4;
  --color-warning: #e17100;  --color-warning-50: #fffbeb;   /* "Draft"/"No data" chips use warning-50 bg */
  --color-danger:  #e7000b;  --color-danger-50:  #fef2f2;   /* "Insufficient", "Blocked", targeting-too-narrow card */
  --color-info: #155dfc;

  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-xl: 16px;
  --shadow-card: 0 1px 2px rgb(15 23 42 / 0.05);
  --shadow-pop: 0 10px 30px rgb(15 23 42 / 0.12);
}
```
Dark mode: not required for v1 (reference app is light-only).

## Typography
| Use | Size / weight |
|---|---|
| Page title (h1) | 30px / 700, `--color-text` |
| Section card title | 16px / 600 with 16px leading icon |
| Body | 14px / 400 (`text-sm`) ; base html 16px |
| Helper / captions | 12–13px / 400 muted |
| Step labels in wizard rail | 11px / 600 uppercase tracking-wide + 13px description |
| Numbers in KPI tiles | 24px / 600 tabular-nums |

## Layout primitives
- **AppShell:** sticky top nav 56px (dark navy) → logo left, primary nav links, right side: notifications bell,
  "Ask Agent" outline button (white border, sparkle-plus icon), account switcher (avatar square + account name + chevron).
- **PageHeader:** h1 + muted subtitle on left, primary CTA on right ("+ Create campaign", "+ New audience"...),
  32px padding, bottom border.
- **Card:** white, 1px border, radius-lg, 20–24px padding, title row with optional right-side icon button.
- **Wizard layout:** 3 columns — left step rail 220px, center form max-w 720px (cards stacked), right sticky
  "Strategy Estimate" panel 260px. Sticky footer bar inside the center column with back/continue buttons.
- **Modals:** right-anchored large sheet (≈ 640px wide, full height, radius-xl on left) with title, close X,
  body scroll, footer with pagination dots (multi-step) + primary button bottom-right.
- **Empty states:** centered small illustration (simple line SVG you draw yourself), bold title, muted line, primary button.

## Components (build in `components/app`)
`AppShell, TopNav, AccountSwitcher, PageHeader, KpiTile, StatusPill, GoalBadge, EmptyState, DateRangePicker,
FilterPill (icon + label + sort-chevrons), DataTable (sortable, column chooser, totals row, sticky first column),
ChartCard (metric selector + line/bar toggle), StepRail, WizardFooter, OptionCard (radio card with icon,
title, description; selected = primary border + primary-50 bg), SegmentTree (checkbox tree with reach badge),
ChannelPicker (grid of channel tiles with logo + reach), DaypartGrid (7×48 toggle grid with presets),
EstimatePanel, InlineAlert (danger/warning/info variants), AskAgentButton, AgentPopover, AgentSidePanel,
RecommendationCard, ForecastChart, HeatmapUS, ReportBuilder, UploadDropzone, VideoPreviewDialog, PixelSnippet (copy button).`

## Status pills
| Status | Style |
|---|---|
| Draft | warning-50 bg, warning text |
| In review | info-50 / info |
| Learning | primary-50 / primary, pulsing dot |
| Delivering | success-50 / success, dot |
| Paused | slate-100 / slate-600 |
| Blocked | danger-50 / danger |
| Completed | slate-100 / slate-500 |

## Interaction rules
- Every form field has an (i) tooltip explaining it in one sentence.
- Unsaved wizard changes: "Save" button in top bar becomes enabled; leaving shows a confirm dialog.
- Optimistic updates for toggles; toasts (bottom-right) for success/error.
- Numbers: `Intl.NumberFormat` compact for reach (`38.9M`), currency with 2 decimals, percentages 1 decimal.
