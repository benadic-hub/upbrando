import clsx from "clsx";

type BadgeProps = {
  tone?: "default" | "success" | "warning" | "danger" | "muted";
  children: string;
};

const toneClasses: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "border-primary/20 bg-primary/10 text-primary",
  success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700",
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-700",
  danger: "border-red-500/20 bg-red-500/10 text-red-700",
  muted: "border-border bg-bg text-muted"
};

export function Badge({ children, tone = "default" }: BadgeProps) {
  return <span className={clsx("inline-flex rounded-md border px-2 py-1 text-xs font-medium", toneClasses[tone])}>{children}</span>;
}
