import React from "react";

export default function StorePickupSelector({ stores, value, onChange, productNames, disabled }) {
  if (!stores.length) return <p className="muted">There are no pickup stores in your area.</p>;

  return (
    <fieldset className="option-group" disabled={disabled}>
      <legend className="section-label">Choose a pickup store</legend>
      {stores.map((store) => {
        const missing = store.unavailable_product_ids.map((id) => productNames[id] || "An item").join(", ");
        return (
          <label
            key={store.store_id}
            className={`option-card${value === store.store_id ? " is-selected" : ""}${store.all_items_available ? "" : " is-unavailable"}`}
          >
            <input
              type="radio"
              name="pickup-store"
              value={store.store_id}
              checked={value === store.store_id}
              disabled={!store.all_items_available}
              onChange={() => onChange(store.store_id)}
            />
            <span className="option-body">
              <span className="option-title">{store.name}</span>
              <span className="option-meta">{store.address}, {store.city}, {store.state} {store.zip_code}</span>
              <span className={store.all_items_available ? "stock-ok" : "stock-short"}>
                {store.all_items_available ? "All items in stock" : `Not enough stock: ${missing}`}
              </span>
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}
