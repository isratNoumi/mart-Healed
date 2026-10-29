import React from "react";
import { Link, useLocation as useRouterLocation, useParams } from "react-router-dom";
import { getBrands, getProducts } from "../api/products";
import ProductCard from "../components/products/ProductCard";
import { useLocation } from "../context/LocationContext";

export default function ProductListingPage() {
  const { search } = useRouterLocation();
  const { slug } = useParams();
  const { location } = useLocation();
  const [result, setResult] = React.useState({ items: [], total: 0 });
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [brands, setBrands] = React.useState([]);
  const [filters, setFilters] = React.useState({ brand: "", min_price: "", max_price: "", in_stock: false, sort: "relevance" });

  React.useEffect(() => {
    getBrands().then(setBrands).catch(() => setBrands([]));
  }, []);

  React.useEffect(() => {
    const searchParams = new URLSearchParams(search);
    const params = {
      category: slug,
      search: searchParams.get("search") || undefined,
      region_id: location ? location.region.id : undefined,
      store_id: location ? location.store.id : undefined,
      ...filters,
      limit: 24
    };
    let mounted = true;
    setLoading(true);
    setError("");
    getProducts(params)
      .then((data) => { if (mounted) setResult(data); })
      .catch((requestError) => { if (mounted) setError(requestError.message); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [search, slug, location, filters]);

  const title = slug ? slug.replaceAll("-", " ") : "Products";
  return (
    <section>
      <p className="eyebrow">CATALOG</p>
      <div className="section-heading"><div><h1 className="listing-title">{title}</h1><p className="muted">{result.total} products</p></div><Link to="/">Back home</Link></div>
      <form className="catalog-filters" onSubmit={(event) => event.preventDefault()}>
        <label>Brand<select value={filters.brand} onChange={(event) => setFilters({ ...filters, brand: event.target.value })}><option value="">All brands</option>{brands.map((brand) => <option value={brand.slug} key={brand.id}>{brand.name}</option>)}</select></label>
        <label>Min price<input type="number" min="0" value={filters.min_price} onChange={(event) => setFilters({ ...filters, min_price: event.target.value })} /></label>
        <label>Max price<input type="number" min="0" value={filters.max_price} onChange={(event) => setFilters({ ...filters, max_price: event.target.value })} /></label>
        <label className="checkbox-filter"><input type="checkbox" checked={filters.in_stock} onChange={(event) => setFilters({ ...filters, in_stock: event.target.checked })} /> In stock</label>
        <label>Sort<select value={filters.sort} onChange={(event) => setFilters({ ...filters, sort: event.target.value })}><option value="relevance">Relevance</option><option value="rating">Top rated</option><option value="price">Price</option></select></label>
      </form>
      {error ? <p className="error-message">{error}</p> : null}
      {loading ? <div className="product-grid">{[1, 2, 3, 4].map((item) => <div className="product-card skeleton-card" key={item} />)}</div> : (
        <div className="product-grid">{result.items.map((product) => <ProductCard product={product} key={product.id} />)}</div>
      )}
      {!loading && !result.items.length && !error ? <p className="empty-state">No products matched this selection.</p> : null}
    </section>
  );
}