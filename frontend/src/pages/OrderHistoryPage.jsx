import React from "react";
import { Link } from "react-router-dom";
import { getOrders } from "../api/orders";
import OrderCard from "../components/orders/OrderCard";

const PAGE_SIZE = 10;

export default function OrderHistoryPage() {
  const [page, setPage] = React.useState(1);
  const [state, setState] = React.useState({ loading: true, data: null, error: "" });

  const load = React.useCallback(() => {
    let active = true;
    setState({ loading: true, data: null, error: "" });
    getOrders(page, PAGE_SIZE)
      .then((data) => { if (active) setState({ loading: false, data, error: "" }); })
      .catch((error) => { if (active) setState({ loading: false, data: null, error: error.message }); });
    return () => { active = false; };
  }, [page]);

  React.useEffect(load, [load]);

  const { loading, data, error } = state;
  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="order-page">
      <Link className="back-link" to="/account">← Account</Link>
      <p className="eyebrow">YOUR ACCOUNT</p>
      <h1>Your orders</h1>
      {loading ? <p className="page-status" role="status">Loading orders...</p> : null}
      {error ? (
        <div>
          <div className="error-message" role="alert"><p>{error}</p></div>
          <button className="button" type="button" onClick={load}>Try again</button>
        </div>
      ) : null}
      {data && !data.items.length ? (
        <div className="empty-state">
          <p>You haven't placed any orders yet.</p>
          <Link className="button" to="/products">Start shopping</Link>
        </div>
      ) : null}
      {data && data.items.length ? (
        <>
          <div className="order-list">{data.items.map((order) => <OrderCard key={order.order_id} order={order} />)}</div>
          {pageCount > 1 ? (
            <nav className="pagination" aria-label="Order pages">
              <button className="secondary-button" type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {page} of {pageCount}</span>
              <button className="secondary-button" type="button" disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Next</button>
            </nav>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
