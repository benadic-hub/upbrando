import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Administration Settings"
        subtitle="Organization-level settings placeholder."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Administration", to: "/administration" },
          { label: "Settings" }
        ]}
      />
      <Card title="Settings Module" description="Coming soon">
        <p className="text-body-lg text-muted">
          Configuration controls for policies, notifications, and integrations will be available in upcoming releases.
        </p>
      </Card>
    </div>
  );
}
