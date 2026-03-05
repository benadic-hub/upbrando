import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function HrmPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="HRM"
        subtitle="Human resource management shell page."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "HRM" }
        ]}
      />
      <Card title="HRM Module" description="Coming soon">
        <p className="text-body-lg text-muted">Employee records, leave workflows, and performance sections will be connected in upcoming iterations.</p>
      </Card>
    </div>
  );
}
