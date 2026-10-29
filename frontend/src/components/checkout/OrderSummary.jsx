import React from "react";
import { FULFILLMENT_LABELS, formatDate, formatMoney } from "../../utils/format";

export default function OrderSummary({ quote, updating, children }) {
  const isPickup = quote.fulfillment_type === "STORE_PICKUP";
  return (
    <aside className="order-summary" aria-labelledby="order-summary-heading" aria-busy={updating}>
      <h2 id="order-summary-heading">Order summary</h2>
      <ul className="summary-lines">
        {quote.lines.map((line) => (
          <li key={line.cart_item_id} className="summary-line">
            <img src={line.image_url} alt="" />
            <span className="summary-line-text">
              <span className="summary-line-name">{line.product_name}</span>
              <span className="muted">{line.variant_name ? `${line.variant_name} · ` : ""}Qty {line.quantity}</span>
            </span>
            <span>{line.line_total === null ? "—" : formatMoney(line.line_total)}</span>
          </li>
        ))}
      </ul>
      <div className="summary-row"><span>Subtotal</span><span>{formatMoney(quote.subtotal)}</span></div>
      {quote.discount > 0 ? <div className="summary-row"><span>Discount</span><span>−{formatMoney(quote.discount)}</span></div> : null}
      <div className="summary-row">
        <span>{quote.fulfillment_type ? FULFILLMENT_LABELS[quote.fulfillment_type] : "Shipping"}</span>
        <span>{!quote.fulfillment_type ? "—" : quote.shipping_cost === 0 ? "Free" : formatMoney(quote.shipping_cost)}</span>
      </div>
      <div className="summary-row"><span>Estimated tax</span><span>{formatMoney(quote.tax)}</span></div>
      <div className="summary-row summary-total"><strong>Total</strong><strong>{formatMoney(quote.total)}</strong></div>
      {quote.estimated_date ? (
        <p className="muted summary-date">{isPickup ? "Ready for pickup" : "Estimated arrival"}: {formatDate(quote.estimated_date)}</p>
      ) : null}
      {updating ? <p className="muted" role="status">Updating totals...</p> : null}
      {children}
    </aside>
  );
}
