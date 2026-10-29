import { apiRequest } from "./client";

export function getCurrentUser() {
  return apiRequest("/auth/me");
}

export function login(credentials) {
  return apiRequest("/auth/login", { method: "POST", body: JSON.stringify(credentials) });
}

export function register(details) {
  return apiRequest("/auth/register", { method: "POST", body: JSON.stringify(details) });
}

export function logout() {
  return apiRequest("/auth/logout", { method: "POST" });
}
