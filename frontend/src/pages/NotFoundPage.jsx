import React from "react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="empty-state">
      <h1>Page not found</h1>
      <p>The page you're looking for doesn't exist or has moved.</p>
      <Link className="button" to="/">Go to the home page</Link>
    </section>
  );
}
