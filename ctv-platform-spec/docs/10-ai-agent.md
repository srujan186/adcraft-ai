# 10 — "Ask Agent" (LLM agent)

## Surfaces
1. **Global** "Ask Agent" button in top nav → right Sheet with chat (thread persisted).
2. **Section buttons** "Ask agent" on wizard cards (Campaign name, Audience, Placement, Bidding, Creatives...) →
   popover with input "What's on your mind?" + 2 suggested questions for that section, e.g.
   Audience: "What audience should I target?", "What's the difference between audience suggestions and audience controls?"
   Bidding: "Should I use automatic or manual bidding?", "What CPM should I expect?"
   Measurement: "Help me set my target", "Which attribution window should I use?"
   Answer appears in a floating card ("Agent's answer") with **Dismiss** / **Open chat**.
   While the agent runs: top button shows "Working...", wizard inputs disabled with note
   "While the agent is running you cannot edit any campaign settings."
3. **Dashboard FAQ / explainer** buttons open the global panel pre-filled.

## Backend (`services/agent/`)
- Provider: Anthropic Messages API with tool use, streaming over SSE to the client. Model name from env.
- System prompt = product role + rules + **the playbook** (`playbook/playbook.yaml` rendered to markdown) +
  glossary (00) + current context JSON (page, section, campaign + strategies with targeting summary, last 14 days
  metrics, tracking status, open recommendations).
- Rules in the system prompt: answer in ≤ 180 words with short bold section headers; ground claims in the
  context; cite playbook rule ids silently; never invent metrics; offer a concrete next step and ask if it should do it.

### Tools
| tool | type | description |
|---|---|---|
| get_campaign(campaign_id) | read | campaign + strategies |
| get_metrics(entity, id, from, to, metrics[]) | read | from stats_daily |
| get_estimate(strategy_draft) | read | calls estimator |
| list_interest_segments(query) | read | taxonomy search with reach |
| list_audiences(advertiser_id) | read | |
| list_channels(category?, query?) | read | |
| get_tracking_status(advertiser_id) | read | |
| get_recommendations(campaign_id) | read | |
| search_help(query) | read | over /web/content/help/*.md (simple BM25) |
| propose_change(action) | write-proposal | creates `agent_proposals` row with JSON patch, returns a diff summary |

`propose_change` actions: `update_campaign`, `update_strategy` (any field), `create_strategy` (e.g. split warm/cold),
`duplicate_strategy`, `add_creatives`. The UI renders a **Proposal card**: human-readable diff
("Budget: $100 → $150/day", "+ Interests: Home & Garden, Personal Finance") with **Apply** / **Discard**.
Apply calls `/agent/proposals/{id}/apply` which validates with the same Pydantic schemas as the normal API.
The agent can never write directly.

## Reference behavior (acceptance test)
Context: Sales campaign, 30-day window, one strategy with web audiences (Visitors, Leads, Purchasers) included.
Q: "What audience should I target?" Expected answer structure:
1. **What you already have — warm audiences (retargeting)**: visitors/leads/purchasers are highest intent, fit Sales.
2. **What you could add — prospecting audiences**: because the attribution window is long (30d), playbook rule
   `reach_for_long_window` says maximize reach → interests, demographics, age & gender, lookalikes.
3. **One important note**: mixing warm and cold in one strategy hides what works (rule `separate_warm_cold`) →
   recommend one retargeting strategy + one prospecting strategy.
4. Offer: "Would you like me to add interest targeting to this strategy, or set up a second prospecting strategy?"
   → on "yes, second strategy" it calls `propose_change(create_strategy ...)`.

## Without API key
Agent panel shows "AI agent is not configured" and section popovers fall back to static playbook answers
(`playbook.yaml > faq`).
