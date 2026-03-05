import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function ReportsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Reporting and analytics shell page."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Reports" }
        ]}
      />
      <Card title="Reports Module" description="Coming soon">
        <p className="text-body-lg text-muted">Operational dashboards and downloadable reports will be integrated after the core modules are finalized.</p>
      </Card>
    </div>
  );
}
