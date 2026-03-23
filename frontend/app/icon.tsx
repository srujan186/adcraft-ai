// app/icon.tsx — Custom browser tab icon (replaces default Vercel favicon)
// Next.js 14 supports generating favicons via this file
import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 32,
          height: 32,
          background: "linear-gradient(135deg, #0a0a12 0%, #12121e 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 6,
        }}
      >
        {/* Lightning bolt ⚡ in purple gradient */}
        <svg width="20" height="22" viewBox="0 0 20 22" fill="none">
          <path
            d="M12 2L3 13H10L8 20L17 9H10L12 2Z"
            fill="url(#grad)"
            stroke="none"
          />
          <defs>
            <linearGradient id="grad" x1="3" y1="2" x2="17" y2="20" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#6c63ff" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    ),
    { ...size }
  );
}
