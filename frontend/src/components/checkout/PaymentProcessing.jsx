import React from "react";

const MESSAGES = {
  placing: "Checking prices and stock...",
  paying: "Processing your payment..."
};

export default function PaymentProcessing({ stage }) {
  if (!MESSAGES[stage]) return null;
  return (
    <div className="processing-overlay" role="status" aria-live="assertive">
      <div className="processing-card">
        <span className="spinner" aria-hidden="true" />
        <p>{MESSAGES[stage]}</p>
        <p className="muted">Please don't close or refresh this page.</p>
      </div>
    </div>
  );
}
