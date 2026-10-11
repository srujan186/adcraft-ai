import type { MarketingContent } from "./types";

export const SOLUTIONS: MarketingContent[] = [
  {
    slug: "launch-fast",
    eyebrow: "Solution",
    title: "Launch a campaign fast",
    lead: "From URL to finished MP4 in under a minute, with nothing to install.",
    metaDescription:
      "Go from a business URL to a finished, narrated video ad in under a minute with AdCraft AI.",
    intro:
      "The slowest part of most campaigns is waiting on creative. AdCraft removes that step: paste the URL, choose a style and a length, and the pipeline scrapes the site, writes the script, records the voiceover, scores it and renders the video in one pass.",
    points: [
      { title: "No brief, no shoot", desc: "The source material is your existing website, so there is nothing to write or film up front." },
      { title: "One pass, one file", desc: "Scrape, script, narrate, score and render all happen in a single request that returns a downloadable MP4." },
      { title: "Change your mind cheaply", desc: "Not right? Change the style and run it again — there is no cost to a second attempt." },
    ],
    suggested: { style: "Modern", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "brand-awareness",
    eyebrow: "Solution",
    title: "Build brand awareness",
    lead: "Consistent, on-brand video that actually looks like you.",
    metaDescription:
      "Produce on-brand video ads that reuse your real logo, colours and messaging, extracted straight from your site.",
    intro:
      "Awareness work only compounds when it looks consistent. Because branding is read from your live site — the palette from your stylesheet, the logo from your markup, the positioning from your meta tags — every ad comes out recognisably yours without anyone maintaining a template.",
    points: [
      { title: "Colours from your CSS", desc: "The scraper reads theme-color tags, CSS custom properties and the most frequent non-neutral colours in your markup." },
      { title: "Your logo, not a placeholder", desc: "Logos are found through several strategies and scored, with banner and hero images actively rejected." },
      { title: "Repeatable", desc: "Run the same settings across pages or locations and the output stays visually consistent." },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Inspirational" },
  },
  {
    slug: "refresh-creative",
    eyebrow: "Solution",
    title: "Refresh old creative",
    lead: "Regenerate a tired ad instead of rebuilding it.",
    metaDescription:
      "Refresh stale video creative in under a minute by regenerating it with a new style, length or script.",
    intro:
      "Creative fatigue is a scheduling problem more than a craft problem — the ad still works, it has just been seen too often. Regenerating with a different style produces a genuinely different script, pacing and score from the same source page, so you can rotate without briefing anything new.",
    points: [
      { title: "Four distinct styles", desc: "Modern, Bold, Minimal and Playful each change the script, sentence length and pacing, not just the colours." },
      { title: "Same source, new cut", desc: "Point at the same URL and the pipeline writes a fresh script rather than reusing the previous one." },
      { title: "Edit rather than restart", desc: "If only the wording is stale, rewrite the headline and voiceover in the editor." },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "test-variations",
    eyebrow: "Solution",
    title: "Test ad variations",
    lead: "Generate several versions of the same idea and compare them.",
    metaDescription:
      "Create multiple video ad variations from one URL to compare styles, lengths and messaging.",
    intro:
      "Because generation is fast and free during the beta, producing four variants costs about as much as producing one. Run the same page through each style, or the same style at both lengths, and compare them before spending anything on distribution.",
    points: [
      { title: "Eight combinations out of the box", desc: "Four styles times two lengths, all from one URL, with no additional setup." },
      { title: "Isolate one variable", desc: "Hold the style and change only the headline in the editor to test messaging on its own." },
      { title: "Nothing to clean up", desc: "Each render is a separate file with its own id, so discarded variants do not overwrite anything." },
    ],
    suggested: { style: "Modern", duration: "15 seconds", music: "Corporate" },
  },
  {
    slug: "promote-product",
    eyebrow: "Solution",
    title: "Promote a product",
    lead: "Point it at the product page and let the page do the talking.",
    metaDescription:
      "Turn any product page into a narrated video ad that leads with the offer and closes on a call to action.",
    intro:
      "A good product page already contains the argument: what it is, who it is for, why it is worth the money. AdCraft reads that page and compresses the argument into a spoken script, ending on a call-to-action button rendered in your own brand colour.",
    points: [
      { title: "Starts from your own copy", desc: "Headline and description come from the page's meta tags and hero content, not from a generic template." },
      { title: "Closes on an action", desc: "Every script ends with a call to action, rendered as a button in your primary brand colour." },
      { title: "One ad per product", desc: "Point it at each product page in turn to build out a catalogue of ads." },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "announce-offer",
    eyebrow: "Solution",
    title: "Announce an offer",
    lead: "Get a time-sensitive promotion on screen while it is still running.",
    metaDescription:
      "Announce sales, promotions and limited offers with a video ad generated in under a minute.",
    intro:
      "Offers have a deadline, and creative turnaround is usually what eats into it. A fifteen-second Bold spot with an upbeat bed is enough to carry a discount or a limited run, and it can be produced and downloaded the same hour the offer is signed off.",
    points: [
      { title: "Same-day turnaround", desc: "Generation takes under a minute, so the ad is ready long before the offer expires." },
      { title: "Urgency in the script", desc: "Bold scripts favour short, direct sentences, which suits a deadline-driven message." },
      { title: "Terms on the end card", desc: "Use the closing card for dates, conditions or a promotional code." },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "localize",
    eyebrow: "Solution",
    title: "Localise for a market",
    lead: "Different sites, different voices, one consistent look.",
    metaDescription:
      "Produce localised video ads for regional sites, with a choice of narration voices and per-market branding.",
    intro:
      "If you run separate sites or landing pages per market, each one can be scraped independently — so regional pricing, wording and imagery all carry through. Narration currently offers four English voices, including a British option, with the voice set in the TTS layer.",
    points: [
      { title: "Per-market source pages", desc: "Point at each regional URL and the branding and copy for that market are used." },
      { title: "Four narration voices", desc: "Warm, professional, male and British English voices ship with the Kokoro model." },
      { title: "Consistent framing", desc: "Keep the style and length fixed across markets so the campaign stays recognisable." },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Corporate" },
  },
];
