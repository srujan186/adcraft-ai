"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { portalRoot } from "./portalRoot";
import Link from "next/link";
import { MENUS } from "./nav-data";
import NavIcon from "./NavIcon";

// Drives the same MENUS data as the desktop mega-menu, so the two can never
// drift apart — add a link there and it appears in both.

export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<string | null>(null);

  // Lock body scroll while the drawer is open, and close on Escape.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const close = () => { setOpen(false); setSection(null); };

  return (
    <>
      <button
        type="button"
        className="burger"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls="mobile-drawer"
        onClick={() => setOpen((o) => !o)}
      >
        <span className={`burger-box${open ? " open" : ""}`}>
          <span /><span /><span />
        </span>
      </button>

      {/* Portalled to <body>: .site-header sets backdrop-filter, which makes it
          a containing block for position:fixed descendants — rendering the
          drawer inside it clipped the panel to the header's height. */}
      {open && createPortal(
        <>
          <div className="drawer-scrim" onClick={close} aria-hidden="true" />
          <div className="drawer" id="mobile-drawer" role="dialog" aria-modal="true" aria-label="Menu">
            <nav className="drawer-body">
              {MENUS.map((menu) => {
                const isOpen = section === menu.id;
                return (
                  <div className="drawer-group" key={menu.id}>
                    <button
                      type="button"
                      className={`drawer-section${isOpen ? " open" : ""}`}
                      aria-expanded={isOpen}
                      onClick={() => setSection(isOpen ? null : menu.id)}
                    >
                      {menu.label}
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                           strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                        <path d="M6 9l6 6 6-6" />
                      </svg>
                    </button>

                    {isOpen && (
                      <div className="drawer-links">
                        {menu.columns.map((col, ci) => (
                          <div key={ci}>
                            {col.title && <p className="drawer-col-title">{col.title}</p>}
                            {col.links.map((link) => (
                              <Link
                                key={link.label}
                                href={link.href}
                                className="drawer-link"
                                onClick={close}
                              >
                                {link.icon && <NavIcon name={link.icon} />}
                                {link.label}
                              </Link>
                            ))}
                          </div>
                        ))}
                        {menu.promo && (
                          <Link href={menu.promo.href} className="drawer-promo" onClick={close}>
                            {menu.promo.title} →
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              <Link className="drawer-section plain" href="/#pricing" onClick={close}>Pricing</Link>
              <Link className="drawer-section plain" href="/#faq" onClick={close}>FAQ</Link>
              <Link className="drawer-section plain" href="/login" onClick={close}>Log in</Link>
              <Link className="drawer-section plain" href="/signup" onClick={close}>Sign up</Link>

              <Link className="btn btn-primary btn-block" href="/generate" onClick={close}
                    style={{ marginTop: "1.25rem" }}>
                Create an ad
              </Link>
            </nav>
          </div>
        </>,
        portalRoot()
      )}
    </>
  );
}
