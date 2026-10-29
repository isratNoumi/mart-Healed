import React from "react";
import { Link, useParams } from "react-router-dom";
import OrderDetails from "../components/orders/OrderDetails";
import OrderLoadError from "../components/orders/OrderLoadError";
import useOrder from "../hooks/useOrder";

export default function OrderDetailsPage() {
  const { orderId } = useParams();
  const { loading, order, error, reload } = useOrder(orderId);

  return (
    <section className="order-page">
      <Link className="back-link" to="/account/orders">← All orders</Link>
      <p className="eyebrow">YOUR ACCOUNT</p>
      <h1>Order details</h1>
      {loading ? <p className="page-status" role="status">Loading order...</p> : null}
      {error ? <OrderLoadError error={error} onRetry={reload} /> : null}
      {order ? <OrderDetails order={order} /> : null}
    </section>
  );
}
