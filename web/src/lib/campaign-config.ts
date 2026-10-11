export interface KpiOption {
  value: string;
  label: string;
  desc: string;
  ratio?: boolean; // ROAS uses a ratio target, not currency
}

export interface GoalDef {
  value: string;
  group: "Performance" | "Specialized";
  label: string;
  description: string;
  kpis: KpiOption[];
}

export const GOALS: GoalDef[] = [
  {
    value: "awareness", group: "Performance", label: "Awareness",
    description: "Maximize reach across streaming households.",
    kpis: [
      { value: "cpm", label: "CPM", desc: "Cost per 1,000 impressions" },
      { value: "cost_per_household", label: "Cost per household", desc: "Cost to reach one household" },
    ],
  },
  {
    value: "traffic", group: "Performance", label: "Traffic",
    description: "Drive visits to your website.",
    kpis: [
      { value: "cps", label: "Cost per session", desc: "Cost per site session" },
      { value: "cpv", label: "Cost per visit", desc: "Cost per visit" },
    ],
  },
  {
    value: "leads", group: "Performance", label: "Leads",
    description: "Generate leads from your site.",
    kpis: [{ value: "cpl", label: "Cost per lead", desc: "Cost per lead captured" }],
  },
  {
    value: "sales", group: "Performance", label: "Sales",
    description: "Increase your sales.",
    kpis: [
      { value: "cpp", label: "Cost per purchase", desc: "Completed orders on your site" },
      { value: "roas", label: "ROAS", desc: "Revenue per dollar spent", ratio: true },
    ],
  },
  {
    value: "retargeting", group: "Specialized", label: "Retargeting",
    description: "Re-engage people who visited your site.",
    kpis: [
      { value: "cps", label: "Cost per session", desc: "Cost per returning session" },
      { value: "cpp", label: "Cost per purchase", desc: "Completed orders" },
      { value: "roas", label: "ROAS", desc: "Revenue per dollar spent", ratio: true },
    ],
  },
  {
    value: "app_promotion", group: "Specialized", label: "App Promotion",
    description: "Drive app installs & in-app revenue.",
    kpis: [
      { value: "cpi", label: "Cost per install", desc: "Cost per app install" },
      { value: "roas", label: "ROAS", desc: "In-app revenue per dollar", ratio: true },
    ],
  },
  {
    value: "abm", group: "Specialized", label: "ABM",
    description: "Reach a list of target companies.",
    kpis: [
      { value: "cost_per_account", label: "Cost per reached account", desc: "Cost per company reached" },
      { value: "cpl", label: "Cost per lead", desc: "Cost per lead" },
    ],
  },
];

export const goalDef = (value: string) => GOALS.find((g) => g.value === value);
