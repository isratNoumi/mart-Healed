import React from "react";

export default function PaymentError({ error }) {
  if (!error) return null;
  let hint = "Please try again or use a different payment method.";
  if (!error.canRetry) {
    hint = "This checkout was cancelled after too many failed attempts. Placing your order again will start a new checkout.";
  } else if (error.attemptsRemaining !== undefined) {
    hint = `You can try again or use a different card. ${error.attemptsRemaining} ${error.attemptsRemaining === 1 ? "attempt" : "attempts"} left.`;
  }

  return (
    <div className="error-message payment-error" role="alert">
      <strong>Payment not completed</strong>
      <p>{error.message}</p>
      <p>{hint} Your cart has been kept.</p>
    </div>
  );
}
