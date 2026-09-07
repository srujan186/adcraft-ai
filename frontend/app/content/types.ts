// Shared shape for every generated marketing page (industries, solutions, features).
//
// Copy rule for this whole directory: describe only what the product actually does.
// No invented statistics, customer counts, ROAS figures or testimonials.

export type MarketingContent = {
  slug: string;
  /** Small uppercase label above the title, e.g. "Industry". */
  eyebrow: string;
  title: string;
  /** One-sentence summary under the title. */
  lead: string;
  /** <meta name="description"> for this page. */
  metaDescription: string;
  /** Opening paragraph of the body. */
  intro: string;
  /** Three supporting cards. */
  points: { title: string; desc: string }[];
  /** Honest setup guidance — a suggestion, not a performance claim. */
  suggested?: { style: string; duration: string; music: string };
};

export function findBySlug<T extends { slug: string }>(
  items: T[],
  slug: string
): T | undefined {
  return items.find((i) => i.slug === slug);
}
