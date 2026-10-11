import Link from "next/link";

import { ARTICLES } from "@/content/help";
import { PRODUCT_NAME } from "@/lib/utils";

export default function HelpCenterPage() {
  return (
    <div className="mx-auto max-w-[760px] px-6 py-16">
      <h1 className="text-3xl font-bold text-[var(--color-text)]">{PRODUCT_NAME} Help center</h1>
      <p className="mt-2 text-[var(--color-text-body)]">Short guides to get the most out of streaming-TV advertising.</p>
      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {ARTICLES.map((a) => (
          <Link
            key={a.slug}
            href={`/help/${a.slug}`}
            className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)] transition-colors hover:border-[var(--color-border-strong)]"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{a.category}</p>
            <p className="mt-1 font-medium text-[var(--color-text)]">{a.title}</p>
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">{a.readMins} min read</p>
          </Link>
        ))}
      </div>
      <div className="mt-8">
        <Link href="/dashboard" className="text-sm font-medium text-[var(--color-primary)]">← Back to dashboard</Link>
      </div>
    </div>
  );
}
