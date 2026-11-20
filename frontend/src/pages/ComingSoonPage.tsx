import { EmptyState, PageHeader } from "../components/ui";

interface ComingSoonPageProps {
  title: string;
  description: string;
}

/** Shared placeholder body for not-yet-built timetable-workspace screens. */
export function ComingSoonPage({ title, description }: ComingSoonPageProps) {
  return (
    <div>
      <PageHeader title={title} description={description} />
      <EmptyState title="Coming soon" description="This screen will be built as part of the timetable workspace." />
    </div>
  );
}
