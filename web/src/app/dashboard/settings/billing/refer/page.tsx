import { MilestonePlaceholder } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";

export default function Page() {
  return (
    <>
      <PageHeader title="Refer & earn" subtitle="Share your referral link and earn credit." />
      <MilestonePlaceholder milestone="M13" feature="Refer & earn" />
    </>
  );
}
