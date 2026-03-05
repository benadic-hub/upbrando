import type { SVGProps } from "react";

export type IconName =
  | "dashboard"
  | "projects"
  | "crm"
  | "hrm"
  | "finance"
  | "recruitment"
  | "administration"
  | "reports"
  | "users"
  | "roles"
  | "settings"
  | "search"
  | "notification"
  | "chevron-right"
  | "chevron-down"
  | "menu";

type IconProps = SVGProps<SVGSVGElement> & {
  name: IconName;
};

export function Icon({ name, className, ...props }: IconProps) {
  const common = "h-4 w-4";
  const cls = className ? `${common} ${className}` : common;

  switch (name) {
    case "dashboard":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <rect x="3" y="3" width="8" height="8" rx="2" />
          <rect x="13" y="3" width="8" height="5" rx="2" />
          <rect x="13" y="10" width="8" height="11" rx="2" />
          <rect x="3" y="13" width="8" height="8" rx="2" />
        </svg>
      );
    case "projects":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M3 7h18" />
          <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
          <rect x="3" y="7" width="18" height="14" rx="2" />
        </svg>
      );
    case "crm":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <circle cx="9" cy="8" r="3" />
          <path d="M3 20a6 6 0 0 1 12 0" />
          <circle cx="17.5" cy="9.5" r="2.5" />
          <path d="M15 20a4.5 4.5 0 0 1 6 0" />
        </svg>
      );
    case "hrm":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M12 21s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 11c0 5.5-7 10-7 10Z" />
        </svg>
      );
    case "finance":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M12 3v18" />
          <path d="M16.5 7.5c0-1.7-1.9-3-4.5-3s-4.5 1.3-4.5 3 1.9 3 4.5 3 4.5 1.3 4.5 3-1.9 3-4.5 3-4.5-1.3-4.5-3" />
        </svg>
      );
    case "recruitment":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
          <path d="M11 8v6M8 11h6" />
        </svg>
      );
    case "administration":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M12 3 4 7v6c0 4.5 3 7.5 8 8 5-.5 8-3.5 8-8V7l-8-4Z" />
          <path d="M9 12h6" />
        </svg>
      );
    case "reports":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M5 20h14" />
          <path d="M7 16V9" />
          <path d="M12 16V5" />
          <path d="M17 16v-3" />
        </svg>
      );
    case "users":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <circle cx="9" cy="8.5" r="2.5" />
          <path d="M4.5 19a4.5 4.5 0 0 1 9 0" />
          <circle cx="16.5" cy="9.5" r="2" />
          <path d="M14.5 18.5a3.5 3.5 0 0 1 5 0" />
        </svg>
      );
    case "roles":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M12 3 4 7v6c0 4.5 3 7.5 8 8 5-.5 8-3.5 8-8V7l-8-4Z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      );
    case "settings":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.1a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.1a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2h.1a1 1 0 0 0 .5-.9V4a2 2 0 1 1 4 0v.1a1 1 0 0 0 .6.9h.1a1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1v.1a1 1 0 0 0 .9.5H20a2 2 0 1 1 0 4h-.1a1 1 0 0 0-.9.6Z" />
        </svg>
      );
    case "search":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
      );
    case "notification":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M6 9a6 6 0 1 1 12 0v5l2 2H4l2-2V9Z" />
          <path d="M10 19a2 2 0 0 0 4 0" />
        </svg>
      );
    case "chevron-down":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="2" {...props}>
          <path d="m6 9 6 6 6-6" />
        </svg>
      );
    case "menu":
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      );
    case "chevron-right":
    default:
      return (
        <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="2" {...props}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );
  }
}
