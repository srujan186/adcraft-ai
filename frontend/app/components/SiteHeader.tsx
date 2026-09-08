"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { MENUS, type NavLink as NavLinkT } from "./nav-data";
import NavIcon from "./NavIcon";
import MobileNav from "./MobileNav";

const OPEN_DELAY = 90;
const CLOSE_DELAY = 160;

export default function SiteHeader() {
  const [openId, setOpenId] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const headerRef = useRef<HTMLElement>(null);
  const triggers = useRef<Record<string, HTMLButtonElement | null>>({});

  const clear = () => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
  };

  const openLater = (id: string) => {
    clear();
    timer.current = setTimeout(() => setOpenId(id), OPEN_DELAY);
  };

  const closeLater = () => {
    clear();
    timer.current = setTimeout(() => setOpenId(null), CLOSE_DELAY);
  };

  // Inlines the timer clear rather than closing over `clear`, which is a fresh
  // function each render and would defeat the memoization.
  const closeNow = useCallback(() => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    setOpenId(null);
  }, []);

  // Close on outside click, and on Escape (returning focus to the trigger).
  useEffect(() => {
    if (!openId) return;

    function onPointerDown(e: PointerEvent) {
      if (!headerRef.current?.contains(e.target as Node)) closeNow();
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        const id = openId;
        closeNow();
        if (id) triggers.current[id]?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [openId, closeNow]);

  useEffect(() => clear, []);

  const menu = MENUS.find((m) => m.id === openId) ?? null;

  return (
    <header
      className="site-header"
      ref={headerRef}
      onBlur={(e) => {
        // Close when focus leaves the header entirely (keyboard tab-out).
        if (!e.currentTarget.contains(e.relatedTarget as Node)) closeNow();
      }}
    >
      <div className="site-header-bar">
        <div className="site-header-inner">
          <Link className="brand" href="/" onClick={closeNow}>
            <span className="brand-mark">⚡</span>
            AdCraft AI
          </Link>

          <nav className="nav-links" aria-label="Main">
            {MENUS.map((m) => (
              <button
                key={m.id}
                type="button"
                ref={(el) => { triggers.current[m.id] = el; }}
                id={`nav-trigger-${m.id}`}
                className={`nav-trigger${openId === m.id ? " open" : ""}`}
                aria-expanded={openId === m.id}
                aria-haspopup="true"
                aria-controls={`nav-panel-${m.id}`}
                onClick={() => { clear(); setOpenId(openId === m.id ? null : m.id); }}
                onMouseEnter={() => openLater(m.id)}
                onMouseLeave={closeLater}
                onFocus={() => { clear(); setOpenId(m.id); }}
              >
                {m.label}
                <svg className="nav-chev" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
                     strokeLinejoin="round" aria-hidden="true">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
            ))}

            <Link className="nav-link" href="/#pricing" onClick={closeNow}>Pricing</Link>
            <Link className="nav-link" href="/#faq" onClick={closeNow}>FAQ</Link>
          </nav>

          <div className="nav-actions">
            <Link className="btn btn-primary btn-sm" href="/generate" onClick={closeNow}>
              Create an ad
            </Link>
            <MobileNav />
          </div>
        </div>
      </div>

      {menu && (
        <div
          className="mega-panel"
          id={`nav-panel-${menu.id}`}
          role="group"
          aria-label={menu.label}
          onMouseEnter={clear}
          onMouseLeave={closeLater}
        >
          <div className="mega-inner">
            <div className={`mega-cols${menu.promo ? " has-promo" : ""}`}>
              {menu.columns.map((col, i) => (
                <div className="mega-col" key={i}>
                  {col.title && <p className="mega-col-title">{col.title}</p>}
                  <ul className="mega-links">
                    {col.links.map((link) => (
                      <li key={link.label}>
                        <MegaLink link={link} onNavigate={closeNow} />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              {menu.promo && (
                <Link className="mega-promo" href={menu.promo.href} onClick={closeNow}>
                  <span className="mega-promo-eyebrow">{menu.promo.eyebrow}</span>
                  <span className="mega-promo-title">{menu.promo.title}</span>
                  <span className="mega-promo-body">{menu.promo.body}</span>
                  <span className="mega-promo-cta">{menu.promo.cta}</span>
                </Link>
              )}
            </div>

            {menu.columns.some((c) => c.links.some((l) => l.soon)) && (
              <p className="mega-note">
                <span className="mega-note-dot" aria-hidden="true" />
                Dimmed items are placeholders — those pages aren&apos;t built yet.
              </p>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function MegaLink({ link, onNavigate }: { link: NavLinkT; onNavigate: () => void }) {
  return (
    <Link
      className={`mega-link${link.soon ? " soon" : ""}`}
      href={link.href}
      onClick={onNavigate}
      aria-describedby={link.soon ? "mega-soon-hint" : undefined}
    >
      {link.icon && <NavIcon name={link.icon} />}
      <span className="mega-link-text">
        <span className="mega-link-label">
          {link.label}
          {link.soon && <span className="mega-soon-dot" aria-label="coming soon" />}
        </span>
        {link.desc && <span className="mega-link-desc">{link.desc}</span>}
      </span>
    </Link>
  );
}
