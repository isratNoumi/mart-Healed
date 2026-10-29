import React from "react";
import { Link, Redirect, useLocation as useRouterLocation } from "react-router-dom";
import FormField, { describedBy } from "../components/forms/FormField";
import { useAuth } from "../context/AuthContext";
import { safeNextPath } from "../utils/redirect";

export default function LoginPage() {
  const { user, loading, signIn } = useAuth();
  const { search } = useRouterLocation();
  const next = safeNextPath(search);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  if (!loading && user) return <Redirect to={next} />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setSubmitting(true);
    try {
      await signIn({ email, password });
    } catch (requestError) {
      setError(requestError.message);
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">WELCOME BACK</p>
        <h1>Sign in</h1>
        {next === "/checkout" ? <p className="muted">Sign in to finish checking out. Your cart will be saved to your account.</p> : null}
        {error ? <p className="error-message" role="alert">{error}</p> : null}
        <form onSubmit={handleSubmit} noValidate>
          <FormField id="login-email" label="Email">
            <input id="login-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </FormField>
          <FormField id="login-password" label="Password">
            <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby={describedBy("login-password")} />
          </FormField>
          <button className="button auth-submit" type="submit" disabled={submitting}>{submitting ? "Signing in..." : "Sign in"}</button>
        </form>
        <p className="auth-switch">New to BuildMart? <Link to={`/register${search}`}>Create an account</Link></p>
      </div>
    </section>
  );
}
