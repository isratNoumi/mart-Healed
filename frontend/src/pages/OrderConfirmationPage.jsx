import React from "react";
import { Link, useParams } from "react-router-dom";
import OrderDetails from "../components/orders/OrderDetails";
import OrderLoadError from "../components/orders/OrderLoadError";
import useOrder from "../hooks/useOrder";
import { formatDate } from "../utils/format";

export default function OrderConfirmationPage() {
  const { orderId } = useParams();
  const { loading, order, error, reload } = useOrder(orderId);

  if (loading) return <section><p className="page-status" role="status">Loading your order...</p></section>;
  if (error) return <section><h1>Order confirmation</h1><OrderLoadError error={error} onRetry={reload} /></section>;

  const confirmed = order.payment_status === "PAID";
  const fulfillment = order.fulfillment;
  const isPickup = fulfillment && fulfillment.type === "STORE_PICKUP";

  return (
    <section className="confirmation-page">
      {confirmed ? (
        <div className="confirmation-banner" role="status">
          <span className="confirmation-check" aria-hidden="true">✓</span>
          <div>
            <h1>Thank you for your order!</h1>
            <p>Order <strong>#{order.order_number}</strong> is confirmed.</p>
            {fulfillment && fulfillment.estimated_date ? (
              <p>{isPickup ? `Ready for pickup at ${fulfillment.store_name} from` : "Estimated arrival"} {formatDate(fulfillment.estimated_date)}.</p>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="notice" role="status">
          <h1>Order {order.order_number}</h1>
          <p>This order hasn't been paid yet, so it isn't confirmed.</p>
        </div>
      )}
      <OrderDetails order={order} />
      <div className="form-actions">
        <Link className="button" to="/products">Continue shopping</Link>
        <Link className="link-button" to="/account/orders">View all orders</Link>
      </div>
    </section>
  );
}
