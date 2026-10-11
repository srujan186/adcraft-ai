import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="Installed integrations" subtitle="Your connected integrations." />
      <MilestonePlaceholder milestone="M6" feature="Installed integrations" />
    </>
  );
}
