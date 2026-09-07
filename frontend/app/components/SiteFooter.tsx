import Link from "next/link";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "/#how-it-works" },
      { label: "Ad styles", href: "/#styles" },
      { label: "Pricing", href: "/#pricing" },
      { label: "Create an ad", href: "/generate" },
    ],
  },
  {
    title: "Built with",
    links: [
      { label: "Llama 3.3 70B via Groq", href: "/#how-it-works" },
      { label: "Kokoro TTS", href: "/#how-it-works" },
      { label: "Pexels stock footage", href: "/#how-it-works" },
      { label: "FFmpeg", href: "/#how-it-works" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/" },
      { label: "Contact", href: "/" },
      { label: "Careers", href: "/" },
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
          <div className="footer-legal">
            <Link className="footer-link" href="/">Privacy Policy</Link>
            <Link className="footer-link" href="/">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
