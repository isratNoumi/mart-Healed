import React from "react";
import { Link } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { useLocation } from "../../context/LocationContext";

export default function ProductCard({ product }) {
  const price = product.price;
  const { addItem } = useCart();
  const { location } = useLocation();
  const [adding, setAdding] = React.useState(false);
  const [added, setAdded] = React.useState(false);

  async function handleAdd() {
    setAdding(true);
    setAdded(false);
    try {
      const defaultVariant = product.variants.find((variant) => variant.is_default);
      await addItem({
        product_id: product.id,
        variant_id: defaultVariant ? defaultVariant.id : undefined,
        quantity: 1,
        region_id: location ? location.region.id : undefined,
        store_id: location ? location.store.id : undefined,
        zip_code: location ? location.zip_code : undefined
      });
      setAdded(true);
    } finally {
      setAdding(false);
    }
  }

  return (
    <article className="product-card">
      <div className="product-image"><img src={product.image_url} alt={product.name} /></div>
      <p className="eyebrow">{product.brand.name}</p>
      <Link className="product-name" to={`/products/${product.id}`}>{product.name}</Link>
      <p className="rating">{product.rating.toFixed(1)} / 5 ({product.review_count})</p>
      {price ? <p className="price">${price.current_price.toFixed(2)}{price.sale_price ? <del> ${price.price.toFixed(2)}</del> : null}</p> : <p className="muted">Choose a location for pricing</p>}
      <p className="availability">{product.availability ? product.availability.status : "Select a store for availability"}</p>
      <button className="card-action" type="button" disabled={adding || !price || product.availability && !product.availability.in_stock} onClick={handleAdd}>{adding ? "Adding..." : added ? "Added to cart" : "Add to cart"}</button>
    </article>
  );
}