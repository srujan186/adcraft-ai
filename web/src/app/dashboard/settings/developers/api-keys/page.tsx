import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="API keys" subtitle="Create and manage API keys." />
      <MilestonePlaceholder milestone="M1" feature="API keys" />
    </>
  );
}
