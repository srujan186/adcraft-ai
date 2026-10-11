/** Single source of truth for navigation (docs/04-frontend-spec.md). */

export interface NavItem {
  label: string;
  href: string;
  badge?: string;
}

export const TOP_NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Campaigns", href: "/dashboard/campaigns" },
  { label: "Audiences", href: "/dashboard/audiences" },
  { label: "Library", href: "/dashboard/library" },
  { label: "Reports", href: "/dashboard/reports" },
  { label: "Insights", href: "/dashboard/insights/overview", badge: "New" },
];

export interface SettingsGroup {
  group: string;
  items: NavItem[];
}

export const SETTINGS_NAV: SettingsGroup[] = [
  {
    group: "Account",
    items: [
      { label: "General", href: "/dashboard/settings/general" },
      { label: "Members", href: "/dashboard/settings/members" },
      { label: "Advertisers", href: "/dashboard/settings/advertisers" },
    ],
  },
  {
    group: "Integrations",
    items: [
      { label: "Marketplace", href: "/dashboard/settings/integrations-marketplace" },
      { label: "Installed integrations", href: "/dashboard/settings/integrations-installed" },
    ],
  },
  {
    group: "Tracking",
    items: [
      { label: "Web Pixel", href: "/dashboard/settings/tracking/web" },
      { label: "App Tracking", href: "/dashboard/settings/tracking/app" },
    ],
  },
  {
    group: "Billing",
    items: [
      { label: "Balance & transactions", href: "/dashboard/settings/billing/balance" },
      { label: "Payment methods", href: "/dashboard/settings/billing/payment-methods" },
      { label: "Invoices", href: "/dashboard/settings/billing/invoices" },
      { label: "Receipts", href: "/dashboard/settings/billing/receipts" },
      { label: "Coupons", href: "/dashboard/settings/billing/coupons" },
      { label: "Refer & earn", href: "/dashboard/settings/billing/refer" },
    ],
  },
  {
    group: "Developers",
    items: [
      { label: "My applications", href: "/dashboard/settings/developers/applications" },
      { label: "API keys", href: "/dashboard/settings/developers/api-keys" },
    ],
  },
];
