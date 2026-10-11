import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="Integrations marketplace" subtitle="Connect your marketing tools and data sources." />
      <MilestonePlaceholder milestone="M6" feature="Integrations marketplace" />
    </>
  );
}
