import React from "react";

export default function CheckoutError({ message, issues = [] }) {
  const blocking = issues.filter((issue) => issue.blocking);
  const notes = issues.filter((issue) => !issue.blocking);
  if (!message && !blocking.length && !notes.length) return null;

  return (
    <div className="checkout-messages">
      {message || blocking.length ? (
        <div className="error-message" role="alert">
          {message ? <p>{message}</p> : null}
          {blocking.length ? (
            <ul className="issue-list">
              {blocking.map((issue) => <li key={`${issue.code}-${issue.product_id || ""}`}>{issue.message}</li>)}
            </ul>
          ) : null}
        </div>
      ) : null}
      {notes.length ? (
        <div className="notice" role="status">
          <ul className="issue-list">
            {notes.map((issue) => <li key={`${issue.code}-${issue.product_id || ""}`}>{issue.message}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
