import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  description?: string;
  actions?: ReactNode;
};

export function Card({ title, description, actions, children, className, ...props }: CardProps) {
  return (
    <section className={clsx("rounded-lg border border-border bg-surface p-6 shadow-sm", className)} {...props}>
      {title || description || actions ? (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title ? <h3 className="text-heading-4 text-text">{title}</h3> : null}
            {description ? <p className="mt-1 text-body-lg text-muted">{description}</p> : null}
          </div>
          {actions ? <div>{actions}</div> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}
