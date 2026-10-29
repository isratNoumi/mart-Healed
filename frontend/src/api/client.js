const API_ROOT = "/api";
const DEFAULT_MESSAGE = "Something went wrong. Please try again.";
export const UNAUTHORIZED_EVENT = "buildmart:unauthorized";

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body || {};
    this.code = this.body.code || null;
  }
}

function cleanMessage(message) {
  return message.replace(/^Value error, /, "");
}

function messageFrom(body) {
  if (body && typeof body.detail === "string") return body.detail;
  if (body && Array.isArray(body.detail) && body.detail.length) return cleanMessage(body.detail[0].msg);
  return DEFAULT_MESSAGE;
}

export function fieldErrors(error) {
  const body = error && error.body;
  if (!body) return {};
  if (body.errors) return body.errors;
  if (!Array.isArray(body.detail)) return {};
  return body.detail.reduce((errors, item) => {
    const field = item.loc[item.loc.length - 1];
    if (!errors[field]) errors[field] = cleanMessage(item.msg);
    return errors;
  }, {});
}

export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      credentials: "same-origin",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });
  } catch {
    throw new ApiError("We couldn't reach BuildMart. Check your connection and try again.", 0, { code: "NETWORK_ERROR" });
  }

  if (response.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (response.status === 204) return null;

  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(messageFrom(body), response.status, body);
  return body;
}