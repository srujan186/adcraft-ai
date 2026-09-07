import type { IconName } from "./nav-data";

// Simple 24x24 stroke icons, sized by font-size at the call site.
const PATHS: Record<IconName, React.ReactNode> = {
  zap:       <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />,
  megaphone: <><path d="M4 9v6h3l6 4V5L7 9H4z" /><path d="M17 9a3.5 3.5 0 0 1 0 6" /></>,
  refresh:   <><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 4v5h-5" /></>,
  layers:    <><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></>,
  tag:       <><path d="M20.6 13.4L13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z" /><circle cx="7.5" cy="7.5" r="1.5" /></>,
  percent:   <><path d="M19 5L5 19" /><circle cx="7.5" cy="7.5" r="2.5" /><circle cx="16.5" cy="16.5" r="2.5" /></>,
  globe:     <><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18z" /></>,
  scan:      <><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></>,
  pen:       <><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" /></>,
  mic:       <><path d="M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3z" /><path d="M19 11a7 7 0 0 1-14 0" /><path d="M12 18v3" /></>,
  film:      <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 4v16" /><path d="M17 4v16" /><path d="M3 12h18" /></>,
  sparkles:  <path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z" />,
  plug:      <><path d="M9 3v6" /><path d="M15 3v6" /><path d="M6 9h12v3a6 6 0 0 1-12 0V9z" /><path d="M12 18v3" /></>,
};

export default function NavIcon({ name }: { name: IconName }) {
  return (
    <svg
      className="mega-link-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
