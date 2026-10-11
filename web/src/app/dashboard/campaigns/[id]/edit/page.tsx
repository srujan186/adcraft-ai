"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { goalDef } from "@/lib/campaign-config";
import { type CampaignDetail, type Creative, type Estimate, type Strategy } from "@/lib/hooks";
import { nfCompact, usd } from "@/lib/utils";

type Loc = { type: string; code: string; name?: string };
const DEMO = {
  age: ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
  gender: ["female", "male"],
  income: ["<20k", "20k-49k", "50k-99k", "100k-249k", "250k-499k", "500k+"],
};
const DELIV_TONE: Record<string, string> = {
  insufficient: "danger", limited: "warning", good: "success", excellent: "success",
};

export default function WizardPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [strat, setStrat] = useState<Strategy | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [saving, setSaving] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const estTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: campaign } = useQuery({
    queryKey: ["campaign", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/campaigns/{campaign_id}", {
        params: { path: { campaign_id: id } },
      });
      if (error) throw error;
      return data as CampaignDetail;
    },
  });

  // active strategy = first (wizard edits one at a time for now)
  useEffect(() => {
    if (campaign && !strat) setStrat(campaign.strategies[0] ?? null);
  }, [campaign, strat]);

  const runEstimate = useCallback(
    (s: Strategy, goal: string) => {
      if (estTimer.current) clearTimeout(estTimer.current);
      estTimer.current = setTimeout(async () => {
        const { data } = await api.POST("/api/v1/estimate", {
          body: {
            goal: goal as never,
            strategy: {
              budget_type: s.budget_type, budget_micros: s.budget_micros, start_date: s.start_date,
              end_date: s.end_date, dayparting: s.dayparting, locations: s.locations,
              interest_segment_ids: s.interest_segment_ids, demographics: s.demographics,
              placement_mode: s.placement_mode, channel_ids: s.channel_ids,
              device_types: s.device_types, bidding_mode: s.bidding_mode, max_cpm_micros: s.max_cpm_micros,
            } as never,
          },
        });
        if (data) setEstimate(data as Estimate);
      }, 400);
    },
    [],
  );

  useEffect(() => {
    if (strat && campaign) runEstimate(strat, campaign.goal);
  }, [strat, campaign, runEstimate]);

  const patch = (partial: Partial<Strategy>) => {
    if (!strat) return;
    const next = { ...strat, ...partial };
    setStrat(next);
    setSaving(true);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      await api.PATCH("/api/v1/strategies/{strategy_id}", {
        params: { path: { strategy_id: String(next.id) } },
        body: partial as never,
      });
      setSaving(false);
      qc.invalidateQueries({ queryKey: ["campaign", id] });
    }, 600);
  };

  if (!campaign || !strat) {
    return <div className="grid min-h-[60vh] place-items-center text-sm text-[var(--color-text-muted)]">Loading…</div>;
  }

  return (
    <div>
      {/* top bar */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-3">
        <Link href="/dashboard/campaigns" className="flex items-center gap-1.5 text-sm text-[var(--color-text-body)]">
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <div className="text-sm font-medium text-[var(--color-text)]">
          You are creating… / {campaign.name}
        </div>
        <span className="text-xs text-[var(--color-text-muted)]">{saving ? "Saving…" : "Saved"}</span>
      </div>

      <div className="grid grid-cols-12 gap-6 px-6 py-6">
        {/* step rail */}
        <aside className="col-span-12 lg:col-span-2">
          <ol className="space-y-1">
            {[["01", "Set your campaign"], ["02", "Set your strategies"], ["03", "Review"]].map((s, i) => (
              <li key={s[0]}>
                <button
                  onClick={() => setStep(i + 1)}
                  className={`w-full rounded-[var(--radius-md)] px-3 py-2 text-left ${step === i + 1 ? "bg-[var(--color-primary-50)]" : "hover:bg-[var(--color-bg-subtle)]"}`}
                >
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                    {s[0]} {i === 0 ? "Campaign" : i === 1 ? "Strategy" : "Summary"}
                  </div>
                  <div className="text-[13px] text-[var(--color-text-body)]">{s[1]}</div>
                </button>
              </li>
            ))}
          </ol>
        </aside>

        {/* center */}
        <main className="col-span-12 space-y-5 lg:col-span-7">
          {step === 1 && <CampaignStep campaign={campaign} onChange={() => qc.invalidateQueries({ queryKey: ["campaign", id] })} />}
          {step === 2 && <StrategyStep strat={strat} patch={patch} />}
          {step === 3 && <SummaryStep campaignId={id} />}
          <div className="flex justify-between pt-2">
            <Button variant="ghost" disabled={step === 1} onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
            {step < 3 && <Button onClick={() => setStep((s) => s + 1)}>Continue</Button>}
          </div>
        </main>

        {/* estimate panel */}
        <aside className="col-span-12 lg:col-span-3">
          <div className="sticky top-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">Strategy estimate</h3>
            {estimate ? (
              <div className="mt-4 space-y-3 text-sm">
                <div>
                  <div className="text-xs text-[var(--color-text-muted)]">Audience size</div>
                  <div className="font-semibold tabular-nums text-[var(--color-text)]">
                    {nfCompact.format(estimate.audience_households[0])} – {nfCompact.format(estimate.audience_households[1])}
                  </div>
                </div>
                <div className="rounded-[var(--radius-md)] bg-[var(--color-bg-subtle)] p-3">
                  <div className="text-xs text-[var(--color-text-muted)]">
                    Based on ${(strat.budget_micros / 1e6).toFixed(0)}/day, weekly results:
                  </div>
                  <div className="mt-1 flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Impressions</span>
                    <span className="tabular-nums">{nfCompact.format(estimate.weekly.impressions[0])}–{nfCompact.format(estimate.weekly.impressions[1])}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Households</span>
                    <span className="tabular-nums">{nfCompact.format(estimate.weekly.households[0])}–{nfCompact.format(estimate.weekly.households[1])}</span>
                  </div>
                </div>
                <div>
                  <div className="mb-1 text-xs text-[var(--color-text-muted)]">Deliverability</div>
                  <StatusPill status={estimate.deliverability === "insufficient" ? "blocked" : estimate.deliverability === "limited" ? "draft" : "delivering"} />
                  <span className="ml-2 text-xs capitalize text-[var(--color-text-muted)]">{estimate.deliverability}</span>
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">Est. CPM {usd(estimate.expected_cpm_micros)}</div>
                {estimate.deliverability === "insufficient" && (
                  <div className="rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-danger-50)] p-3 text-xs text-[var(--color-danger)]">
                    {estimate.messages[0] ?? "Your targeting is too narrow."}
                    <button className="mt-2 block font-medium underline" onClick={() => setStep(2)}>
                      Adjust targeting
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="mt-3 text-xs text-[var(--color-text-muted)]">Calculating…</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

// ── Step 1: campaign ──────────────────────────────────────────────────────────
const REQUIRED_EVENTS: Record<string, string[]> = {
  traffic: ["page_view"], retargeting: ["page_view"],
  leads: ["page_view", "lead"], sales: ["page_view", "purchase"],
};

function CampaignStep({ campaign, onChange }: { campaign: CampaignDetail; onChange: () => void }) {
  const [name, setName] = useState(campaign.name);
  const def = goalDef(campaign.goal);
  const required = REQUIRED_EVENTS[campaign.goal] ?? [];

  const { data: tracking } = useQuery({
    queryKey: ["tracking", campaign.advertiser_id],
    enabled: required.length > 0 || campaign.goal === "app_promotion",
    refetchInterval: 4000,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/advertisers/{advertiser_id}/tracking", {
        params: { path: { advertiser_id: String(campaign.advertiser_id) } },
      });
      return data as { has_pixel: boolean; events_seen: Record<string, boolean>; has_app: boolean };
    },
  });

  async function saveName() {
    await api.PATCH("/api/v1/campaigns/{campaign_id}", {
      params: { path: { campaign_id: String(campaign.id) } },
      body: { name } as never,
    });
    onChange();
  }
  return (
    <>
      <Card title="Campaign name">
        <Input value={name} onChange={(e) => setName(e.target.value)} onBlur={saveName} />
      </Card>
      <Card title="Goal & measurement">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--color-text)]">{def?.label}</span>
        </div>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">{def?.description}</p>
        <p className="mt-2 text-sm text-[var(--color-text-body)]">
          Optimizing for <strong>{def?.kpis.find((k) => k.value === campaign.kpi)?.label ?? campaign.kpi}</strong>.
        </p>
      </Card>
      {(required.length > 0 || campaign.goal === "app_promotion") && (
        <Card title="Measurement setup">
          {campaign.goal === "app_promotion" ? (
            <div className="flex items-center gap-2 text-sm">
              {tracking?.has_app ? (
                <span className="text-[var(--color-success)]">App Tracking connected ✓</span>
              ) : (
                <>
                  <span className="rounded-full bg-[var(--color-danger-50)] px-2 py-0.5 text-xs font-medium text-[var(--color-danger)]">App Tracking missing</span>
                  <Link href="/dashboard/settings/tracking/app" className="font-medium text-[var(--color-primary)]">Manage App Tracking</Link>
                </>
              )}
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              {required.map((ev) => {
                const seen = tracking?.events_seen?.[ev];
                return (
                  <span
                    key={ev}
                    className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${seen ? "bg-[var(--color-success-50)] text-[var(--color-success)]" : "bg-[var(--color-danger-50)] text-[var(--color-danger)]"}`}
                  >
                    {ev.replace("_", " ")} {seen ? "✓" : "missing"}
                  </span>
                );
              })}
              {!tracking?.has_pixel && (
                <Link href="/dashboard/settings/tracking/web" className="font-medium text-[var(--color-primary)]">Set up pixel</Link>
              )}
            </div>
          )}
        </Card>
      )}
    </>
  );
}

// ── Step 2: strategy ──────────────────────────────────────────────────────────
function StrategyStep({ strat, patch }: { strat: Strategy; patch: (p: Partial<Strategy>) => void }) {
  const include = (strat.locations?.include ?? []) as Loc[];

  return (
    <>
      <Card title="Budget & schedule">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <div className="mb-1 text-[var(--color-text-body)]">Budget (USD)</div>
            <Input
              type="number"
              min={50}
              value={Math.round(strat.budget_micros / 1e6)}
              onChange={(e) => patch({ budget_micros: Math.max(0, Number(e.target.value)) * 1_000_000 })}
              className="w-32"
            />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-[var(--color-text-body)]">Type</div>
            <Select value={strat.budget_type} onChange={(e) => patch({ budget_type: e.target.value as never })}>
              <option value="daily">Daily budget</option>
              <option value="lifetime">Lifetime budget</option>
            </Select>
          </label>
        </div>
        <p className="mt-2 text-xs text-[var(--color-text-muted)]">Minimum $50/day.</p>
      </Card>

      <LocationsCard include={include} onChange={(inc) => patch({ locations: { ...strat.locations, include: inc } as never })} />
      <InterestsCard selected={(strat.interest_segment_ids ?? []) as string[]} onChange={(ids) => patch({ interest_segment_ids: ids as never })} />

      <Card title="Demographics">
        {Object.entries(DEMO).map(([dim, opts]) => (
          <div key={dim} className="mb-2">
            <div className="mb-1 text-xs font-medium capitalize text-[var(--color-text-muted)]">{dim}</div>
            <div className="flex flex-wrap gap-2">
              {opts.map((o) => {
                const cur = ((strat.demographics as Record<string, string[]>)?.[dim] ?? []) as string[];
                const on = cur.includes(o);
                return (
                  <button
                    key={o}
                    onClick={() => {
                      const next = on ? cur.filter((x) => x !== o) : [...cur, o];
                      patch({ demographics: { ...strat.demographics, [dim]: next } as never });
                    }}
                    className={`rounded-full border px-3 py-1 text-xs ${on ? "border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)]" : "border-[var(--color-border)] text-[var(--color-text-body)]"}`}
                  >
                    {o}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </Card>

      <AudiencesCard strat={strat} patch={patch} />
      <PlacementCard strat={strat} patch={patch} />

      <Card title="Bidding">
        <div className="flex gap-2">
          {["automatic", "manual"].map((m) => (
            <button
              key={m}
              onClick={() => patch({ bidding_mode: m as never })}
              className={`flex-1 rounded-[var(--radius-md)] border px-3 py-2 text-sm capitalize ${strat.bidding_mode === m ? "border-[var(--color-primary)] bg-[var(--color-primary-50)]" : "border-[var(--color-border)]"}`}
            >
              {m}
            </button>
          ))}
        </div>
        {strat.bidding_mode === "manual" && (
          <label className="mt-3 block text-sm">
            <div className="mb-1 text-[var(--color-text-body)]">Max CPM (USD)</div>
            <Input
              type="number"
              value={strat.max_cpm_micros ? Math.round(strat.max_cpm_micros / 1e6) : ""}
              onChange={(e) => patch({ max_cpm_micros: Number(e.target.value) * 1_000_000 })}
              className="w-32"
            />
          </label>
        )}
      </Card>

      <CreativesCard strat={strat} patch={patch} />
    </>
  );
}

function LocationsCard({ include, onChange }: { include: Loc[]; onChange: (inc: Loc[]) => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: string; type: string; code: string; name: string }[]>([]);
  useEffect(() => {
    if (q.length < 2) return setResults([]);
    const t = setTimeout(async () => {
      const { data } = await api.GET("/api/v1/geos/search", { params: { query: { q } } });
      setResults((data as never[]) ?? []);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <Card title="Locations">
      <p className="mb-2 text-xs text-[var(--color-text-muted)]">
        {include.length === 0 ? "Entire US (no restriction)" : `${include.length} location(s) included`}
      </p>
      <Input placeholder="Search a state, DMA, city or ZIP…" value={q} onChange={(e) => setQ(e.target.value)} />
      {results.length > 0 && (
        <div className="mt-1 max-h-40 overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
          {results.map((r) => (
            <button
              key={r.id}
              className="block w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--color-bg-subtle)]"
              onClick={() => {
                if (!include.some((i) => i.code === r.code && i.type === r.type))
                  onChange([...include, { type: r.type, code: r.code, name: r.name }]);
                setQ("");
                setResults([]);
              }}
            >
              <span className="capitalize text-[var(--color-text-muted)]">{r.type}</span> · {r.name}
            </button>
          ))}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {include.map((i) => (
          <span key={`${i.type}:${i.code}`} className="flex items-center gap-1 rounded-full bg-[var(--color-primary-50)] px-2 py-0.5 text-xs text-[var(--color-primary)]">
            {i.name ?? i.code}
            <button onClick={() => onChange(include.filter((x) => !(x.code === i.code && x.type === i.type)))}>×</button>
          </span>
        ))}
      </div>
    </Card>
  );
}

function InterestsCard({ selected, onChange }: { selected: string[]; onChange: (ids: string[]) => void }) {
  const [q, setQ] = useState("");
  const { data: tree = [] } = useQuery({
    queryKey: ["interest-segments"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/interest-segments");
      return (data as never[]) ?? [];
    },
  });
  const leaves = useMemo(() => {
    const out: { id: string; name: string; parent: string }[] = [];
    for (const r of tree as { id: string; name: string; children: { id: string; name: string }[] }[]) {
      for (const c of r.children) out.push({ id: c.id, name: c.name, parent: r.name });
    }
    return out;
  }, [tree]);
  const shown = leaves.filter((l) => !q || l.name.toLowerCase().includes(q.toLowerCase())).slice(0, 40);
  return (
    <Card title={`In-market & interests${selected.length ? ` (${selected.length})` : ""}`}>
      <Input placeholder="Search interests…" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="mt-2 flex max-h-48 flex-wrap gap-1.5 overflow-auto">
        {shown.map((l) => {
          const on = selected.includes(l.id);
          return (
            <button
              key={l.id}
              onClick={() => onChange(on ? selected.filter((x) => x !== l.id) : [...selected, l.id])}
              className={`rounded-full border px-2.5 py-1 text-xs ${on ? "border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)]" : "border-[var(--color-border)] text-[var(--color-text-body)]"}`}
              title={l.parent}
            >
              {l.name}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

function PlacementCard({ strat, patch }: { strat: Strategy; patch: (p: Partial<Strategy>) => void }) {
  const [q, setQ] = useState("");
  const { data } = useQuery({
    queryKey: ["channels", q],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/channels", { params: { query: { q: q || undefined, limit: 30 } } });
      return (data as { items: { id: string; name: string; reach_households: number }[]; total_count: number }) ?? null;
    },
  });
  const selected = (strat.channel_ids ?? []) as string[];
  return (
    <Card title="Placement">
      <div className="flex gap-2">
        {[["all", "All Apps & Channels"], ["selected", "Select channels"]].map(([m, label]) => (
          <button
            key={m}
            onClick={() => patch({ placement_mode: m as never })}
            className={`flex-1 rounded-[var(--radius-md)] border px-3 py-2 text-sm ${strat.placement_mode === m ? "border-[var(--color-primary)] bg-[var(--color-primary-50)]" : "border-[var(--color-border)]"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {strat.placement_mode === "selected" && (
        <div className="mt-3">
          <Input placeholder={`Search ${data?.total_count ?? ""} channels…`} value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="mt-2 max-h-48 overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
            {(data?.items ?? []).map((ch) => {
              const on = selected.includes(ch.id);
              return (
                <button
                  key={ch.id}
                  onClick={() => patch({ channel_ids: (on ? selected.filter((x) => x !== ch.id) : [...selected, ch.id]) as never })}
                  className={`flex w-full items-center justify-between px-3 py-1.5 text-left text-sm ${on ? "bg-[var(--color-primary-50)]" : "hover:bg-[var(--color-bg-subtle)]"}`}
                >
                  <span>{ch.name}</span>
                  <span className="text-xs text-[var(--color-text-muted)]">{nfCompact.format(ch.reach_households)}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">{selected.length} selected</p>
        </div>
      )}
    </Card>
  );
}

function AudiencesCard({ strat, patch }: { strat: Strategy; patch: (p: Partial<Strategy>) => void }) {
  const { data: audiences = [] } = useQuery({
    queryKey: ["audiences"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/audiences");
      return (data as { id: string; name: string; source: string; matched_households: number }[]) ?? [];
    },
  });
  const inc = (strat.include_audience_ids ?? []).map(String);
  const exc = (strat.exclude_audience_ids ?? []).map(String);
  const set = (id: string, mode: "inc" | "exc" | "off") => {
    const ni = inc.filter((x) => x !== id);
    const ne = exc.filter((x) => x !== id);
    if (mode === "inc") ni.push(id);
    if (mode === "exc") ne.push(id);
    patch({ include_audience_ids: ni as never, exclude_audience_ids: ne as never });
  };
  return (
    <Card title="Custom & web audiences">
      {audiences.length === 0 ? (
        <p className="text-sm text-[var(--color-text-muted)]">No audiences yet. Create some under Audiences.</p>
      ) : (
        <div className="space-y-1.5">
          {audiences.map((a) => {
            const state = inc.includes(a.id) ? "inc" : exc.includes(a.id) ? "exc" : "off";
            return (
              <div key={a.id} className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2 text-sm">
                <div>
                  <span className="font-medium text-[var(--color-text)]">{a.name}</span>
                  <span className="ml-2 text-xs text-[var(--color-text-muted)]">{a.source.replace(/_/g, " ")} · {nfCompact.format(a.matched_households)}</span>
                </div>
                <div className="flex gap-1">
                  {(["inc", "off", "exc"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => set(a.id, m)}
                      className={`rounded px-2 py-0.5 text-xs ${state === m ? (m === "exc" ? "bg-[var(--color-danger-50)] text-[var(--color-danger)]" : m === "inc" ? "bg-[var(--color-primary-50)] text-[var(--color-primary)]" : "bg-slate-100 text-slate-600") : "text-[var(--color-text-muted)]"}`}
                    >
                      {m === "inc" ? "Include" : m === "exc" ? "Exclude" : "Off"}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function CreativesCard({ strat, patch }: { strat: Strategy; patch: (p: Partial<Strategy>) => void }) {
  const { data: creatives = [] } = useQuery({
    queryKey: ["creatives", "approved"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/creatives", { params: { query: { review_status: "approved" } } });
      return (data as Creative[]) ?? [];
    },
  });
  // creative_ids is write-only (not on StrategyOut); track locally
  const [picked, setPicked] = useState<string[]>([]);
  return (
    <Card title="Creatives">
      {creatives.length === 0 ? (
        <p className="text-sm text-[var(--color-text-muted)]">
          No approved creatives yet. Upload one in the Library.
        </p>
      ) : (
        <div className="space-y-1.5">
          {creatives.map((c) => {
            const on = picked.includes(String(c.id));
            return (
              <button
                key={String(c.id)}
                onClick={() => {
                  const next = on ? picked.filter((x) => x !== String(c.id)) : [...picked, String(c.id)];
                  setPicked(next);
                  patch({ creative_ids: next } as never);
                }}
                className={`flex w-full items-center gap-3 rounded-[var(--radius-md)] border px-3 py-2 text-left text-sm ${on ? "border-[var(--color-primary)] bg-[var(--color-primary-50)]" : "border-[var(--color-border)]"}`}
              >
                {c.thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.thumbnail_url} alt={c.name} className="h-8 w-14 rounded object-cover" />
                )}
                <span className="font-medium text-[var(--color-text)]">{c.name}</span>
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}

// ── Step 3: summary ──────────────────────────────────────────────────────────
function SummaryStep({ campaignId }: { campaignId: string }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [note, setNote] = useState<{ ok: boolean; text: string; needFunds?: boolean } | null>(null);

  const { data: result } = useQuery({
    queryKey: ["validate", campaignId],
    queryFn: async () => {
      const { data, error } = await api.POST("/api/v1/campaigns/{campaign_id}/validate", {
        params: { path: { campaign_id: campaignId } },
      });
      if (error) throw error;
      return data as { ok: boolean; issues: { level: string; code: string; message: string; field: string | null }[] };
    },
  });

  const publish = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/campaigns/{campaign_id}/publish", {
        params: { path: { campaign_id: campaignId } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      router.push("/dashboard/campaigns");
    },
    onError: (e: unknown) => {
      const err = e as { error?: { code?: string; message?: string } };
      if (err?.error?.code === "INSUFFICIENT_BALANCE") {
        setNote({ ok: false, text: err.error.message ?? "Add funds to publish.", needFunds: true });
      } else {
        setNote({ ok: false, text: err?.error?.message ?? "Could not publish." });
      }
    },
  });

  const hasErrors = (result?.issues ?? []).some((i) => i.level === "error");

  return (
    <Card title="Review & publish">
      {!result ? (
        <p className="text-sm text-[var(--color-text-muted)]">Checking…</p>
      ) : (
        <>
          {result.issues.length === 0 ? (
            <p className="text-sm text-[var(--color-success)]">Everything looks good.</p>
          ) : (
            <ul className="space-y-2">
              {result.issues.map((i, n) => (
                <li
                  key={n}
                  className={`rounded-[var(--radius-md)] px-3 py-2 text-sm ${i.level === "error" ? "bg-[var(--color-danger-50)] text-[var(--color-danger)]" : "bg-[var(--color-warning-50)] text-[var(--color-warning)]"}`}
                >
                  <span className="font-semibold">{i.level === "error" ? "Error" : "Warning"}:</span> {i.message}
                  {i.field && <span className="text-xs"> ({i.field})</span>}
                </li>
              ))}
            </ul>
          )}
          <Button className="mt-4" onClick={() => publish.mutate()} disabled={publish.isPending || hasErrors}>
            {publish.isPending ? "Publishing…" : "Publish campaign"}
          </Button>
          {note && (
            <p className={`mt-3 text-sm ${note.ok ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`}>
              {note.text}{" "}
              {note.needFunds && (
                <Link href="/dashboard/settings/billing/balance" className="font-medium underline">Add funds</Link>
              )}
            </p>
          )}
        </>
      )}
    </Card>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text)]">{title}</h3>
      {children}
    </section>
  );
}
