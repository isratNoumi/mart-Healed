import { apiRequest } from "./client";

// The guest cart is identified by an HttpOnly cookie issued by the server, so the
// client never generates or sends a cart/session identifier itself.
try {
  localStorage.removeItem("build-mart-session");
} catch {
  // localStorage may be unavailable; nothing to clean up.
}

export function getCart(location) {
  const query = new URLSearchParams();
  if (location) {
    query.set("region_id", location.region.id);
    query.set("store_id", location.store.id);
    query.set("zip_code", location.zip_code);
  }
  const suffix = query.toString();
  return apiRequest(suffix ? `/cart?${suffix}` : "/cart");
}

export function addCartItem(item) {
  return apiRequest("/cart/items", {
    method: "POST",
    body: JSON.stringify(item)
  });
}

export function updateCartItem(id, item) {
  return apiRequest(`/cart/items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(item)
  });
}

export function removeCartItem(id) {
  return apiRequest(`/cart/items/${id}`, {
    method: "DELETE"
  });
}
