import React from "react";
import { Link, Redirect, useLocation as useRouterLocation } from "react-router-dom";
import { fieldErrors } from "../api/client";
import FormField, { describedBy } from "../components/forms/FormField";
import { useAuth } from "../context/AuthContext";
import { safeNextPath } from "../utils/redirect";

const EMPTY = { first_name: "", last_name: "", email: "", password: "" };

function validate(values) {
  const errors = {};
  if (!values.first_name.trim()) errors.first_name = "Enter your first name.";
  if (!values.last_name.trim()) errors.last_name = "Enter your last name.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.email.trim())) errors.email = "Enter a valid email address.";
  if (values.password.length < 8) errors.password = "Use at least 8 characters.";
  return errors;
}

export default function RegisterPage() {
  const { user, loading, signUp } = useAuth();
  const { search } = useRouterLocation();
  const next = safeNextPath(search);
  const [values, setValues] = React.useState(EMPTY);
  const [errors, setErrors] = React.useState({});
  const [formError, setFormError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  if (!loading && user) return <Redirect to={next} />;

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    const clientErrors = validate(values);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;
    setSubmitting(true);
    try {
      await signUp(values);
    } catch (requestError) {
      setErrors(fieldErrors(requestError));
      setFormError(requestError.message);
      setSubmitting(false);
    }
  }

  const field = (name, label, type, autoComplete, hint) => (
    <FormField id={`register-${name}`} label={label} error={errors[name]} hint={hint}>
      <input
        id={`register-${name}`}
        type={type}
        autoComplete={autoComplete}
        value={values[name]}
        onChange={(event) => update(name, event.target.value)}
        aria-invalid={Boolean(errors[name])}
        aria-describedby={describedBy(`register-${name}`, errors[name], hint)}
      />
    </FormField>
  );

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">JOIN BUILDMART</p>
        <h1>Create an account</h1>
        {formError ? <p className="error-message" role="alert">{formError}</p> : null}
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-row">
            {field("first_name", "First name", "text", "given-name")}
            {field("last_name", "Last name", "text", "family-name")}
          </div>
          {field("email", "Email", "email", "email")}
          {field("password", "Password", "password", "new-password", "At least 8 characters.")}
          <button className="button auth-submit" type="submit" disabled={submitting}>{submitting ? "Creating account..." : "Create account"}</button>
        </form>
        <p className="auth-switch">Already have an account? <Link to={`/login${search}`}>Sign in</Link></p>
      </div>
    </section>
  );
}
