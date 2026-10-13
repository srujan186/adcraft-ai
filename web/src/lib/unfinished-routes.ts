/**
 * Settings screens not built yet (fix plan P0-6). Unless NEXT_PUBLIC_SHOW_UNFINISHED=1 they are
 * left out of navigation (components/app/nav-data.ts) and answer a real HTTP 404 (next.config.ts).
 * Plain module, no path aliases: next.config imports it.
 */
export const UNFINISHED_ROUTES = [
  "/dashboard/settings/integrations-marketplace",
  "/dashboard/settings/integrations-installed",
  "/dashboard/settings/billing/invoices",
  "/dashboard/settings/billing/receipts",
  "/dashboard/settings/billing/refer",
  "/dashboard/settings/developers/applications",
];
