# AdCraft — generation pipeline architecture

How a business URL becomes a narrated MP4, and specifically how the ad's
**scenes** are sourced and chosen. Diagrams are Mermaid (render in GitHub and in
VS Code's preview). Prose lives in [`AGENTS.md`](./AGENTS.md); this file is the
map.

**One idea runs through the whole thing:** the hard problem is *which visuals*
an ad should use, and it is split into two stages that each use only the data
they have —

- a **text / structure** stage (`visual_sourcing.py`, at scrape time) decides
  which image URLs are worth using and in what order, from page structure,
  section headings and the sitemap;
- a **pixel** stage (`video_assembler.py`, at render time) downloads them and
  makes the calls that need actual pixels — face vs UI, flat vs busy, coherent
  tone.

Because the pixel stage runs after and filters, the text stage never has to be
perfect.

```
Shape key:  ([ ... ])  data / artifact      [ ... ]  step / function
            { ... }    decision             [[ ... ]] external process
```

---

## 1. End-to-end

```mermaid
flowchart LR
  U(["business URL"]) --> RT["POST /api/generate/video"]
  RT --> SCR["scrape_business_url()"]

  subgraph SCRAPE["scrape  ·  scraper.py"]
    SCR --> PARSE["parse_html()<br/>name · desc · colours · logo<br/>detect_site_intent()"]
    PARSE --> FIN["_finalize_result()<br/>runs visual sourcing"]
  end

  FIN --> BRAND(["brand data + site_intent"])
  FIN --> IMGS(["ordered image URLs"])

  BRAND --> SGEN["generate_ad_script()<br/>duration-aware arc"]
  SGEN --> SCRIPT(["ad script"])

  SCRIPT --> ASM["assemble_video()"]
  IMGS --> ASM
  BRAND --> ASM

  subgraph MEDIA["media  ·  tts.py · music.py"]
    TTS[["Kokoro TTS"]] --> MIX["mix_audio()"]
    MUS[["music bed"]] --> MIX
  end
  MIX --> ASM

  ASM --> FF[["FFmpeg<br/>scrim · captions · logo<br/>end card · audio mux"]]
  FF --> OUT(["narrated MP4 (720p)"])
```

`/generate/rerender` skips `scrape` + `generate_ad_script` and re-enters at
`assemble_video` with the editor's edited copy.

---

## 2. Visual sourcing — the text / structure stage

`services/visual_sourcing.py`, called once from `_finalize_result`. Produces the
ordered candidate image URLs. **Nothing here is per-site**: discovery is the
site's own sitemap + nav, ownership is the site's own section headings.

```mermaid
flowchart TB
  START(["homepage HTML + business name + site_intent"]) --> EXTRACT

  subgraph PROFILE_SOURCE["Profile → Source"]
    EXTRACT["extract_candidates()<br/>every img, tagged with provenance:<br/>source page · section heading · alt"]
    EXTRACT --> OWN["classify_ownership() per image"]
    OWN --> OWNKIND{"heading shape?"}
    OWNKIND -->|"'Company does X with the business'<br/>customers · trusted by"| TP(["third_party"])
    OWNKIND -->|"product · features · how it works"| OWNED(["own"])
    OWNKIND -->|"else"| NEU(["neutral"])
  end

  TP --> GATE
  OWNED --> GATE
  NEU --> GATE

  GATE{"site_intent == saas?"}
  GATE -->|"no — store / unknown"| ORDER
  GATE -->|"yes — product UI on sub-pages"| DISC

  subgraph CRAWL["product-page crawl · no hardcoded paths"]
    DISC["discover_product_pages()<br/>nav link semantics<br/>+ sitemap.xml / robots.txt"]
    DISC --> REND[["render each page (Playwright)"]]
    REND --> EXTRACT2["extract_candidates()<br/>source = product-page"]
  end
  EXTRACT2 --> ORDER

  subgraph SCORE["Score / order"]
    ORDER["order_candidates()<br/>own &gt; neutral &gt; third_party<br/>product-page &gt; homepage<br/>then size · SVG down-ranked"]
  end
  ORDER --> RESULT(["ordered image URLs → result images"])
```

**Why ownership generalises:** a customer/case-study section reads
*"{external company} {verb} with {business}"* — "Hertz unifies commerce with
Stripe". That shape is detectable without any list of brand names, and it is
what flagged 18/35 of Stripe's homepage images as third-party so its *own*
product UI could lead.

---

## 3. Scene selection — the pixel / assembly stage

Inside `assemble_video()` (`video_assembler.py`). Takes the ordered URLs and
turns them into the background video. This is where the calls that need pixels
happen, and where the ordered-but-imperfect list gets cleaned.

```mermaid
flowchart TB
  IN(["ordered image URLs (content_images)<br/>+ duration"]) --> N["scenes_for_duration()<br/>15s = 6 · 30s = 10"]
  N --> RES["resolve_scene_images(vet=True)<br/>download · decode"]

  RES --> VET{"_vet_scene_image()<br/>badge? logo-strip? flat?"}
  VET -->|"reject"| DROP["drop"]
  VET -->|"keep"| FLAT["_flatten_for_render()<br/>RGBA onto white, not black"]

  FLAT --> SELECT["select_scenes()<br/>classify_scene_image() per image:<br/>face? ui? tone? detail?<br/>rank faces last, tone-coherent"]

  SELECT --> GOODQ{"distinct good<br/>non-face shots?"}
  GOODQ -->|"at least target"| USE["take target"]
  GOODQ -->|"3+ but under target"| REUSE["reuse good shots<br/>to hit target, spread out"]
  GOODQ -->|"under 3"| POOR["use what exists<br/>+ faces, then…"]
  POOR --> TOP[["screenshot top-up<br/>capture_website_screenshots()"]]

  USE --> S2V
  REUSE --> S2V
  TOP --> S2V
  S2V["screenshots_to_video()<br/>cover-crop, 1 clip per scene"] --> BG(["background video"])
  BG --> ASSEM[["assemble_with_ffmpeg()<br/>scrim · captions · logo · end card"]]
```

**The safety-net relationship:** stage 2 orders by text signals and can leave
junk near the front (a `close.svg`, a social card); stage 3's `vet` + `classify`
reject or sink it. Neither stage carries the whole burden.

---

## Where each concern lives

| Concern | Stage | Function(s) |
|---|---|---|
| Site type | scrape | `detect_site_intent` |
| Find product pages | scrape | `discover_product_pages` (sitemap + nav) |
| Own vs customer imagery | scrape | `classify_ownership` (section headings) |
| Candidate ordering | scrape | `order_candidates` |
| Badge / logo-strip / flat rejection | assembly | `_vet_scene_image` |
| Face vs UI vs photo, tone | assembly | `classify_scene_image` |
| Final pick + coherence + reuse | assembly | `select_scenes` + fill logic |
| Scene count by length | assembly | `scenes_for_duration` |
| Script length / arc by length | script | `build_prompt` (duration branch) |
