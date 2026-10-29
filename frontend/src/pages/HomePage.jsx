import React from "react";
import { Link } from "react-router-dom";
import { getCategories, getProducts } from "../api/products";
import ProductCard from "../components/products/ProductCard";
import { useLocation } from "../context/LocationContext";

export default function HomePage() {
  const [categories, setCategories] = React.useState([]);
  const [products, setProducts] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const { location } = useLocation();

  React.useEffect(() => {
    let mounted = true;
    const catalogLocation = location ? {
      region_id: location.region.id,
      store_id: location.store.id
    } : {};
    setLoading(true);
    Promise.all([getCategories(), getProducts({ limit: 8, ...catalogLocation })])
      .then(([categoryData, productData]) => {
        if (!mounted) return;
        setCategories(categoryData);
        setProducts(productData.items);
      })
      .catch((requestError) => {
        if (mounted) setError(requestError.message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => { mounted = false; };
  }, [location]);

  return (
    <section className="home-page">
      <div className="hero">
        <p className="eyebrow">BUILD MART PROJECT CENTER</p>
        <h1>Power up your next project.</h1>
        <p>Professional tools and practical supplies for work worth doing.</p>
        <Link className="button" to="/products">Shop products</Link>
      </div>

      <section className="home-section">
        <p className="eyebrow">START HERE</p>
        <h2>Shop by category</h2>
        {loading ? <p className="muted">Loading categories...</p> : (
          <div className="category-grid">
            {categories.map((category) => <Link key={category.id} to={`/category/${category.slug}`}>{category.name}</Link>)}
          </div>
        )}
      </section>

      <section className="home-section">
        <div className="section-heading"><div><p className="eyebrow">PROJECT PICKS</p><h2>Featured products</h2></div><Link to="/products">View all</Link></div>
        {error ? <p className="error-message">{error}</p> : null}
        {loading ? <div className="product-grid">{[1, 2, 3, 4].map((item) => <div className="product-card skeleton-card" key={item} />)}</div> : (
          <div className="product-grid">{products.map((product) => <ProductCard product={product} key={product.id} />)}</div>
        )}
      </section>
    </section>
  );
}