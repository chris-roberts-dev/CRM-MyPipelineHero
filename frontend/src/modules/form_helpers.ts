/**
 * Small form ergonomics shared across Phase 1 templates.
 *
 * Keep this thin. Anything more elaborate than enable/disable, focus
 * routing, or input masking belongs in HTMX server round-trips, not in
 * client-side JS state (per H.1.7 Alpine.js scope rules).
 */

/** Disable the submit button on `<form>` submit to prevent double-posts. */
export function disableSubmitOnSubmit(): void {
  document.body.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const submits = form.querySelectorAll<HTMLButtonElement | HTMLInputElement>(
      "button[type=submit], input[type=submit]",
    );
    submits.forEach((el) => {
      el.setAttribute("aria-busy", "true");
      el.setAttribute("disabled", "disabled");
    });
  });
}

/** Auto-focus the first `[autofocus]` element on first paint. */
export function autoFocusFirst(): void {
  const target = document.querySelector<HTMLElement>("[autofocus]");
  if (target && typeof target.focus === "function") {
    target.focus();
  }
}