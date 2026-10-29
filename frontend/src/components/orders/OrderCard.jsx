import React from "react";
import { Link } from "react-router-dom";
import { FULFILLMENT_LABELS, formatDate, formatMoney, formatStatus } from "../../utils/format";

export default function OrderCard({ order }) {
  return (
    <article className="order-card">
      <div className="order-card-header">
        <div>
          <h2><Link to={`/account/orders/${order.order_id}`}>Order {order.order_number}</Link></h2>
          <p className="muted">Placed {formatDate(order.created_at)} · {order.item_count} {order.item_count === 1 ? "item" : "items"}</p>
        </div>
        <strong className="order-card-total">{formatMoney(order.total)}</strong>
      </div>
      <dl className="order-card-statuses">
        <div><dt>Order</dt><dd><span className="status-pill">{formatStatus(order.status)}</span></dd></div>
        <div><dt>Payment</dt><dd><span className="status-pill">{formatStatus(order.payment_status)}</span></dd></div>
        <div><dt>{order.fulfillment_type ? FULFILLMENT_LABELS[order.fulfillment_type] : "Fulfillment"}</dt><dd><span className="status-pill">{formatStatus(order.fulfillment_status)}</span></dd></div>
      </dl>
      <Link className="link-button" to={`/account/orders/${order.order_id}`}>View order details</Link>
    </article>
  );
}
