import { notFound } from "next/navigation";
import type { Metadata } from "next";
import MarketingPage from "../../components/MarketingPage";
import { FEATURES } from "../../content/features";
import { findBySlug } from "../../content/types";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return FEATURES.map((i) => ({ slug: i.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const content = findBySlug(FEATURES, slug);
  if (!content) return {};
  return {
    title: `${content.title} — AdCraft AI`,
    description: content.metaDescription,
  };
}

export default async function FeaturePage({ params }: Props) {
  const { slug } = await params;
  const content = findBySlug(FEATURES, slug);
  if (!content) notFound();
  return <MarketingPage content={content} />;
}
