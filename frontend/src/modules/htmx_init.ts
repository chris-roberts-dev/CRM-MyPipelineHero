/**
 * HTMX initialization (H.1.5).
 *
 * Imported by every entry that uses HTMX (tenant_portal, platform_console,
 * login_landing). Each entry calls `initHtmx()` at module top-level.
 */

import "htmx.org";
import { setupCsrf } from "./csrf";
import { setupNotifications } from "./notifications";

export function initHtmx(): void {
  setupCsrf();
  setupNotifications();

  window.htmx.config.defaultSwapStyle = "innerHTML";
  window.htmx.config.includeIndicatorStyles = false;
  window.htmx.config.scrollIntoViewOnBoost = false;
  // Tenant data must never persist in browser history-state (H.1.9).
  window.htmx.config.historyCacheSize = 0;
  window.htmx.config.allowEval = false;
  window.htmx.config.allowScriptTags = false;

  // 401 from a tenant subdomain → bounce to root-domain login.
  document.body.addEventListener("htmx:responseError", (rawEvent: Event) => {
    const evt = rawEvent as HtmxResponseErrorEvent;
    if (evt.detail.xhr.status === 401) {
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `/login/?next=${next}`;
    }
  });

  // Surface server-set X-Error-Code headers as user-visible toasts.
  document.body.addEventListener("htmx:responseError", (rawEvent: Event) => {
    const evt = rawEvent as HtmxResponseErrorEvent;
    const errorCode = evt.detail.xhr.getResponseHeader("X-Error-Code");
    if (errorCode) {
      const message =
        evt.detail.xhr.responseText || "Something went wrong.";
      window.dispatchEvent(
        new CustomEvent("mph:toast", {
          detail: { kind: "error", message, errorCode },
        }),
      );
    }
  });
}