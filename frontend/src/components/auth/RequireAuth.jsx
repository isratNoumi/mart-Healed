import React from "react";
import { Redirect, useLocation as useRouterLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const routerLocation = useRouterLocation();

  if (loading) return <p className="page-status" role="status">Checking your account...</p>;
  if (!user) {
    const next = encodeURIComponent(`${routerLocation.pathname}${routerLocation.search}`);
    return <Redirect to={`/login?next=${next}`} />;
  }
  return children;
}
