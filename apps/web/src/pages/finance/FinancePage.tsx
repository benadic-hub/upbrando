import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function FinancePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Finance & Accounts"
        subtitle="Finance and accounting module scaffold."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Finance & Accounts" }
        ]}
      />
      <Card title="Finance & Accounts" description="Coming soon">
        <p className="text-body-lg text-muted">Budget, expenses, invoicing, and account dashboards will be implemented in the business-logic phase.</p>
      </Card>
    </div>
  );
}
