import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function AdministrationPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Administration"
        subtitle="System and organization administration overview."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Administration" }
        ]}
      />
      <Card title="Administration Hub" description="Coming soon">
        <p className="text-body-lg text-muted">
          Use the sidebar to access Users and Roles now. Additional administration controls will be enabled incrementally.
        </p>
      </Card>
    </div>
  );
}
