import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";

export function RecruitmentPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Recruitment"
        subtitle="Hiring and recruitment shell page."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Recruitment" }
        ]}
      />
      <Card title="Recruitment Module" description="Coming soon">
        <p className="text-body-lg text-muted">Candidate funnel, interviews, and offer management components will be added in the next milestone.</p>
      </Card>
    </div>
  );
}
