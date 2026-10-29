import React from "react";
import AddressForm from "./AddressForm";

export function formatAddress(address) {
  const line2 = address.address_line2 ? `, ${address.address_line2}` : "";
  return `${address.address_line1}${line2}, ${address.city}, ${address.state} ${address.zip_code}`;
}

export default function AddressSelector({ name, label, addresses, allowedTypes, value, onChange, onSave, disabled }) {
  const [editing, setEditing] = React.useState(null);
  const usable = addresses.filter((address) => allowedTypes.includes(address.type));

  async function handleSave(payload) {
    const previousId = editing === "new" ? null : editing.id;
    const saved = await onSave(payload, previousId);
    setEditing(null);
    onChange(saved.id, previousId);
  }

  return (
    <div className="address-selector">
      {usable.length ? (
        <fieldset className="option-group" disabled={disabled || Boolean(editing)}>
          <legend className="visually-hidden">{label}</legend>
          {usable.map((address) => (
            <div key={address.id} className={`option-card address-option${value === address.id ? " is-selected" : ""}`}>
              <label className="address-choice">
                <input type="radio" name={name} value={address.id} checked={value === address.id} onChange={() => onChange(address.id)} />
                <span className="option-body">
                  <span className="option-title">
                    {address.first_name} {address.last_name}
                    {address.is_default ? <span className="tag">Default</span> : null}
                  </span>
                  <span className="option-meta">{formatAddress(address)}</span>
                  <span className="option-meta">{address.phone}</span>
                </span>
              </label>
              <button className="link-button" type="button" onClick={() => setEditing(address)}>Edit</button>
            </div>
          ))}
        </fieldset>
      ) : (
        !editing ? <p className="muted">You don't have a saved address for this yet.</p> : null
      )}

      {editing ? (
        <AddressForm
          key={editing === "new" ? "new" : editing.id}
          idPrefix={`${name}-form`}
          initial={editing === "new" ? { type: allowedTypes.includes("both") ? "both" : allowedTypes[0] } : editing}
          submitLabel={editing === "new" ? "Save address" : "Update address"}
          onSubmit={handleSave}
          onCancel={() => setEditing(null)}
        />
      ) : (
        <button className="link-button add-link" type="button" disabled={disabled} onClick={() => setEditing("new")}>+ Add a new address</button>
      )}
    </div>
  );
}
