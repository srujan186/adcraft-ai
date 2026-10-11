// ─────────────────────────────────────────────────────────────────────────────
// Navigation data for the header mega-menu.
//
// Every entry below resolves to a real page. The `soon` flag is retained for
// future use: setting it dims the link, adds a marker dot, and makes the
// "placeholders" footnote appear on that panel automatically.
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
          { label: "Launch a campaign fast", href: "/solutions/launch-fast",      icon: "zap" },
          { label: "Build brand awareness",  href: "/solutions/brand-awareness",  icon: "megaphone" },
          { label: "Refresh old creative",   href: "/solutions/refresh-creative", icon: "refresh" },
          { label: "Test ad variations",     href: "/solutions/test-variations",  icon: "layers" },
          { label: "Promote a product",      href: "/solutions/promote-product",  icon: "tag" },
          { label: "Announce an offer",      href: "/solutions/announce-offer",   icon: "percent" },
          { label: "Localise for a market",  href: "/solutions/localize",         icon: "globe" },
        ],
      },
      {
        title: "By feature",
        links: [
          { label: "Brand scraping",     href: "/features/brand-scraping",  icon: "scan" },
          { label: "AI script writing",  href: "/features/ai-script",       icon: "pen" },
          { label: "Voiceover & music",  href: "/features/voiceover-music", icon: "mic" },
          { label: "Video editor",       href: "/features/video-editor",    icon: "film" },
          { label: "Ad styles",          href: "/features/ad-styles",       icon: "sparkles" },
          { label: "Integrations & API", href: "/features/api",             icon: "plug" },
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
          { label: "E-commerce",         href: "/industries/ecommerce" },
          { label: "Restaurants & food", href: "/industries/restaurants" },
          { label: "Fitness & wellness", href: "/industries/fitness" },
          { label: "Healthcare",         href: "/industries/healthcare" },
        ],
      },
      {
        links: [
          { label: "Real estate", href: "/industries/real-estate" },
          { label: "SaaS & tech", href: "/industries/saas" },
          { label: "Automotive",  href: "/industries/automotive" },
          { label: "Education",   href: "/industries/education" },
        ],
      },
      {
        links: [
          { label: "Salon & spa",    href: "/industries/salon-spa" },
          { label: "Local services", href: "/industries/local-services" },
          { label: "Nonprofits",     href: "/industries/nonprofits" },
          { label: "Events",         href: "/industries/events" },
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
          { label: "Help centre",        href: "/resources/help",        desc: "Answers to common questions" },
          { label: "Guides",             href: "/resources/help#guides", desc: "Getting the most out of it" },
          { label: "How it works",       href: "/#how-it-works",         desc: "The pipeline, end to end" },
        ],
      },
      {
        title: "Developers",
        links: [
          { label: "API reference", href: "/resources/api",       desc: "Generate ads programmatically" },
          { label: "Changelog",     href: "/resources/changelog", desc: "What shipped recently" },
        ],
      },
      {
        title: "Get started",
        links: [
          { label: "Create an ad", href: "/generate", desc: "Free while in beta" },
          { label: "Ad styles",    href: "/features/ad-styles", desc: "Modern, Bold, Minimal, Playful" },
          { label: "FAQ",          href: "/#faq",     desc: "Cost, timing and formats" },
        ],
      },
    ],
  },
];
