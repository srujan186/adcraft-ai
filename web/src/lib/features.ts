/**
 * Screens that aren't built yet stay out of the product — hidden from navigation and 404 at
 * their URLs — unless explicitly enabled (NEXT_PUBLIC_SHOW_UNFINISHED=1, e.g. on a staging
 * preview). Clients must never land on a "building in…" page.
 */
export const SHOW_UNFINISHED = process.env.NEXT_PUBLIC_SHOW_UNFINISHED === "1";
