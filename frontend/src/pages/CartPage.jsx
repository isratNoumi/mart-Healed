import React from "react";
import { Link, useHistory } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useLocation } from "../context/LocationContext";

export default function CartPage() {
  const { cart, loading, updateItem, removeItem } = useCart();
  const { location } = useLocation();
  const history = useHistory();
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  if (loading) return <section aria-busy="true"><h1>Your cart</h1><p role="status">Loading cart...</p></section>;

  async function changeQuantity(item, quantity) {
    setError("");
    setBusy(true);
    try {
      await updateItem(item.id, {
        quantity,
        region_id: location ? location.region.id : undefined,
        store_id: location ? location.store.id : undefined
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(itemId) {
    setError("");
    setBusy(true);
    try {
      await removeItem(itemId);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <p className="eyebrow">YOUR PROJECT</p>
      <h1 className="listing-title">Your cart</h1>
      {error ? <p className="error-message" role="alert">{error}</p> : null}
      {!cart || !cart.items.length ? <div className="empty-state"><p>Your cart is empty.</p><Link className="button" to="/products">Shop products</Link></div> : (
        <div className="cart-layout">
          <div className="cart-items"><div className="cart-items-heading"><span>Product</span><span>Quantity</span><span>Total</span></div>{cart.items.map((item) => <article className="cart-item" key={item.id}>
            <div className="cart-product"><div className="cart-image"><img src={item.image_url} alt={item.product_name} /></div><div><Link className="product-name" to={`/products/${item.product_id}`}>{item.product_name}</Link>{item.variant_name ? <p className="muted">{item.variant_name}</p> : null}<p className="muted">${item.unit_price.toFixed(2)} each</p></div></div>
            <div className="quantity-control"><button type="button" aria-label={`Decrease quantity of ${item.product_name}`} disabled={busy || item.quantity <= 1} onClick={() => changeQuantity(item, item.quantity - 1)}>-</button><output aria-label="Quantity">{item.quantity}</output><button type="button" disabled={busy} aria-label={`Increase quantity of ${item.product_name}`} onClick={() => changeQuantity(item, item.quantity + 1)}>+</button></div>
            <strong className="cart-item-total">${item.total.toFixed(2)}</strong>
            <button className="remove-button" type="button" disabled={busy} aria-label={`Remove ${item.product_name}`} onClick={() => remove(item.id)}>Remove</button>
          </article>)}</div>
          <aside className="cart-summary"><p className="eyebrow">ORDER SUMMARY</p><div className="summary-row"><span>{cart.item_count} item(s)</span><span>${cart.subtotal.toFixed(2)}</span></div><div className="summary-row summary-total"><strong>Subtotal</strong><strong>${cart.subtotal.toFixed(2)}</strong></div><button className="button" type="button" disabled={busy} onClick={() => history.push("/checkout")}>Proceed to checkout</button><Link className="continue-link" to="/products">Continue shopping</Link></aside>
        </div>
      )}
    </section>
  );
}