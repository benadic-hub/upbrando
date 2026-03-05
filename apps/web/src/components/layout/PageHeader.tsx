import type { ReactNode } from "react";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import { Breadcrumb } from "@/components/ui/Breadcrumb";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
};

export function PageHeader({ title, subtitle, actions, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-2">
        {breadcrumbs ? <Breadcrumb items={breadcrumbs} /> : null}
        <h2 className="text-heading-2 text-text">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div>{actions}</div> : null}
    </div>
  );
}
