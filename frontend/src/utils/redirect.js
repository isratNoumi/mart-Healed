export function safeNextPath(search) {
  const next = new URLSearchParams(search).get("next");
  // Only same-site paths: "//host" or "/\host" would send the user to another site.
  return next && /^\/(?![/\\])/.test(next) ? next : "/";
}
