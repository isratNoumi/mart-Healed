import React from "react";
import { getCart, addCartItem, updateCartItem, removeCartItem } from "../api/cart";
import { useAuth } from "./AuthContext";
import { useLocation } from "./LocationContext";

export const CartContext = React.createContext(null);

export function CartProvider({ children }) {
  const [cart, setCart] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const { location } = useLocation();
  const { user, loading: authLoading } = useAuth();
  const userId = user ? user.id : null;

  // userId is a dependency so the cart reloads (and merges the guest cart) on sign-in and sign-out.
  const refreshCart = React.useCallback(async () => {
    setLoading(true);
    try {
      setCart(await getCart(location));
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [location, userId]);

  React.useEffect(() => {
    if (!authLoading) refreshCart();
  }, [authLoading, refreshCart]);

  const addItem = async (item) => setCart(await addCartItem(item));
  const updateItem = async (id, item) => setCart(await updateCartItem(id, item));
  const removeItem = async (id) => setCart(await removeCartItem(id));

  return (
    <CartContext.Provider value={{ cart, loading, error, refreshCart, addItem, updateItem, removeItem }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return React.useContext(CartContext);
}