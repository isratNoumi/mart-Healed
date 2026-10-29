import React from "react";
import { FULFILLMENT_LABELS, formatDate, formatDateTime, formatMoney, formatStatus } from "../../utils/format";
import { formatAddress } from "../checkout/AddressSelector";
import OrderStatusTimeline from "./OrderStatusTimeline";

function AddressBlock({ title, address }) {
  if (!address) return null;
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      <p>{address.first_name} {address.last_name}</p>
      <p className="muted">{formatAddress(address)}</p>
      {address.phone ? <p className="muted">{address.phone}</p> : null}
    </div>
  );
}

export default function OrderDetails({ order }) {
  const { fulfillment, payment } = order;
  const isPickup = fulfillment && fulfillment.type === "STORE_PICKUP";

  return (
    <div className="order-details">
      <div className="order-meta">
        <span>Order <strong>{order.order_number}</strong></span>
        <span>Placed {formatDateTime(order.created_at)}</span>
        <span className="status-pill">{formatStatus(order.status)}</span>
      </div>

      <div className="order-details-layout">
        <section aria-labelledby="order-items-heading">
          <h2 id="order-items-heading">Items</h2>
          <table className="order-items-table">
            <thead>
              <tr><th scope="col">Product</th><th scope="col">Qty</th><th scope="col">Unit price</th><th scope="col">Subtotal</th></tr>
            </thead>
            <tbody>
              {order.items.map((item) => (
                <tr key={`${item.product_id}-${item.variant_id || ""}`}>
                  <td>
                    <span className="order-item-product">
                      {item.image_url ? <img src={item.image_url} alt="" /> : null}
                      <span><span className="product-name">{item.product_name}</span><span className="muted">SKU {item.sku}</span></span>
                    </span>
                  </td>
                  <td>{item.quantity}</td>
                  <td>{formatMoney(item.unit_price)}</td>
                  <td>{formatMoney(item.subtotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="detail-grid">
            {fulfillment ? (
              <div className="detail-block">
                <h3>{FULFILLMENT_LABELS[fulfillment.type]}</h3>
                <p><span className="status-pill">{formatStatus(fulfillment.status)}</span></p>
                {isPickup ? <p>{fulfillment.store_name}<br /><span className="muted">{fulfillment.store_address}</span></p> : null}
                {fulfillment.estimated_date ? <p className="muted">{isPickup ? "Pickup from" : "Estimated arrival"} {formatDate(fulfillment.estimated_date)}</p> : null}
                {fulfillment.tracking_number ? <p className="muted">Tracking: {fulfillment.tracking_number}</p> : null}
              </div>
            ) : null}
            {!isPickup ? <AddressBlock title="Shipping address" address={order.shipping_address} /> : null}
            <AddressBlock title="Billing address" address={order.billing_address} />
            {payment ? (
              <div className="detail-block">
                <h3>Payment</h3>
                <p>{payment.card_display || "Card"}</p>
                <p><span className="status-pill">{formatStatus(order.payment_status)}</span></p>
                {payment.transaction_id ? <p className="muted">Transaction {payment.transaction_id}</p> : null}
              </div>
            ) : null}
          </div>
        </section>

        <aside className="order-summary" aria-labelledby="order-totals-heading">
          <h2 id="order-totals-heading">Order total</h2>
          <div className="summary-row"><span>Subtotal</span><span>{formatMoney(order.subtotal)}</span></div>
          <div className="summary-row"><span>Discount</span><span>{order.discount > 0 ? `−${formatMoney(order.discount)}` : formatMoney(0)}</span></div>
          <div className="summary-row"><span>Shipping</span><span>{order.shipping_cost === 0 ? "Free" : formatMoney(order.shipping_cost)}</span></div>
          <div className="summary-row"><span>Tax</span><span>{formatMoney(order.tax)}</span></div>
          <div className="summary-row summary-total"><strong>Total</strong><strong>{formatMoney(order.total)}</strong></div>
          <h2 className="timeline-heading">Status</h2>
          <OrderStatusTimeline events={order.timeline} />
        </aside>
      </div>
    </div>
  );
}
