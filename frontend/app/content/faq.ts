// Real answers, checked against the pipeline. If behaviour changes, change these.
// Do not add claims here that the backend cannot back up.

export type FaqItem = { q: string; a: string };

export const FAQ: FaqItem[] = [
  {
    q: "What does it cost?",
    a: "Nothing while AdCraft is in beta. There is no account, no card and no per-render charge — paste a URL and download the result.",
  },
  {
    q: "How long does a video take to generate?",
    a: "Usually under a minute. The exact time depends on your site: pages that respond quickly to a plain HTTP request are fastest, while sites that render client-side or block bots need a full headless browser pass, which adds time.",
  },
  {
    q: "What does it read from my website?",
    a: "Only what is publicly available on the page. It takes three screenshots to use as the backdrop, and pulls your business name, description and tagline from your title and meta tags, your logo from your markup, and your brand colours from your theme-color tag, inline styles, CSS custom properties and stylesheets.",
  },
  {
    q: "What format is the finished video?",
    a: "A 1280×720 MP4 — H.264 video with AAC audio at 128 kbps, thirty frames per second. It plays anywhere and uploads directly to social platforms.",
  },
  {
    q: "How long are the ads?",
    a: "Fifteen or thirty seconds. The length is part of the prompt given to the script model, so a fifteen-second script is genuinely written short rather than cut off at the end.",
  },
  {
    q: "Who does the voiceover?",
    a: "A synthesised voice from the Kokoro model, running locally rather than through a paid API. Four English voices are available: warm, professional, male and British.",
  },
  {
    q: "Where does the music come from?",
    a: "A small library of royalty-free tracks that ship with the app. The script model picks a mood to suit the ad, and the matching track is looped or trimmed to your chosen length, faded in and out, and mixed underneath the narration so the voice stays clear.",
  },
  {
    q: "Can I change the script before it goes out?",
    a: "Yes. The full script — headline, subtext, call to action and the complete voiceover — is shown on the result page, and the editor lets you rewrite any of it, adjust your brand colours and add a contact banner.",
  },
  {
    q: "Do my edits change the downloaded video?",
    a: "Yes. “Save & re-render” rebuilds the MP4 with your headline, subtext, call to action, voiceover script, music bed, brand colours and any scene images you swapped in. It takes about half a minute — narration is synthesised again and the video is re-encoded — and Download then gives you the new file. Scenes you did not replace are re-captured from your site, so the ad stays current.",
  },
  {
    q: "What if it cannot read my site?",
    a: "Some sites sit behind bot protection. When that happens you get a clear message rather than a failure, and can enter your business details by hand instead of having them detected automatically.",
  },
  {
    q: "Do I need to install anything?",
    a: "No. It runs in the browser and gives you a standard MP4 file. There is no editor to learn, no plugin and no export settings to configure.",
  },
  {
    q: "Can I generate ads programmatically?",
    a: "Yes — the web app is just a client for a plain JSON HTTP API. You can request a script on its own or run the whole pipeline through to a rendered video. See the API reference for the endpoints and payloads.",
  },
];
