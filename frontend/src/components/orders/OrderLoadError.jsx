import React from "react";
import { Link } from "react-router-dom";

export default function OrderLoadError({ error, onRetry }) {
  if (error.status === 404) {
    return (
      <div className="empty-state">
        <p>We couldn't find that order.</p>
        <Link className="button" to="/account/orders">View your orders</Link>
      </div>
    );
  }
  return (
    <div>
      <div className="error-message" role="alert"><p>{error.message}</p></div>
      <button className="button" type="button" onClick={onRetry}>Try again</button>
    </div>
  );
}
