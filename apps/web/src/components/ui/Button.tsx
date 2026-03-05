import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import clsx from "clsx";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "danger" | "ghost";
    loading?: boolean;
  }
>;

const baseClasses =
  "inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "border-primary bg-primary text-white hover:bg-primary/90",
  secondary: "border-border bg-surface text-text hover:bg-bg",
  danger: "border-red-600 bg-red-600 text-white hover:bg-red-700",
  ghost: "border-transparent bg-transparent text-text hover:bg-bg"
};

export function Button({ children, className, variant = "primary", loading = false, ...props }: ButtonProps) {
  return (
    <button className={clsx(baseClasses, variantClasses[variant], className)} disabled={loading || props.disabled} {...props}>
      {loading ? "Loading..." : children}
    </button>
  );
}
