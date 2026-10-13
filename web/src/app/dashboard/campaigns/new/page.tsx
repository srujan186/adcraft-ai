"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { OptionCard } from "@/components/app/OptionCard";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { GOALS, goalDef } from "@/lib/campaign-config";
import { type Advertiser, errorMessage } from "@/lib/hooks";

export default function NewCampaignPage() {
  const router = useRouter();
  const [advertiserId, setAdvertiserId] = useState("");
  // Empty value + placeholder: a prefilled value made typing append ("Untitled campaignSpring Sale").
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("traffic");
  const [kpi, setKpi] = useState("cps");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });

  const def = goalDef(goal)!;

  function pickGoal(v: string) {
    setGoal(v);
    setKpi(goalDef(v)!.kpis[0].value);
  }

  async function create() {
    setBusy(true);
    setError(null);
    const { data, error } = await api.POST("/api/v1/campaigns", {
      body: {
        advertiser_id: (advertiserId || advertisers[0]?.id || "") as string,
        name: name.trim() || "Untitled campaign",
        goal: goal as never,
        kpi: kpi as never,
      },
    });
    setBusy(false);
    if (error || !data) {
      setError(errorMessage(error, "Could not create campaign."));
      return;
    }
    router.push(`/dashboard/campaigns/${data.id}/edit`);
  }

  if (advertisers.length === 0) {
    return (
      <>
        <PageHeader title="Create campaign" subtitle="Set your campaign, strategies and review." />
        <div className="px-8 py-8">
          <p className="rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
            Add an advertiser first (Settings → Advertisers).
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Create campaign" subtitle="Pick a goal and how you'll measure success." />
      <div className="max-w-[820px] space-y-6 px-8 py-8">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Advertiser" htmlFor="c-adv">
            <Select id="c-adv" value={advertiserId} onChange={(e) => setAdvertiserId(e.target.value)}>
              {advertisers.map((a) => (
                <option key={String(a.id)} value={String(a.id)}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Campaign name" htmlFor="c-name">
            <Input id="c-name" value={name} placeholder="Untitled campaign" onChange={(e) => setName(e.target.value)} />
          </Field>
        </div>

        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
            Performance goals
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {GOALS.filter((g) => g.group === "Performance").map((g) => (
              <OptionCard key={g.value} selected={goal === g.value} onClick={() => pickGoal(g.value)} title={g.label} description={g.description} />
            ))}
          </div>
          <p className="mb-2 mt-4 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
            Specialized types
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {GOALS.filter((g) => g.group === "Specialized").map((g) => (
              <OptionCard key={g.value} selected={goal === g.value} onClick={() => pickGoal(g.value)} title={g.label} description={g.description} />
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-[var(--color-text-body)]">Measurement (KPI)</p>
          <div className="space-y-2">
            {def.kpis.map((k) => (
              <label
                key={k.value}
                className="flex cursor-pointer items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-2.5 text-sm has-[:checked]:border-[var(--color-primary)] has-[:checked]:bg-[var(--color-primary-50)]"
              >
                <input type="radio" name="kpi" checked={kpi === k.value} onChange={() => setKpi(k.value)} />
                <span className="font-medium text-[var(--color-text)]">{k.label}</span>
                <span className="text-[var(--color-text-muted)]">— {k.desc}</span>
              </label>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
        <Button onClick={create} disabled={busy}>
          {busy ? "Creating…" : "Continue to strategy"}
        </Button>
      </div>
    </>
  );
}
