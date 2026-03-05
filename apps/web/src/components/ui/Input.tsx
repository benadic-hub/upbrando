import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <label className="flex w-full flex-col gap-1">
      {label ? <span className="text-sm font-medium text-text">{label}</span> : null}
      <input
        className={clsx(
          "h-10 rounded-md border border-border bg-surface px-3 text-sm text-text outline-none ring-primary/20 transition placeholder:text-muted focus:ring-2",
          className
        )}
        {...props}
      />
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
