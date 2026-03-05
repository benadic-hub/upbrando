import type { SelectHTMLAttributes } from "react";
import clsx from "clsx";

type SelectOption = {
  label: string;
  value: string;
};

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  options: SelectOption[];
};

export function Select({ label, options, className, ...props }: SelectProps) {
  return (
    <label className="flex w-full flex-col gap-1">
      {label ? <span className="text-sm font-medium text-text">{label}</span> : null}
      <select
        className={clsx(
          "h-10 rounded-md border border-border bg-surface px-3 text-sm text-text outline-none ring-primary/20 transition focus:ring-2",
          className
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
