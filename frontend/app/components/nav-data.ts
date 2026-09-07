// ─────────────────────────────────────────────────────────────────────────────
// Navigation data for the header mega-menu.
//
// PLACEHOLDER SCAFFOLDING: most of these destinations do not exist yet. Any
// entry with `soon: true` renders dimmed with a marker dot and points at "/".
// As you build each page, set its real `href` and delete the `soon` flag —
// the dimmed styling and the "placeholders" footnote disappear on their own
// once a panel has no `soon` entries left.
// ─────────────────────────────────────────────────────────────────────────────

export type NavLink = {
  label: string;
  href: string;
  icon?: IconName;
  desc?: string;
  soon?: boolean;
};

export type IconName =
  | "zap" | "megaphone" | "refresh" | "layers" | "tag" | "percent" | "globe"
  | "scan" | "pen" | "mic" | "film" | "sparkles" | "plug";

export type NavMenu = {
  id: string;
  label: string;
  kind: "mega" | "list";
  columns: { title?: string; links: NavLink[] }[];
  promo?: { eyebrow: string; title: string; body: string; href: string; cta: string };
};

export const MENUS: NavMenu[] = [
  {
    id: "product",
    label: "Product",
    kind: "mega",
    columns: [
      {
        title: "By goal",
        links: [
          { label: "Launch a campaign fast", href: "/", icon: "zap",       soon: true },
          { label: "Build brand awareness",  href: "/", icon: "megaphone", soon: true },
          { label: "Refresh old creative",   href: "/", icon: "refresh",   soon: true },
          { label: "Test ad variations",     href: "/", icon: "layers",    soon: true },
          { label: "Promote a product",      href: "/", icon: "tag",       soon: true },
          { label: "Announce an offer",      href: "/", icon: "percent",   soon: true },
          { label: "Localize for a market",  href: "/", icon: "globe",     soon: true },
        ],
      },
      {
        title: "By feature",
        links: [
          { label: "Brand scraping",     href: "/",                icon: "scan",     soon: true },
          { label: "AI script writing",  href: "/#how-it-works",   icon: "pen" },
          { label: "Voiceover & music",  href: "/",                icon: "mic",      soon: true },
          { label: "Video editor",       href: "/",                icon: "film",     soon: true },
          { label: "Ad styles",          href: "/#styles",         icon: "sparkles" },
          { label: "Integrations & API", href: "/",                icon: "plug",     soon: true },
        ],
      },
    ],
    promo: {
      eyebrow: "AdCraft Studio",
      title: "Your first ad, free",
      body: "Paste a URL and get a finished video ad in under a minute.",
      href: "/generate",
      cta: "Create an ad →",
    },
  },
  {
    id: "industries",
    label: "Industries",
    kind: "list",
    columns: [
      {
        links: [
          { label: "E-commerce",       href: "/", soon: true },
          { label: "Restaurants & food", href: "/", soon: true },
          { label: "Fitness & wellness", href: "/", soon: true },
          { label: "Healthcare",       href: "/", soon: true },
        ],
      },
      {
        links: [
          { label: "Real estate",  href: "/", soon: true },
          { label: "SaaS & tech",  href: "/", soon: true },
          { label: "Automotive",   href: "/", soon: true },
          { label: "Education",    href: "/", soon: true },
        ],
      },
      {
        links: [
          { label: "Salon & spa",    href: "/", soon: true },
          { label: "Local services", href: "/", soon: true },
          { label: "Nonprofits",     href: "/", soon: true },
          { label: "Events",         href: "/", soon: true },
        ],
      },
    ],
  },
  {
    id: "resources",
    label: "Resources",
    kind: "list",
    columns: [
      {
        title: "Learn",
        links: [
          { label: "Blog",               href: "/", desc: "Product news and playbooks", soon: true },
          { label: "Guides & tutorials", href: "/", desc: "Step-by-step walkthroughs",  soon: true },
          { label: "Case studies",       href: "/#results", desc: "Real customer results" },
        ],
      },
      {
        title: "Build",
        links: [
          { label: "Help center",       href: "/", desc: "Answers to common questions", soon: true },
          { label: "API documentation", href: "/", desc: "Generate ads programmatically", soon: true },
          { label: "Changelog",         href: "/", desc: "What shipped recently", soon: true },
        ],
      },
      {
        title: "Connect",
        links: [
          { label: "Community",       href: "/", desc: "Join other AdCraft users", soon: true },
          { label: "Contact support",  href: "/", desc: "Get help from our team",  soon: true },
          { label: "Ad templates",     href: "/", desc: "Starting points by industry", soon: true },
        ],
      },
    ],
  },
];
