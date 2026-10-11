import type { MarketingContent } from "./types";

export const INDUSTRIES: MarketingContent[] = [
  {
    slug: "ecommerce",
    eyebrow: "Industry",
    title: "Video ads for e-commerce",
    lead: "Turn a product page into a scroll-stopping video ad without a studio, a shoot, or an editor.",
    metaDescription:
      "Generate video ads for your online store from your existing product pages. AdCraft reads your site's branding and writes, narrates and renders the ad.",
    intro:
      "Online stores already have everything an ad needs — product photography, a clear offer, a recognisable palette. AdCraft reads your storefront directly, pulls the brand colours and logo out of the page, and builds a short ad around what it finds. You pick the tone and the length; everything else comes from the site you already run.",
    points: [
      {
        title: "Built from your storefront",
        desc: "Screenshots of your live pages become the backdrop, so the ad looks like your shop rather than generic stock footage.",
      },
      {
        title: "Offer-led scripting",
        desc: "The script generator leads with your value proposition and closes on a call to action you can edit before export.",
      },
      {
        title: "Fast enough to iterate",
        desc: "A render takes well under a minute, so you can try several styles against the same product and compare them side by side.",
      },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "restaurants",
    eyebrow: "Industry",
    title: "Video ads for restaurants & food",
    lead: "Show the room, the menu and the atmosphere in fifteen seconds.",
    metaDescription:
      "Create short video ads for your restaurant, café or food business straight from your website — no filming or editing required.",
    intro:
      "Restaurant sites tend to be visual already: hero imagery, a menu, an address. AdCraft captures those pages, lifts the palette from your CSS, and writes a warm, spoken script over the top. It works just as well for a single café as for a group with several locations.",
    points: [
      {
        title: "Atmosphere first",
        desc: "Screenshots of your own site carry the mood of the place — the room, the plating, the type — instead of stock imagery of someone else's kitchen.",
      },
      {
        title: "A voice, not a caption",
        desc: "Every ad is narrated by a natural-sounding voice, so it still lands for people watching with sound on.",
      },
      {
        title: "Contact details on screen",
        desc: "The end card editor closes the ad with your phone number, address and website.",
      },
    ],
    suggested: { style: "Playful", duration: "30 seconds", music: "Upbeat" },
  },
  {
    slug: "fitness",
    eyebrow: "Industry",
    title: "Video ads for fitness & wellness",
    lead: "High-energy ads for gyms, studios and trainers, generated from your class timetable page.",
    metaDescription:
      "Generate energetic video ads for your gym, studio or wellness practice from your existing website.",
    intro:
      "Fitness marketing lives or dies on energy. The Bold style pairs a punchy, short-sentence script with an upbeat music bed and quick cuts between screenshots of your site — enough momentum to work as a paid social placement without a videographer.",
    points: [
      {
        title: "Pace that matches the pitch",
        desc: "Bold scripts run shorter sentences and a faster delivery, which suits a fifteen-second class or membership promo.",
      },
      {
        title: "Your branding, not a template",
        desc: "Colours are extracted from your live stylesheet, so the ad matches the identity members already recognise.",
      },
      {
        title: "Rewrite before you publish",
        desc: "Headline, subtext, call to action and the full voiceover script are all editable after the first render.",
      },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "healthcare",
    eyebrow: "Industry",
    title: "Video ads for healthcare",
    lead: "Calm, credible ads for clinics and practices — measured in tone, quick to produce.",
    metaDescription:
      "Produce clear, professional video ads for your clinic or healthcare practice directly from your website.",
    intro:
      "Healthcare marketing needs restraint. The Modern and Minimal styles keep the script factual and the pacing unhurried, which suits a practice introducing a service or a new location. Because you can edit every line of the script before export, nothing goes out that you have not read.",
    points: [
      {
        title: "Measured tone by default",
        desc: "Modern and Minimal produce calm, declarative copy rather than hard-sell language.",
      },
      {
        title: "Full script review",
        desc: "The voiceover is shown in full and stays editable, so wording can be checked before anything is published.",
      },
      {
        title: "Consistent across locations",
        desc: "Run the same settings against each site to keep a group of practices visually consistent.",
      },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Corporate" },
  },
  {
    slug: "real-estate",
    eyebrow: "Industry",
    title: "Video ads for real estate",
    lead: "Turn a listing or agency site into a polished thirty-second spot.",
    metaDescription:
      "Create professional video ads for property listings and estate agencies from your existing website.",
    intro:
      "Property marketing is repetitive by nature — many listings, same brand, constant turnover. AdCraft reads whichever page you point it at and produces a consistent, on-brand ad each time, which makes it practical to give individual listings their own video.",
    points: [
      {
        title: "One brand, many listings",
        desc: "Because branding is read from the page, every ad in a portfolio comes out visually consistent.",
      },
      {
        title: "Thirty seconds of room",
        desc: "The longer format gives the script space to cover location, features and a closing call to action.",
      },
      {
        title: "Agent details on screen",
        desc: "Add a contact number and website to the end card so enquiries have somewhere to land.",
      },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Inspirational" },
  },
  {
    slug: "saas",
    eyebrow: "Industry",
    title: "Video ads for SaaS & tech",
    lead: "Explain the product in one clear idea, straight from your marketing site.",
    metaDescription:
      "Generate clean, minimal video ads for your software product using the copy and branding already on your site.",
    intro:
      "SaaS landing pages are usually the most carefully written thing a company owns. AdCraft reads that page — the meta description, the hero heading, the palette — and compresses it into a single spoken idea. The Minimal style works well here: one message, cleanly delivered, no clutter.",
    points: [
      {
        title: "One idea per ad",
        desc: "Minimal scripts are built around a single core message rather than a feature list.",
      },
      {
        title: "Reads your positioning",
        desc: "The scraper picks up your existing headline and meta description, so the ad starts from copy you already approved.",
      },
      {
        title: "Test the framing",
        desc: "Generate the same page in several styles to compare how different framings sound before committing.",
      },
    ],
    suggested: { style: "Minimal", duration: "15 seconds", music: "Corporate" },
  },
  {
    slug: "automotive",
    eyebrow: "Industry",
    title: "Video ads for automotive",
    lead: "Dealership and service ads with weight behind them.",
    metaDescription:
      "Create bold video ads for dealerships, garages and automotive services from your existing website.",
    intro:
      "Automotive advertising tends to want scale and confidence. The Bold style with a dramatic music bed gives a thirty-second spot enough presence for a seasonal promotion or a new-stock announcement, built from your own site rather than generic footage.",
    points: [
      {
        title: "Presence without a shoot",
        desc: "A dramatic score under a bold script carries a promotion that would otherwise need production budget.",
      },
      {
        title: "Turn promotions round quickly",
        desc: "Because a render takes under a minute, seasonal offers can go out while they are still current.",
      },
      {
        title: "Location details included",
        desc: "The end card editor puts your address and phone number on the closing frames.",
      },
    ],
    suggested: { style: "Bold", duration: "30 seconds", music: "Dramatic" },
  },
  {
    slug: "education",
    eyebrow: "Industry",
    title: "Video ads for education",
    lead: "Course and enrolment ads that sound like an institution, not an infomercial.",
    metaDescription:
      "Produce clear, credible video ads for schools, courses and training providers from your website.",
    intro:
      "Education marketing has to feel trustworthy before it feels exciting. The Modern style keeps the script informative and the delivery even, which suits enrolment periods, open days and individual course pages.",
    points: [
      {
        title: "Informative by default",
        desc: "Modern scripts explain rather than exclaim, which is the right register for prospective students and parents.",
      },
      {
        title: "A page per course",
        desc: "Point it at any course page and it builds an ad specific to that programme.",
      },
      {
        title: "Editable before it ships",
        desc: "Every claim in the script can be reviewed and rewritten before you export.",
      },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Inspirational" },
  },
  {
    slug: "salon-spa",
    eyebrow: "Industry",
    title: "Video ads for salons & spas",
    lead: "Warm, inviting ads built from your booking site.",
    metaDescription:
      "Create inviting video ads for your salon, spa or treatment room using your existing website.",
    intro:
      "Salons and spas sell atmosphere, and their sites usually show it. AdCraft captures those pages and lays a warm, friendly script over the top. The Playful style keeps the tone approachable without tipping into gimmick.",
    points: [
      {
        title: "Approachable, not shouty",
        desc: "Playful scripts stay friendly and conversational, which fits treatment and beauty services.",
      },
      {
        title: "Your palette, automatically",
        desc: "Brand colours come out of your live stylesheet and carry into the overlay and call-to-action button.",
      },
      {
        title: "Booking details on screen",
        desc: "Add your phone number and booking URL to the end card before export.",
      },
    ],
    suggested: { style: "Playful", duration: "15 seconds", music: "Upbeat" },
  },
  {
    slug: "local-services",
    eyebrow: "Industry",
    title: "Video ads for local services",
    lead: "For trades, repairs and home services — a proper video ad without a production budget.",
    metaDescription:
      "Generate video ads for local trades and home services businesses straight from your website.",
    intro:
      "Local service businesses rarely have creative budget, which is exactly the gap this fills. Point AdCraft at your site and it produces a narrated, branded video ad with your contact details on screen — usable on social or a local placement.",
    points: [
      {
        title: "No production cost",
        desc: "Generation is free while in beta, so a video ad stops being a budget decision.",
      },
      {
        title: "Contact details front and centre",
        desc: "Phone number, service area and website all sit on the end card where they are easy to read.",
      },
      {
        title: "Works from a simple site",
        desc: "Even a single-page site gives the scraper enough to work with; if it cannot read the page, you can supply the details yourself.",
      },
    ],
    suggested: { style: "Modern", duration: "15 seconds", music: "Corporate" },
  },
  {
    slug: "nonprofits",
    eyebrow: "Industry",
    title: "Video ads for nonprofits",
    lead: "Tell the story once and let the tooling handle the rest.",
    metaDescription:
      "Create video ads for your nonprofit, charity or community organisation from your existing website.",
    intro:
      "Nonprofits are usually working against a budget rather than with one. AdCraft produces a narrated, on-brand video for a campaign or appeal at no cost during the beta, using the site you already maintain as the source material.",
    points: [
      {
        title: "Free while in beta",
        desc: "No account, no card, no per-render cost — which matters when creative comes out of programme budget.",
      },
      {
        title: "Tone you control",
        desc: "Inspirational music with a Modern script suits an appeal; every line stays editable before export.",
      },
      {
        title: "Consistent across campaigns",
        desc: "Reuse the same settings so a series of appeals shares one visual identity.",
      },
    ],
    suggested: { style: "Modern", duration: "30 seconds", music: "Inspirational" },
  },
  {
    slug: "events",
    eyebrow: "Industry",
    title: "Video ads for events",
    lead: "Promote a date before it passes — generated in under a minute.",
    metaDescription:
      "Produce promotional video ads for events, conferences and gigs directly from your event page.",
    intro:
      "Event promotion is time-boxed: the ad is worthless the day after. Because a render finishes in well under a minute, you can produce and publish a spot the same afternoon you confirm the line-up, and re-render it if details change.",
    points: [
      {
        title: "Fast enough to matter",
        desc: "Under a minute from URL to finished MP4, so a last-minute announcement still gets a video.",
      },
      {
        title: "Re-render on changes",
        desc: "If the line-up or date shifts, generate again rather than editing a timeline by hand.",
      },
      {
        title: "Date and venue on screen",
        desc: "Put the essentials on the end card so the ad closes on how to get in touch.",
      },
    ],
    suggested: { style: "Bold", duration: "15 seconds", music: "Upbeat" },
  },
];
