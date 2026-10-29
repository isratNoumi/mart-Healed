import React from "react";

export default function PaymentMethodSelector({ methods, value, onChange, disabled }) {
  return (
    <fieldset className="option-group" disabled={disabled}>
      <legend className="visually-hidden">Payment method</legend>
      {methods.map((method) => (
        <label
          key={method.id}
          className={`option-card${value === method.id ? " is-selected" : ""}${method.is_expired ? " is-unavailable" : ""}`}
        >
          <input
            type="radio"
            name="payment-method"
            checked={value === method.id}
            disabled={method.is_expired}
            onChange={() => onChange(method.id)}
          />
          <span className="option-body">
            <span className="option-title">
              {method.display}
              {method.is_default ? <span className="tag">Default</span> : null}
            </span>
            <span className="option-meta">
              {method.is_expired ? "Expired" : "Expires"} {String(method.expiry_month).padStart(2, "0")}/{String(method.expiry_year).slice(-2)}
            </span>
          </span>
        </label>
      ))}
      <label className={`option-card${value === "new" ? " is-selected" : ""}`}>
        <input type="radio" name="payment-method" checked={value === "new"} onChange={() => onChange("new")} />
        <span className="option-body">
          <span className="option-title">Use a new card</span>
          <span className="option-meta">Visa, Mastercard, American Express or Discover</span>
        </span>
      </label>
    </fieldset>
  );
}
