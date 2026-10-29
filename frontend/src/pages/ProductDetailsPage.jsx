import React from "react";
import { Link, useParams } from "react-router-dom";
import { getProduct } from "../api/products";
import { useCart } from "../context/CartContext";
import { useLocation } from "../context/LocationContext";

export default function ProductDetailsPage() {
  const { id } = useParams();
  const { location } = useLocation();
  const { addItem } = useCart();
  const [product, setProduct] = React.useState(null);
  const [variantId, setVariantId] = React.useState(null);
  const [quantity, setQuantity] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [submitting, setSubmitting] = React.useState(false);
  const [message, setMessage] = React.useState("");
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let mounted = true;
    setLoading(true);
    getProduct(id, location ? { region_id: location.region.id, store_id: location.store.id } : {})
      .then((data) => {
        if (!mounted) return;
        setProduct(data);
        const defaultVariant = data.variants.find((variant) => variant.is_default);
        setVariantId(defaultVariant ? defaultVariant.id : null);
      })
      .catch((requestError) => { if (mounted) setError(requestError.message); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [id, location]);

  async function handleAddToCart() {
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      await addItem({
        product_id: product.id,
        variant_id: variantId,
        quantity,
        region_id: location ? location.region.id : undefined,
        store_id: location ? location.store.id : undefined,
        zip_code: location ? location.zip_code : undefined
      });
      setMessage("Product added to cart.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <section><h1>Loading product...</h1></section>;
  if (error && !product) return <section><p className="error-message">{error}</p></section>;
  if (!product) return null;

  const available = product.availability ? product.availability.available_quantity : null;
  return (
    <section className="product-detail">
      <Link className="back-link" to="/products">Back to products</Link>
      <div className="detail-layout">
        <div className="detail-image"><img src={product.image_url} alt={product.name} /></div>
        <div className="detail-copy">
          <p className="eyebrow">{product.brand.name}</p>
          <h1>{product.name}</h1>
          <p className="rating">{product.rating.toFixed(1)} / 5 ({product.review_count} reviews)</p>
          {product.price ? <p className="price detail-price">${product.price.current_price.toFixed(2)}{product.price.sale_price ? <del> ${product.price.price.toFixed(2)}</del> : null}</p> : <p className="muted">Choose a ZIP code to see regional pricing.</p>}
          <p>{product.short_description || product.description}</p>
          <p className="sku">SKU: {product.sku} {product.model_number ? ` | Model: ${product.model_number}` : ""}</p>
          {product.variants.length ? <fieldset className="variant-options"><legend>Options</legend>{product.variants.map((variant) => <label key={variant.id}><input type="radio" name="variant" checked={variantId === variant.id} onChange={() => setVariantId(variant.id)} /> {variant.name}</label>)}</fieldset> : null}
          <p className="availability">{product.availability ? product.availability.status : "Select a store for availability"}</p>
          <div className="quantity-control"><label htmlFor="quantity">Quantity</label><button type="button" onClick={() => setQuantity(Math.max(1, quantity - 1))}>-</button><output id="quantity">{quantity}</output><button type="button" disabled={available !== null && quantity >= available} onClick={() => setQuantity(quantity + 1)}>+</button></div>
          {error ? <p className="error-message">{error}</p> : null}
          {message ? <p className="success-message">{message} <Link to="/cart">View cart</Link></p> : null}
          <button className="button add-button" type="button" disabled={submitting || available === 0} onClick={handleAddToCart}>{submitting ? "Adding..." : available === 0 ? "Out of stock" : "Add to cart"}</button>
        </div>
      </div>
    </section>
  );
}