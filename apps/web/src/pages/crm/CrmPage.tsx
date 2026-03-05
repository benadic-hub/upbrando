import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function CrmPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="CRM"
        subtitle="Customer relationship workspace scaffold."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "CRM" }
        ]}
      />
      <Card title="CRM Module" description="Coming soon">
        <p className="text-body-lg text-muted">Lead tracking, account history, and communication timeline components will be added in the next phase.</p>
      </Card>
    </div>
  );
}
