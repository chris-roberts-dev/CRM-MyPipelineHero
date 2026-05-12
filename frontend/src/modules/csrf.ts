/**
 * CSRF integration for HTMX (H.1.6).
 *
 * Django sets the CSRF cookie (`mph_csrftoken`); HTMX reads it and adds
 * the `X-CSRFToken` header on mutating requests.
 *
 * The cookie is HttpOnly=false (see config/settings/base.py) precisely
 * so this JS module can read it. The token itself is not a credential —
 * it's a per-session anti-forgery value. Treat it as non-sensitive.
 */

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const parts = document.cookie.split(";");
  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.substring(prefix.length));
    }
  }
  return null;
}

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function setupCsrf(): void {
  const cookieName =
    (document.documentElement.dataset.csrfCookie as string | undefined) ??
    "mph_csrftoken";
  const token = readCookie(cookieName);
  if (!token) {
    return;
  }
  document.body.addEventListener("htmx:configRequest", (rawEvent: Event) => {
    const evt = rawEvent as HtmxConfigRequestEvent;
    if (MUTATING_METHODS.has(evt.detail.verb.toUpperCase())) {
      evt.detail.headers["X-CSRFToken"] = token;
    }
  });
}