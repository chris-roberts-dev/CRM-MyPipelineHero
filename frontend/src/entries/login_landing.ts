/**
 * Login + landing page entry (H.1.2).
 *
 * The public landing page and the login page share this bundle because
 * they share the same body class posture (`mph-public-body`), share the
 * same visual baseline, and have nearly identical client-side needs
 * (focus management, CSRF for the login POST, no HTMX-heavy flows).
 */

import { setupCsrf } from "../modules/csrf";
import { autoFocusFirst, disableSubmitOnSubmit } from "../modules/form_helpers";
import { setupNotifications } from "../modules/notifications";
import "../styles/login_landing.css";

function boot(): void {
  setupCsrf();
  setupNotifications();
  autoFocusFirst();
  disableSubmitOnSubmit();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}