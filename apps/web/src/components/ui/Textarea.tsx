import type { TextareaHTMLAttributes } from "react";
import clsx from "clsx";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  error?: string;
};

export function Textarea({ label, error, className, ...props }: TextareaProps) {
  return (
    <label className="flex w-full flex-col gap-1">
      {label ? <span className="text-sm font-medium text-text">{label}</span> : null}
      <textarea
        className={clsx(
          "min-h-32 rounded-md border border-border bg-surface p-3 text-sm text-text outline-none ring-primary/20 transition placeholder:text-muted focus:ring-2",
          className
        )}
        {...props}
      />
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
