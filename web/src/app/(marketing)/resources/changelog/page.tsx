import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Changelog — AdCraft AI",
  description: "What has shipped in AdCraft AI, most recent first.",
};

// Derived from the project's git history. Add an entry when you ship something.

type Entry = { date: string; title: string; items: string[] };

const ENTRIES: Entry[] = [
  {
    date: "September 2026",
    title: "Site redesign, and navigation",
    items: [
      "Rebuilt the frontend around a light design system with a new landing page.",
      "Added Product, Industries and Resources navigation, with dedicated pages behind each entry.",
      "Added a help centre, this changelog, and an API reference written against the real endpoints.",
      "Corrected the advertised output resolution — the pipeline renders 720p, not 1080p.",
    ],
  },
  {
    date: "April 2026",
    title: "Video editor",
    items: [
      "Added a full-screen editor with tabs for text, voiceover, music, colours and the contact banner.",
      "Added a timeline view showing the banner, music, voice and video layers.",
      "Added the bottom banner editor to the result page, with a live preview.",
    ],
  },
  {
    date: "March 2026",
    title: "Deployment and bug fixes",
    items: [
      "Added Hugging Face Space configuration and a root Dockerfile.",
      "Fixed invalid URL generation across the frontend and backend.",
      "Removed a broken secret reference from the Vercel configuration.",
    ],
  },
  {
    date: "March 2026",
    title: "Audio pipeline",
    items: [
      "Stitched narration and music into the rendered video output.",
      "Added Kokoro text-to-speech narration and royalty-free background music beds.",
      "Mixed the music bed underneath narration so the voice stays legible.",
    ],
  },
  {
    date: "March 2026",
    title: "Video generation",
    items: [
      "Added screenshot capture — three viewport captures per site, assembled into a background video.",
      "Added the FFmpeg assembly layer that composites overlay, headline, subtext, call to action and logo.",
      "Integrated the frontend with the generation pipeline end to end.",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <>
      <section className="page-hero">
        <div className="container container-narrow">
          <span className="eyebrow">Changelog</span>
          <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.4rem)" }}>
            What&apos;s shipped
          </h1>
          <p className="lead" style={{ marginTop: "1rem" }}>
            AdCraft is in active development. Most recent first.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container container-narrow">
          <div className="timeline">
            {ENTRIES.map((e, i) => (
              <div className="timeline-entry" key={i}>
                <div className="timeline-marker" aria-hidden="true" />
                <div className="timeline-body">
                  <p className="timeline-date">{e.date}</p>
                  <p className="feature-title" style={{ marginBottom: "0.6rem" }}>{e.title}</p>
                  <ul className="timeline-list">
                    {e.items.map((it) => <li key={it}>{it}</li>)}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
