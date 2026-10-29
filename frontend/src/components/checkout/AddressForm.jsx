import React from "react";
import { fieldErrors } from "../../api/client";
import { US_STATES } from "../../utils/usStates";
import FormField, { describedBy } from "../forms/FormField";

const EMPTY = {
  type: "both",
  first_name: "",
  last_name: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  zip_code: "",
  phone: "",
  is_default: false
};

function validate(values) {
  const errors = {};
  ["first_name", "last_name", "address_line1", "city"].forEach((field) => {
    if (!values[field].trim()) errors[field] = "This field is required.";
  });
  if (!values.state) errors.state = "Choose a state.";
  if (!/^\d{5}(-\d{4})?$/.test(values.zip_code.trim())) errors.zip_code = "Enter a 5-digit ZIP code or ZIP+4.";
  const phone = values.phone.replace(/\D/g, "").replace(/^1(?=\d{10}$)/, "");
  if (phone.length !== 10) errors.phone = "Enter a 10-digit US phone number.";
  return errors;
}

export default function AddressForm({ initial, idPrefix, submitLabel, onSubmit, onCancel }) {
  const [values, setValues] = React.useState(() => ({ ...EMPTY, ...initial, address_line2: (initial && initial.address_line2) || "" }));
  const [errors, setErrors] = React.useState({});
  const [formError, setFormError] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const clientErrors = validate(values);
    setErrors(clientErrors);
    setFormError("");
    if (Object.keys(clientErrors).length) return;
    setSaving(true);
    try {
      await onSubmit({ ...values, address_line2: values.address_line2.trim() || null });
    } catch (requestError) {
      setErrors(fieldErrors(requestError));
      setFormError(requestError.message);
      setSaving(false);
    }
  }

  const input = (name, label, autoComplete, props = {}) => {
    const id = `${idPrefix}-${name}`;
    return (
      <FormField id={id} label={label} error={errors[name]}>
        <input
          id={id}
          autoComplete={autoComplete}
          value={values[name]}
          onChange={(event) => update(name, event.target.value)}
          aria-invalid={Boolean(errors[name])}
          aria-describedby={describedBy(id, errors[name])}
          {...props}
        />
      </FormField>
    );
  };

  return (
    <form className="inline-form" onSubmit={handleSubmit} noValidate>
      {formError ? <p className="error-message" role="alert">{formError}</p> : null}
      <div className="form-row">
        {input("first_name", "First name", "given-name")}
        {input("last_name", "Last name", "family-name")}
      </div>
      {input("address_line1", "Street address", "address-line1")}
      {input("address_line2", "Apartment, suite, etc. (optional)", "address-line2")}
      <div className="form-row form-row-3">
        {input("city", "City", "address-level2")}
        <FormField id={`${idPrefix}-state`} label="State" error={errors.state}>
          <select
            id={`${idPrefix}-state`}
            autoComplete="address-level1"
            value={values.state}
            onChange={(event) => update("state", event.target.value)}
            aria-invalid={Boolean(errors.state)}
            aria-describedby={describedBy(`${idPrefix}-state`, errors.state)}
          >
            <option value="">Select</option>
            {US_STATES.map((state) => <option key={state} value={state}>{state}</option>)}
          </select>
        </FormField>
        {input("zip_code", "ZIP code", "postal-code", { inputMode: "numeric" })}
      </div>
      {input("phone", "Phone", "tel", { type: "tel" })}
      <FormField id={`${idPrefix}-type`} label="Use this address for">
        <select id={`${idPrefix}-type`} value={values.type} onChange={(event) => update("type", event.target.value)}>
          <option value="both">Shipping and billing</option>
          <option value="shipping">Shipping only</option>
          <option value="billing">Billing only</option>
        </select>
      </FormField>
      <label className="checkbox-row">
        <input type="checkbox" checked={values.is_default} onChange={(event) => update("is_default", event.target.checked)} />
        Make this my default address
      </label>
      <div className="form-actions">
        <button className="button" type="submit" disabled={saving}>{saving ? "Saving..." : submitLabel}</button>
        <button className="link-button" type="button" onClick={onCancel} disabled={saving}>Cancel</button>
      </div>
    </form>
  );
}
