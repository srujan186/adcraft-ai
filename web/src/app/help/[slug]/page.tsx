import Link from "next/link";
import { notFound } from "next/navigation";

import { ARTICLES, bySlug } from "@/content/help";

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

function renderBody(body: string) {
  const blocks = body.split("\n\n");
  return blocks.map((block, i) => {
    if (block.startsWith("## ")) {
      return <h2 key={i} className="mt-6 text-lg font-semibold text-[var(--color-text)]">{block.slice(3)}</h2>;
    }
    if (block.split("\n").every((l) => l.startsWith("- "))) {
      return (
        <ul key={i} className="mt-2 list-disc space-y-1 pl-5 text-[var(--color-text-body)]">
          {block.split("\n").map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}
        </ul>
      );
    }
    return <p key={i} className="mt-3 text-[var(--color-text-body)]">{inline(block)}</p>;
  });
}

function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>,
  );
}

export default async function HelpArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const article = bySlug(slug);
  if (!article) notFound();

  return (
    <div className="mx-auto max-w-[720px] px-6 py-16">
      <Link href="/help" className="text-sm text-[var(--color-primary)]">← Help center</Link>
      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{article.category} · {article.readMins} min read</p>
      <h1 className="mt-1 text-3xl font-bold text-[var(--color-text)]">{article.title}</h1>
      <article className="mt-4 text-sm leading-relaxed">{renderBody(article.body)}</article>
    </div>
  );
}
