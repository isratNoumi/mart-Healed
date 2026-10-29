import React from "react";
import { cardBrand, digitsOnly, formatCardNumber } from "../../utils/card";
import FormField, { describedBy } from "../forms/FormField";

const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1);

export default function PaymentForm({ card, onChange, errors, saveCard, onSaveCardChange, disabled }) {
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 16 }, (_, index) => currentYear + index);
  const brand = cardBrand(digitsOnly(card.card_number));
  const cvvLength = brand === "AMEX" ? 4 : 3;

  function update(field, value) {
    onChange({ ...card, [field]: value });
  }

  return (
    <fieldset className="payment-form" disabled={disabled}>
      <legend className="visually-hidden">New card details</legend>
      <FormField id="card-name" label="Name on card" error={errors.cardholder_name}>
        <input
          id="card-name"
          autoComplete="cc-name"
          value={card.cardholder_name}
          onChange={(event) => update("cardholder_name", event.target.value)}
          aria-invalid={Boolean(errors.cardholder_name)}
          aria-describedby={describedBy("card-name", errors.cardholder_name)}
        />
      </FormField>
      <FormField id="card-number" label="Card number" error={errors.card_number} hint={brand ? `${brand} card` : undefined}>
        <input
          id="card-number"
          inputMode="numeric"
          autoComplete="cc-number"
          value={card.card_number}
          onChange={(event) => update("card_number", formatCardNumber(event.target.value))}
          aria-invalid={Boolean(errors.card_number)}
          aria-describedby={describedBy("card-number", errors.card_number, brand)}
        />
      </FormField>
      <div className="form-row form-row-3">
        <FormField id="card-expiry-month" label="Expiry month" error={errors.expiry}>
          <select
            id="card-expiry-month"
            autoComplete="cc-exp-month"
            value={card.expiry_month}
            onChange={(event) => update("expiry_month", event.target.value)}
            aria-invalid={Boolean(errors.expiry)}
            aria-describedby={describedBy("card-expiry-month", errors.expiry)}
          >
            <option value="">MM</option>
            {MONTHS.map((month) => <option key={month} value={month}>{String(month).padStart(2, "0")}</option>)}
          </select>
        </FormField>
        <FormField id="card-expiry-year" label="Expiry year">
          <select
            id="card-expiry-year"
            autoComplete="cc-exp-year"
            value={card.expiry_year}
            onChange={(event) => update("expiry_year", event.target.value)}
            aria-invalid={Boolean(errors.expiry)}
          >
            <option value="">YYYY</option>
            {years.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </FormField>
        <FormField id="card-cvv" label="Security code" error={errors.cvv}>
          <input
            id="card-cvv"
            type="password"
            inputMode="numeric"
            autoComplete="cc-csc"
            maxLength={cvvLength}
            value={card.cvv}
            onChange={(event) => update("cvv", digitsOnly(event.target.value).slice(0, cvvLength))}
            aria-invalid={Boolean(errors.cvv)}
            aria-describedby={describedBy("card-cvv", errors.cvv)}
          />
        </FormField>
      </div>
      <label className="checkbox-row">
        <input type="checkbox" checked={saveCard} onChange={(event) => onSaveCardChange(event.target.checked)} />
        Save this card for future purchases
      </label>
      <p className="field-hint">We never store your full card number or security code.</p>
    </fieldset>
  );
}
