/**
 * Helpers for keeping auth tokens out of the visible URL.
 *
 * Magic-link and invite emails carry the JWT as a `?token=` query param.
 * Once the session cookie is established we strip that param from the URL
 * (via history replacement) so the credential isn't left in the address
 * bar or browser history.
 */

const TOKEN_PARAM = "token";

/**
 * Return a copy of `url` with the auth `token` query param removed. Other
 * params and the path are preserved. Returns the same logical URL when no
 * token is present.
 */
export function urlWithoutToken(url: URL): URL {
  const next = new URL(url);
  next.searchParams.delete(TOKEN_PARAM);
  return next;
}

/** True when `url` carries an auth `token` query param worth scrubbing. */
export function hasToken(url: URL): boolean {
  return url.searchParams.has(TOKEN_PARAM);
}
