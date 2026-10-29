import { apiRequest } from "./client";

export function resolveZip(zipCode) {
  return apiRequest(`/regions/zip/${encodeURIComponent(zipCode)}`);
}

export function getStores(regionId) {
  const query = regionId ? `?region_id=${regionId}` : "";
  return apiRequest(`/stores${query}`);
}