import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="Invoices" subtitle="Download your invoices." />
      <MilestonePlaceholder milestone="M7" feature="Invoices" />
    </>
  );
}
