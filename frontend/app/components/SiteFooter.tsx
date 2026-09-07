import Link from "next/link";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "/#how-it-works" },
      { label: "Ad styles", href: "/features/ad-styles" },
      { label: "Brand scraping", href: "/features/brand-scraping" },
      { label: "Video editor", href: "/features/video-editor" },
      { label: "Pricing", href: "/#pricing" },
    ],
  },
  {
    title: "Industries",
    links: [
      { label: "E-commerce", href: "/industries/ecommerce" },
      { label: "Restaurants & food", href: "/industries/restaurants" },
      { label: "Real estate", href: "/industries/real-estate" },
      { label: "SaaS & tech", href: "/industries/saas" },
      { label: "Local services", href: "/industries/local-services" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Help centre", href: "/resources/help" },
      { label: "API reference", href: "/resources/api" },
      { label: "Changelog", href: "/resources/changelog" },
      { label: "FAQ", href: "/#faq" },
      { label: "Create an ad", href: "/generate" },
    ],
  },
];

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <Link className="brand" href="/" style={{ marginBottom: "1rem" }}>
              <span className="brand-mark">⚡</span>
              AdCraft AI
            </Link>
            <p className="hint" style={{ maxWidth: 260, marginTop: "0.75rem" }}>
              Paste a URL. Get a broadcast-ready video ad in under a minute.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <p className="footer-col-title">{col.title}</p>
              <div className="footer-links">
                {col.links.map((link) => (
                  <Link key={link.label} className="footer-link" href={link.href}>
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} AdCraft AI</span>
          {/* Privacy Policy / Terms links removed rather than left pointing at "/".
              Add them back here once real legal pages exist. */}
          <div className="footer-legal">
            <span>Beta — free while in development</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
