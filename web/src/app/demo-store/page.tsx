"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { getAccessToken, getAccountId } from "@/lib/auth";
import { API_URL } from "@/lib/utils";

type Page = "home" | "product" | "checkout" | "thankyou";
interface Pixel { id: string; public_key: string; advertiser_id: string }
interface HH { id: string; city: string; state: string; age_bucket: string; interests: string[] }

export default function DemoStorePage() {
  const [page, setPage] = useState<Page>("home");
  const [hh, setHh] = useState("");

  const { data: pixels = [] } = useQuery({
    queryKey: ["pixels"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/pixels");
      return (data as Pixel[]) ?? [];
    },
  });
  const { data: households = [] } = useQuery({
    queryKey: ["dev-households"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/dev/households"); // 404 in production → no picker
      return (data as HH[]) ?? [];
    },
  });
  const pixel = pixels[0];

  const fire = useCallback(
    (ev: string, props: Record<string, unknown> = {}) => {
      if (!pixel) return;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (hh) headers["X-Sim-Household"] = hh;
      fetch(`${API_URL}/e`, {
        method: "POST",
        headers,
        body: JSON.stringify({ k: pixel.public_key, ev, url: `demo-store://${page}`, ...props }),
      }).catch(() => {});
    },
    [pixel, hh, page],
  );

  // page_view on every page; purchase on thank-you
  useEffect(() => {
    if (!pixel) return;
    fire("page_view");
    if (page === "thankyou") fire("purchase", { value: 49.9, currency: "USD", order_id: `demo-${Date.now()}` });
    if (page === "product") fire("add_to_cart", { value: 49.9 });
  }, [page, pixel, fire]);

  const authed = !!getAccessToken() && !!getAccountId();

  return (
    <div className="min-h-screen bg-[var(--color-bg-subtle)]">
      {/* test toolbar — the household picker exists only in development (the list is a dev endpoint) */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--color-nav)] px-4 py-2 text-xs text-[var(--color-nav-text)]">
        <span className="font-semibold">Test store</span>
        {households.length > 0 ? (
          <>
            <span>Visit as test household:</span>
            <select
              value={hh}
              onChange={(e) => setHh(e.target.value)}
              className="rounded bg-white/10 px-2 py-1 text-white"
            >
              <option value="">— anonymous —</option>
              {households.map((h) => (
                <option key={h.id} value={h.id} className="text-black">
                  {h.city}, {h.state} · {h.age_bucket} · {h.interests.join("/")}
                </option>
              ))}
            </select>
          </>
        ) : (
          <span>Browsing this store sends test events to your pixel, so you can check your setup.</span>
        )}
        <span className="ml-auto">{pixel ? `pixel ${pixel.public_key.slice(0, 10)}…` : "no pixel"}</span>
      </div>

      {!authed && (
        <p className="bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
          Log in to AdCraft AI first so the demo store can use your pixel.
        </p>
      )}
      {authed && !pixel && (
        <p className="bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
          Set up a pixel first (Settings → Web Pixel), then reload this page.
        </p>
      )}

      {/* fake shop */}
      <header className="mx-auto flex max-w-[840px] items-center justify-between px-6 py-5">
        <button onClick={() => setPage("home")} className="text-lg font-bold text-[var(--color-text)]">
          Nimbus Goods
        </button>
        <nav className="flex gap-4 text-sm text-[var(--color-text-body)]">
          <button onClick={() => setPage("home")}>Home</button>
          <button onClick={() => setPage("product")}>Shop</button>
        </nav>
      </header>

      <main className="mx-auto max-w-[840px] px-6 pb-20">
        {page === "home" && (
          <div className="rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-10 text-center shadow-[var(--shadow-card)]">
            <h1 className="text-3xl font-bold text-[var(--color-text)]">The Cloud Mug</h1>
            <p className="mt-2 text-[var(--color-text-muted)]">Keeps coffee warm for hours. Fires a page_view on every page.</p>
            <Button className="mt-6" onClick={() => setPage("product")}>Shop now</Button>
          </div>
        )}
        {page === "product" && (
          <div className="grid gap-6 rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-8 shadow-[var(--shadow-card)] sm:grid-cols-2">
            <div className="aspect-square rounded-[var(--radius-lg)] bg-gradient-to-br from-indigo-200 to-indigo-400" />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-text)]">The Cloud Mug</h1>
              <p className="mt-1 text-xl font-semibold text-[var(--color-primary)]">$49.90</p>
              <p className="mt-3 text-sm text-[var(--color-text-body)]">Double-walled, 12oz. Added an add_to_cart event when you landed here.</p>
              <Button className="mt-6" onClick={() => setPage("checkout")}>Buy now</Button>
            </div>
          </div>
        )}
        {page === "checkout" && (
          <div className="rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-8 shadow-[var(--shadow-card)]">
            <h1 className="text-2xl font-bold text-[var(--color-text)]">Checkout</h1>
            <p className="mt-2 text-sm text-[var(--color-text-muted)]">1 × The Cloud Mug — $49.90</p>
            <Button className="mt-6" onClick={() => setPage("thankyou")}>Place order</Button>
          </div>
        )}
        {page === "thankyou" && (
          <div className="rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-10 text-center shadow-[var(--shadow-card)]">
            <h1 className="text-2xl font-bold text-[var(--color-success)]">Thank you! 🎉</h1>
            <p className="mt-2 text-[var(--color-text-muted)]">
              A <strong>purchase</strong> event ($49.90) was sent to your pixel. Check Settings → Web Pixel to see it turn green.
            </p>
            <Button className="mt-6" variant="outline" onClick={() => setPage("home")}>Back to store</Button>
          </div>
        )}
      </main>
    </div>
  );
}
