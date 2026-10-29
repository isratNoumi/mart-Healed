import React from "react";
import AddressSelector from "./AddressSelector";

const BILLING_TYPES = ["billing", "both"];

export default function BillingAddressSelector({ allowSameAsShipping, sameAsShipping, onSameChange, addresses, value, onChange, onSave, disabled }) {
  const showSelector = !allowSameAsShipping || !sameAsShipping;
  return (
    <div className="billing-selector">
      {allowSameAsShipping ? (
        <label className="checkbox-row">
          <input type="checkbox" checked={sameAsShipping} disabled={disabled} onChange={(event) => onSameChange(event.target.checked)} />
          Billing address is the same as shipping
        </label>
      ) : null}
      {showSelector ? (
        <AddressSelector
          name="billing-address"
          label="Billing address"
          addresses={addresses}
          allowedTypes={BILLING_TYPES}
          value={value}
          onChange={onChange}
          onSave={onSave}
          disabled={disabled}
        />
      ) : null}
    </div>
  );
}
