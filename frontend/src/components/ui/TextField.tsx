import type { InputHTMLAttributes } from "react";
import { Field, controlClasses } from "./Field";

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "className"> {
  label: string;
  error?: string;
  hint?: string;
  containerClassName?: string;
}

let idCounter = 0;
function nextId(): string {
  idCounter += 1;
  return `field-${idCounter}`;
}

export function TextField({ label, error, hint, id, containerClassName, required, ...rest }: TextFieldProps) {
  const fieldId = id ?? nextId();
  return (
    <Field label={label} htmlFor={fieldId} error={error} hint={hint} required={required} className={containerClassName}>
      <input id={fieldId} className={controlClasses(error)} aria-invalid={!!error} {...rest} />
    </Field>
  );
}
