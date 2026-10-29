import React from "react";

export default function CheckoutProgress({ steps }) {
  const currentIndex = steps.findIndex((step) => !step.complete);
  return (
    <ol className="checkout-progress" aria-label="Checkout progress">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={step.complete ? "is-complete" : index === currentIndex ? "is-current" : ""}
          aria-current={index === currentIndex ? "step" : undefined}
        >
          <span className="step-marker" aria-hidden="true">{step.complete ? "✓" : index + 1}</span>
          <span>{step.label}</span>
          {step.complete ? <span className="visually-hidden"> (complete)</span> : null}
        </li>
      ))}
    </ol>
  );
}
