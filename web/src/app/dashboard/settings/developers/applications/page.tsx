import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="My applications" subtitle="OAuth applications you have created." />
      <MilestonePlaceholder milestone="M1" feature="My applications" />
    </>
  );
}
