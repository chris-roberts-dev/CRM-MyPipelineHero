/**
 * Platform console entry (H.1.2).
 *
 * The platform console is server-rendered and HTMX-driven. Tenant-side
 * Alpine integrations are intentionally not loaded here.
 */

import {
    autoFocusFirst,
    disableSubmitOnSubmit,
} from "../modules/form_helpers";
import { initHtmx } from "../modules/htmx_init";
import "../styles/platform_console.css";

function boot(): void {
  initHtmx();
  disableSubmitOnSubmit();
  autoFocusFirst();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}