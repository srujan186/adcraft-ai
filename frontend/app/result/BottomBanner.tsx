"use client";
import { useState, useEffect } from "react";
import type { ScrapeResult } from "@/lib/api";

interface BannerData {
  companyName: string;
  phone: string;
  address: string;
  website: string;
  primaryColor: string;
  accentColor: string;
}

interface Props {
  scraped: ScrapeResult;
}

export default function BottomBanner({ scraped }: Props) {
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [banner, setBanner] = useState<BannerData>({
    companyName: scraped.business_name ?? "",
    phone: "",
    address: "",
    website: "",
    primaryColor: scraped.colors?.primary ?? "#1a1a2e",
    accentColor: scraped.colors?.accent ?? "#6c63ff",
  });

  // Load saved banner from sessionStorage on mount
  useEffect(() => {
    const raw = sessionStorage.getItem("adcraft_banner");
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as BannerData;
        setBanner(parsed);
      } catch {
        // ignore
      }
    }
  }, []);

  function handleChange(field: keyof BannerData, value: string) {
    setSaved(false);
    setBanner((prev) => ({ ...prev, [field]: value }));
  }

  function handleSave() {
    sessionStorage.setItem("adcraft_banner", JSON.stringify(banner));
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  const brandPrimary = banner.primaryColor;
  const brandAccent = banner.accentColor;

  return (
    <div style={{ marginTop: "2rem" }}>
      {/* Section header — click to expand */}
      <button
        id="bottom-banner-toggle"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: open ? "var(--radius-lg) var(--radius-lg) 0 0" : "var(--radius-lg)",
          padding: "1.1rem 1.5rem",
          cursor: "pointer",
          color: "var(--text)",
          fontFamily: "var(--font-head)",
          fontWeight: 700,
          fontSize: "1rem",
          transition: "border-color 0.22s, background 0.22s",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span style={{
            fontSize: "1.2rem",
            background: "var(--accent-soft)",
            borderRadius: "8px",
            width: 32, height: 32,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>🏷️</span>
          Bottom Banner
          <span className="badge" style={{ marginLeft: "0.25rem" }}>NEW</span>
        </span>
        <span style={{
          transform: open ? "rotate(180deg)" : "rotate(0deg)",
          transition: "transform 0.22s",
          color: "var(--text-muted)",
          fontSize: "1.1rem",
        }}>▼</span>
      </button>

      {/* Expandable body */}
      <div style={{
        overflow: "hidden",
        maxHeight: open ? "1200px" : "0",
        transition: "max-height 0.5s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderTop: "none",
          borderRadius: "0 0 var(--radius-lg) var(--radius-lg)",
          padding: "1.75rem",
        }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "2rem",
          }}>
            {/* LEFT — form */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                Add company contact info that appears as a banner at the bottom of your video.
              </p>

              <Field
                label="Company Name"
                id="banner-company"
                value={banner.companyName}
                placeholder="Nike, Inc."
                onChange={(v) => handleChange("companyName", v)}
              />
              <Field
                label="Phone Number"
                id="banner-phone"
                value={banner.phone}
                placeholder="+1 (800) 555-0100"
                onChange={(v) => handleChange("phone", v)}
              />
              <Field
                label="Address"
                id="banner-address"
                value={banner.address}
                placeholder="One Bowerman Drive, Beaverton, OR"
                onChange={(v) => handleChange("address", v)}
              />
              <Field
                label="Website URL"
                id="banner-website"
                value={banner.website}
                placeholder={`${scraped.business_name?.toLowerCase().replace(/\s+/g, "")}.com`}
                onChange={(v) => handleChange("website", v)}
              />

              {/* Color pickers */}
              <div style={{ display: "flex", gap: "1rem" }}>
                <div style={{ flex: 1 }}>
                  <label style={{
                    display: "block",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    marginBottom: "0.4rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.07em",
                  }}>Banner Color</label>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <input
                      id="banner-primary-color"
                      type="color"
                      value={banner.primaryColor}
                      onChange={(e) => handleChange("primaryColor", e.target.value)}
                      style={{
                        width: 38, height: 38,
                        border: "none",
                        borderRadius: "8px",
                        cursor: "pointer",
                        background: "none",
                        padding: 2,
                      }}
                    />
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {banner.primaryColor}
                    </span>
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{
                    display: "block",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    marginBottom: "0.4rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.07em",
                  }}>Accent Color</label>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <input
                      id="banner-accent-color"
                      type="color"
                      value={banner.accentColor}
                      onChange={(e) => handleChange("accentColor", e.target.value)}
                      style={{
                        width: 38, height: 38,
                        border: "none",
                        borderRadius: "8px",
                        cursor: "pointer",
                        background: "none",
                        padding: 2,
                      }}
                    />
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {banner.accentColor}
                    </span>
                  </div>
                </div>
              </div>

              {/* Save button */}
              <button
                id="banner-save-btn"
                onClick={handleSave}
                className="btn btn-primary"
                style={{ marginTop: "0.5rem", alignSelf: "flex-start" }}
              >
                {saved ? "✅ Saved!" : "💾 Save Banner"}
              </button>
            </div>

            {/* RIGHT — live preview */}
            <div>
              <p style={{
                fontSize: "0.78rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: "0.75rem",
              }}>Live Preview</p>

              {/* Mini video mockup with banner */}
              <div style={{
                borderRadius: "12px",
                overflow: "hidden",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-md)",
                background: "#000",
                aspectRatio: "16/9",
                position: "relative",
              }}>
                {/* fake video content */}
                <div style={{
                  width: "100%",
                  height: "100%",
                  background: "linear-gradient(135deg,#0d0d1a 0%, #1a1a35 50%, #0d0d1a 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}>
                  <div style={{ textAlign: "center", opacity: 0.3 }}>
                    <div style={{ fontSize: "2rem" }}>🎬</div>
                    <p style={{ fontSize: "0.65rem", color: "#fff", marginTop: "0.3rem" }}>Video Preview</p>
                  </div>
                </div>

                {/* The actual banner overlay */}
                <div style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  background: brandPrimary,
                  padding: "0.5rem 0.75rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "0.5rem",
                }}>
                  {/* Left: company name */}
                  <div style={{
                    fontFamily: "var(--font-head)",
                    fontWeight: 700,
                    fontSize: "0.7rem",
                    color: "#fff",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}>
                    {banner.companyName || "Company Name"}
                  </div>

                  {/* Center: contact info */}
                  <div style={{
                    display: "flex",
                    gap: "0.75rem",
                    fontSize: "0.55rem",
                    color: "rgba(255,255,255,0.8)",
                    flexWrap: "nowrap",
                    overflow: "hidden",
                  }}>
                    {banner.phone && (
                      <span style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}>
                        📞 {banner.phone}
                      </span>
                    )}
                    {banner.address && (
                      <span style={{ display: "flex", alignItems: "center", gap: "0.2rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "120px" }}>
                        📍 {banner.address}
                      </span>
                    )}
                  </div>

                  {/* Right: website pill */}
                  <div style={{
                    background: brandAccent,
                    borderRadius: "999px",
                    padding: "0.2rem 0.5rem",
                    fontSize: "0.55rem",
                    fontWeight: 700,
                    color: "#fff",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}>
                    {banner.website || scraped.business_name}
                  </div>
                </div>
              </div>

              {/* Banner description */}
              <p style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginTop: "0.75rem",
                lineHeight: 1.5,
              }}>
                This banner will appear at the bottom of your video with your company contact information.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Reusable field ────────────────────────────────────────────────────────────
function Field({
  label, id, value, placeholder, onChange,
}: {
  label: string;
  id: string;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="input-wrap">
      <label htmlFor={id} className="label" style={{ textTransform: "uppercase", letterSpacing: "0.07em", fontSize: "0.75rem" }}>
        {label}
      </label>
      <input
        id={id}
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
