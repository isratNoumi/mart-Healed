import React from "react";
import { formatDate, formatMoney } from "../../utils/format";

function availabilityText(option) {
  if (!option.available) return option.reason;
  return option.type === "STORE_PICKUP"
    ? `Ready for pickup ${formatDate(option.estimated_date)}`
    : `Arrives by ${formatDate(option.estimated_date)}`;
}

export default function FulfillmentSelector({ options, value, onChange, disabled }) {
  return (
    <fieldset className="option-group" disabled={disabled}>
      <legend className="visually-hidden">Delivery method</legend>
      {options.map((option) => (
        <label
          key={option.type}
          className={`option-card${value === option.type ? " is-selected" : ""}${option.available ? "" : " is-unavailable"}`}
        >
          <input
            type="radio"
            name="fulfillment-type"
            value={option.type}
            checked={value === option.type}
            disabled={!option.available}
            onChange={() => onChange(option.type)}
          />
          <span className="option-body">
            <span className="option-title">{option.label}</span>
            <span className="option-meta">{availabilityText(option)}</span>
          </span>
          <span className="option-price">{option.cost === 0 ? "Free" : formatMoney(option.cost)}</span>
        </label>
      ))}
    </fieldset>
  );
}
