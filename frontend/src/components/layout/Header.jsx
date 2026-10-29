import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useCart } from "../../context/CartContext";
import LocationSelector from "../location/LocationSelector";

export default function Header() {
  const { cart } = useCart();
  const { user } = useAuth();
  const itemCount = cart ? cart.item_count : 0;

  return (
    <>
      <header className="site-header">
        <Link className="brand" to="/">BUILD MART</Link>
        <form className="search-form" action="/products">
          <input name="search" placeholder="What can we help you find?" />
          <button type="submit" aria-label="Search">Search</button>
        </form>
        <div className="header-actions">
          <LocationSelector />
          {user ? <Link to="/account">Hi, {user.first_name}</Link> : <Link to="/login">Sign in</Link>}
          <Link to="/cart">Cart ({itemCount})</Link>
        </div>
      </header>
      <nav className="category-nav"><Link to="/products">Shop All</Link><Link to="/category/power-tools">Power Tools</Link><Link to="/category/hand-tools">Hand Tools</Link><Link to="/category/hardware">Hardware</Link><Link to="/category/paint">Paint</Link><Link to="/category/lawn-garden">Lawn &amp; Garden</Link></nav>
    </>
  );
}