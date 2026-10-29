import React from "react";

export default function FormField({ id, label, error, hint, children }) {
  return (
    <div className={`form-field${error ? " has-error" : ""}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error ? <p className="field-hint" id={`${id}-hint`}>{hint}</p> : null}
      {error ? <p className="field-error" id={`${id}-error`}>{error}</p> : null}
    </div>
  );
}

export function describedBy(id, error, hint) {
  if (error) return `${id}-error`;
  return hint ? `${id}-hint` : undefined;
}
