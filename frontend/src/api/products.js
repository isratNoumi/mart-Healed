import { apiRequest } from "./client";

export function getProducts(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  return apiRequest(`/products?${query.toString()}`);
}

export function getProduct(id, location = {}) {
  const query = new URLSearchParams(location);
  return apiRequest(`/products/${id}?${query.toString()}`);
}

export function getCategories() {
  return apiRequest("/categories");
}

export function getBrands() {
  return apiRequest("/brands");
}