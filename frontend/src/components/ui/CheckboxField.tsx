import type { InputHTMLAttributes } from "react";

interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "type"> {
  label: string;
  hint?: string;
}

let idCounter = 0;
function nextId(): string {
  idCounter += 1;
  return `checkbox-${idCounter}`;
}

export function CheckboxField({ label, hint, id, ...rest }: CheckboxFieldProps) {
  const fieldId = id ?? nextId();
  return (
    <div className="flex items-start gap-2">
      <input
        id={fieldId}
        type="checkbox"
        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800"
        {...rest}
      />
      <div>
        <label htmlFor={fieldId} className="text-sm font-medium text-slate-700 dark:text-slate-200">
          {label}
        </label>
        {hint && <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
      </div>
    </div>
  );
}
