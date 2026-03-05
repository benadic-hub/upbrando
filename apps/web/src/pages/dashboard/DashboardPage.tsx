import { useAuthStore } from "@/store/auth.store";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-5">
      <p className="text-body-lg text-muted">{label}</p>
      <p className="mt-2 text-display-4 text-text">{value}</p>
    </Card>
  );
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome, ${user?.fullName ?? "User"}`}
        subtitle="Overview snapshot for the pilot shell."
        breadcrumbs={[{ label: "Dashboard" }]}
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <StatCard label="Active Users" value="--" />
        <StatCard label="Open Tasks" value="--" />
        <StatCard label="Pending Tickets" value="--" />
      </div>
      <Card title="Quick Notes" description="Coming soon">
        <p className="text-body-lg text-muted">
          This dashboard shell now matches the design navigation structure. Module widgets will be connected in the next phase.
        </p>
      </Card>
    </div>
  );
}
