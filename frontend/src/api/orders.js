import { apiRequest } from "./client";

export function getOrders(page = 1, limit = 10) {
  return apiRequest(`/orders?page=${page}&limit=${limit}`);
}

export function getOrder(orderId) {
  return apiRequest(`/orders/${encodeURIComponent(orderId)}`);
}
