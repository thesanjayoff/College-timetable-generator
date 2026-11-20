import type { SelectHTMLAttributes } from "react";
import { Field, controlClasses } from "./Field";

export interface SelectOption {
  value: string | number;
  label: string;
}

interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "className"> {
  label: string;
  error?: string;
  hint?: string;
  options: SelectOption[];
  placeholder?: string;
  containerClassName?: string;
}

let idCounter = 0;
function nextId(): string {
  idCounter += 1;
  return `select-${idCounter}`;
}

export function SelectField({
  label,
  error,
  hint,
  options,
  placeholder,
  id,
  containerClassName,
  required,
  ...rest
}: SelectFieldProps) {
  const fieldId = id ?? nextId();
  return (
    <Field label={label} htmlFor={fieldId} error={error} hint={hint} required={required} className={containerClassName}>
      <select id={fieldId} className={controlClasses(error)} aria-invalid={!!error} {...rest}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </Field>
  );
}
