import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function ProjectsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        subtitle="Project management workspace scaffolding based on the design system."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Projects" }
        ]}
      />
      <Card title="Projects Module" description="Coming soon">
        <p className="text-body-lg text-muted">Project pipelines, milestones, and collaboration widgets will be added in the next phase.</p>
      </Card>
    </div>
  );
}
