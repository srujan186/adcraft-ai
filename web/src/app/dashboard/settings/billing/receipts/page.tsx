import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="Receipts" subtitle="Download your top-up receipts." />
      <MilestonePlaceholder milestone="M7" feature="Receipts" />
    </>
  );
}
