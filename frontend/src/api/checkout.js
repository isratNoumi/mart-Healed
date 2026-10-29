import { apiRequest } from "./client";

function toQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  return query.toString();
}

export function getCheckout(storeId) {
  return apiRequest(`/checkout?${toQuery({ store_id: storeId })}`);
}

export function validateCheckout(selection) {
  return apiRequest("/checkout/validate", { method: "POST", body: JSON.stringify(selection) });
}

export function getFulfillmentOptions(storeId, shippingAddressId) {
  return apiRequest(`/fulfillment/options?${toQuery({ store_id: storeId, shipping_address_id: shippingAddressId })}`);
}

export function getAddresses() {
  return apiRequest("/addresses");
}

export function createAddress(address) {
  return apiRequest("/addresses", { method: "POST", body: JSON.stringify(address) });
}

export function updateAddress(id, address) {
  return apiRequest(`/addresses/${id}`, { method: "PUT", body: JSON.stringify(address) });
}

export function placeOrder(order) {
  return apiRequest("/orders", { method: "POST", body: JSON.stringify(order) });
}

export function processPayment(payment) {
  return apiRequest("/payments/process", { method: "POST", body: JSON.stringify(payment) });
}
