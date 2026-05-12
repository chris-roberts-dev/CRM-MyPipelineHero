/**
 * Tenant portal entry (H.1.2).
 *
 * HTMX is the global interactivity default (H.1.4). Alpine.js is
 * available for narrow UI state (H.1.7) but is loaded lazily so the
 * initial payload stays small.
 */

import {
    autoFocusFirst,
    disableSubmitOnSubmit,
} from "../modules/form_helpers";
import { initHtmx } from "../modules/htmx_init";
import "../styles/tenant_portal.css";

async function maybeLoadAlpine(): Promise<void> {
  // Only load Alpine if the page uses x-data / x-init.
  const hasAlpine = document.querySelector<HTMLElement>(
    "[x-data], [x-init]",
  );
  if (!hasAlpine) return;
  const Alpine = (await import("alpinejs")).default;
  (window as unknown as { Alpine: typeof Alpine }).Alpine = Alpine;
  Alpine.start();
}

function boot(): void {
  initHtmx();
  disableSubmitOnSubmit();
  autoFocusFirst();
  void maybeLoadAlpine();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}