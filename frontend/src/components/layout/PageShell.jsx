import React from "react";
import Header from "./Header";

export default function PageShell({ children }) {
  return <><Header /><main className="page-shell">{children}</main></>;
}