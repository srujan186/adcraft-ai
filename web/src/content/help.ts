export interface Article {
  slug: string;
  title: string;
  category: "Billing" | "Measurement" | "Tracking" | "Basics" | "Audiences" | "Creative";
  readMins: number;
  body: string; // markdown-lite: ## headings, paragraphs, - lists, **bold**
}

export const ARTICLES: Article[] = [
  {
    slug: "how-ctv-advertising-works", title: "How streaming-TV advertising works", category: "Basics", readMins: 1,
    body: "Your video ad runs between shows on 500+ streaming apps, shown only to the households in the places and interests you pick.\n\n## Why there are no clicks\nNobody clicks a TV ad. Instead, results show up as **visits and sales** on your site over the following days — matched to the households that saw your ad by IP.\n\n## What to expect\n- Reach is measured in households, not clicks\n- Conversions arrive with a lag (people act later)\n- You pay on a CPM (cost per 1,000 impressions) basis",
  },
  {
    slug: "how-billing-works", title: "How billing works", category: "Billing", readMins: 1,
    body: "AdCraft AI uses a **prepaid balance**.\n\n## Topping up\nAdd funds from Settings → Balance & transactions. In test mode no real card is charged.\n\n## How spend is debited\nAs your campaigns deliver, spend is debited from your balance. When your balance hits zero, campaigns pause automatically.",
  },
  {
    slug: "measurement-and-attribution", title: "Measurement & attribution", category: "Measurement", readMins: 2,
    body: "We credit a conversion to the **last ad impression** a household saw before converting, within your attribution window.\n\n## Choosing an attribution window\n- Traffic/Awareness: shorter windows are fine\n- Sales/Leads: use 7–30 days, since people convert days after seeing a TV ad\n\n## Metrics\n- **ROAS** = revenue ÷ spend\n- **CPS/CPL/CPP** = spend ÷ conversions\n- **Households** = unique households reached",
  },
  {
    slug: "set-up-your-pixel", title: "Set up your pixel", category: "Tracking", readMins: 1,
    body: "The pixel measures the visits and sales your ads drive.\n\n## Install\nGo to Settings → Web Pixel, pick your install method, and paste the snippet before </head> on every page.\n\n## Verify\nVisit your site (or the demo store) and watch the events turn green in the Verify step. Sales campaigns need **Page View** and **Purchase** events.",
  },
  {
    slug: "audiences-explained", title: "Audiences: warm vs. cold", category: "Audiences", readMins: 2,
    body: "## Warm audiences (retargeting)\nYour Visitors, Leads and Purchasers web audiences are your highest-intent viewers — great for Sales goals.\n\n## Cold audiences (prospecting)\nInterests, demographics and lookalikes help you reach new customers.\n\n## One tip\nKeep warm and cold in **separate strategies** so each has its own budget and reporting.",
  },
  {
    slug: "setting-your-budget", title: "Setting your budget", category: "Basics", readMins: 1,
    body: "The minimum is **$50/day** per strategy.\n\n## The estimate panel\nAs you set targeting, the Strategy Estimate shows your audience size and a deliverability forecast. If it says **Insufficient**, broaden your targeting so the budget can actually be spent.\n\n## Scaling\nOnce a strategy has a week of delivery, the Performance Forecaster recommends a budget that grows results efficiently.",
  },
];

export const bySlug = (slug: string) => ARTICLES.find((a) => a.slug === slug);
