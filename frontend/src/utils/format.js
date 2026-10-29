const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export const FULFILLMENT_LABELS = {
  SHIP_TO_HOME: "Ship to Home",
  STORE_PICKUP: "Store Pickup",
  DELIVERY: "Local Delivery"
};

export function formatMoney(value) {
  return currency.format(Number(value) || 0);
}

export function parseDate(value) {
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }
  // Backend timestamps are UTC but sent without a zone suffix.
  return new Date(/([zZ]|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`);
}

export function formatDate(value) {
  const date = parseDate(value);
  return date ? date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "";
}

export function formatDateTime(value) {
  const date = parseDate(value);
  return date ? date.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }) : "";
}

export function formatStatus(status) {
  if (!status) return "";
  const text = status.toLowerCase().replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
