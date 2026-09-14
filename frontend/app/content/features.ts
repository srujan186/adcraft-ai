import type { MarketingContent } from "./types";

// Descriptions here mirror what the backend genuinely does. If the pipeline
// changes, update these too — they are product claims, not marketing filler.

export const FEATURES: MarketingContent[] = [
  {
    slug: "brand-scraping",
    eyebrow: "Feature",
    title: "Brand scraping",
    lead: "We read your site the way a designer would — logo, palette, positioning.",
    metaDescription:
      "AdCraft extracts your logo, brand colours, tagline and description directly from your live website.",
    intro:
      "Give it a URL and the scraper does a two-pass read. A fast HTTP fetch handles most sites; if the result looks thin — because the page renders client-side or blocks bots — it escalates to a real headless browser and tries again, keeping whichever pass produced better data.",
    points: [
      {
        title: "Colours from six sources",
        desc: "theme-color and tile-color meta tags, inline styles, CSS custom properties, the most frequent non-neutral hex values in the markup, and finally external stylesheets.",
      },
      {
        title: "Logos, scored not guessed",
        desc: "Candidates come from og:image, apple-touch-icons, favicons, marked-up img tags and SVGs, each scored by likely quality — and hero or banner images are actively rejected.",
      },
      {
        title: "It degrades gracefully",
        desc: "If a site cannot be read at all, you get a clear message and can supply the details yourself rather than a crash.",
      },
    ],
  },
  {
    slug: "ai-script",
    eyebrow: "Feature",
    title: "AI script writing",
    lead: "GPT-OSS 120B writes to your brand, your style and your exact ad length.",
    metaDescription:
      "Generate structured ad scripts — headline, subtext, call to action and voiceover — with GPT-OSS 120B via Groq.",
    intro:
      "The script model receives your scraped brand data along with the style and duration you chose, and returns a structured script rather than a paragraph. Each field maps to something the renderer uses, which is why the output is consistent enough to drop straight into a video.",
    points: [
      {
        title: "Structured, not freeform",
        desc: "Headline, subtext, call to action, full voiceover, music style, scene description, colour mood and key message all come back as separate fields.",
      },
      {
        title: "Written to length",
        desc: "The target duration is part of the prompt, so a fifteen-second script is genuinely shorter rather than truncated afterwards.",
      },
      {
        title: "Every field editable",
        desc: "Nothing is locked. The whole script is shown on the result page and can be rewritten in the editor.",
      },
    ],
  },
  {
    slug: "voiceover-music",
    eyebrow: "Feature",
    title: "Voiceover & music",
    lead: "Kokoro narration over a licensed music bed, mixed and levelled automatically.",
    metaDescription:
      "Every AdCraft ad is narrated by a natural-sounding voice and scored with a royalty-free music bed.",
    intro:
      "Narration is synthesised locally with the Kokoro model — no per-render API cost and no usage cap. The music bed is chosen from the mood the script model picked, looped or trimmed to your ad length, faded at both ends, and mixed underneath the voice so narration stays legible.",
    points: [
      {
        title: "Four voices",
        desc: "Warm, professional, male and British English narration ship with the model.",
      },
      {
        title: "Music matched to the script",
        desc: "The script model picks a mood, and a matching royalty-free track is selected, looped to length and faded in and out.",
      },
      {
        title: "Mixed for legibility",
        desc: "The bed is dropped to roughly fifteen percent under full-volume narration, so the voice always sits on top.",
      },
    ],
  },
  {
    slug: "video-editor",
    eyebrow: "Feature",
    title: "Video editor",
    lead: "Adjust the text, voice, music, colours and end card after the first render.",
    metaDescription:
      "Refine your generated ad in a full-screen editor — headline, script, music, brand colours and closing contact card.",
    intro:
      "The first render is a starting point. The editor opens full-screen over the result page with tabs for text, voiceover, music, colours and the end card, alongside a live preview of the video and a timeline view of the layers that make it up.",
    points: [
      {
        title: "Every text field",
        desc: "Headline, subtext, call to action and the complete voiceover script are all editable.",
      },
      {
        title: "Brand colours",
        desc: "Primary and accent colours can be overridden with colour pickers if the scraper picked the wrong ones.",
      },
      {
        title: "Contact end card",
        desc: "Add a company name, phone number, email, address and website to a card that closes the ad, under your logo and brand colour.",
      },
    ],
  },
  {
    slug: "ad-styles",
    eyebrow: "Feature",
    title: "Ad styles",
    lead: "Four tones that genuinely change the writing, not just the colours.",
    metaDescription:
      "Choose between Modern, Bold, Minimal and Playful ad styles — each changes the script, pacing and music.",
    intro:
      "Style is part of the prompt, so it changes what the model writes rather than being a filter applied afterwards. The same business run through all four produces four different scripts, with different sentence lengths, different energy and a different music mood.",
    points: [
      { title: "Modern", desc: "Clean, professional and confident. A safe default for most businesses." },
      { title: "Bold & Playful", desc: "Bold runs high energy and punchy; Playful stays fun, friendly and approachable." },
      { title: "Minimal", desc: "Simple and elegant, built around one big idea rather than a list of features." },
    ],
  },
  {
    slug: "api",
    eyebrow: "Feature",
    title: "Integrations & API",
    lead: "Everything the web app does is available over plain HTTP.",
    metaDescription:
      "Generate ads programmatically with the AdCraft HTTP API — scripts, full videos, and file download.",
    intro:
      "The frontend is just a client. The same JSON endpoints it calls are available to you directly, so ads can be generated from a script, a scheduled job or another service. There are no SDKs to install — it is JSON over HTTP.",
    points: [
      { title: "Script or full video", desc: "Generate just the script for review, or run the whole pipeline through to a rendered MP4." },
      { title: "Plain JSON", desc: "POST a URL, a style and a duration; get back a video URL, a render id and the full script." },
      { title: "Documented from the source", desc: "The reference is written against the actual route handlers, not a spec that drifts." },
    ],
  },
];
