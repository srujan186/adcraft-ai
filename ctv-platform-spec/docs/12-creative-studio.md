# 12 — Creatives, review & AI Studio

## Upload
Dropzone (drag & drop, multiple). Flow: `POST /creatives/upload-url` → browser PUT to S3 → `POST /creatives`.
Worker job `process_creative`: ffprobe (duration, resolution, codec) → reject if < 5s or > 90s or > 500MB →
transcode to 1920x1080 H.264 High, 30fps, AAC 48kHz, letterbox if not 16:9 (vertical videos get blurred-background
pillarbox — "repurpose social assets") → thumbnail at 1s → status `processing` → automated review.

## Automated review ("ACR-style" checks)
Checks: black frames > 2s at start/end, silence > 50% (warn), loudness outside −24±2 LUFS (auto-normalize with
ffmpeg `loudnorm`), resolution after transcode, policy keyword scan of the advertiser website/name against
`playbook.restricted_categories` → `needs_changes` + manual review queue (admin page `/admin/reviews`, simple list with
approve/reject + note). Passing → `approved`. Rejected creatives block campaigns that only use them.

## Studio — "Generate a creative" (`/dashboard/library/studio` and sheet inside the wizard)
Input tabs: **Website URL** ("Type your business URL and we'll turn it into a TV ad") or **Business name**
(local business; free-text name + city). Options: length 15s/30s, tone (Energetic, Premium, Friendly, Informative),
voice (from TTSProvider list), music on/off, CTA text, show QR code toggle (QR → URL with UTM).
Pipeline (`services/studio/`, worker job, target < 2 min):
1. Scrape URL (httpx + selectolax): title, meta description, og:image, logo (favicon/apple-touch/og), top 6 images ≥ 600px,
   brand colors (dominant colors of logo via Pillow quantize), price/offer text.
2. LLM → JSON script: `{headline, scenes:[{duration_s, image_ref, caption, voiceover}], cta, end_card}` with total = length.
3. TTS per scene (or silent + captions fallback).
4. Render with ffmpeg filtergraph (or Remotion if Node render preferred): Ken-Burns pan on images, caption lower-third in
   brand color, logo bug top-right, end card with logo + CTA + optional QR, background music bed from `/assets/music/*`
   (royalty-free files you generate or leave silent), audio ducking under voiceover.
5. Save as creative (`source='studio'`) → normal review pipeline. Studio page shows preview player, "Regenerate scene",
   edit captions/voiceover text then re-render.

## Library
Labels (many-to-many as text[]), filters, preview dialog (HTML5 video), edit (rename, labels), archive.
A/B: in a strategy, if `ab_test` true, creatives get equal traffic and the creative report shows significance
(two-proportion z-test on visit rate).
