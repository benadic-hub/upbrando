import { Link } from "react-router-dom";
import { Icon } from "./Icon";

export type BreadcrumbItem = {
  label: string;
  to?: string;
};

type BreadcrumbProps = {
  items: BreadcrumbItem[];
};

export function Breadcrumb({ items }: BreadcrumbProps) {
  if (!items.length) {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-2 text-body-lg text-muted">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className="flex items-center gap-2">
              {item.to && !isLast ? (
                <Link className="transition hover:text-text" to={item.to}>
                  {item.label}
                </Link>
              ) : (
                <span className={isLast ? "font-medium text-text" : ""}>{item.label}</span>
              )}
              {!isLast ? <Icon name="chevron-right" className="h-3.5 w-3.5 text-muted-soft" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
