/**
 * Toast notifications dispatched via custom events.
 *
 * Other modules (or inline templates) can fire:
 *   window.dispatchEvent(new CustomEvent("mph:toast", {
 *     detail: { kind: "error" | "info" | "success", message: "..." }
 *   }))
 *
 * Renders a minimal toast in a top-right region. Phase 2 will replace
 * this with the React notification system; the contract (the custom
 * event name and shape) stays stable.
 */

type ToastKind = "info" | "success" | "error" | "warning";

interface ToastDetail {
  kind: ToastKind;
  message: string;
  errorCode?: string;
}

const KIND_CLASS: Record<ToastKind, string> = {
  info: "mph-toast mph-toast-info",
  success: "mph-toast mph-toast-success",
  warning: "mph-toast mph-toast-warning",
  error: "mph-toast mph-toast-error",
};

function ensureRegion(): HTMLElement {
  let region = document.getElementById("mph-toast-region");
  if (!region) {
    region = document.createElement("div");
    region.id = "mph-toast-region";
    region.setAttribute("role", "status");
    region.setAttribute("aria-live", "polite");
    region.className = "mph-toast-region";
    document.body.appendChild(region);
  }
  return region;
}

function showToast(detail: ToastDetail): void {
  const region = ensureRegion();
  const toast = document.createElement("div");
  toast.className = KIND_CLASS[detail.kind] ?? KIND_CLASS.info;
  toast.textContent = detail.message;
  region.appendChild(toast);
  window.setTimeout(() => {
    toast.classList.add("mph-toast-leaving");
    window.setTimeout(() => toast.remove(), 250);
  }, 4500);
}

export function setupNotifications(): void {
  window.addEventListener("mph:toast", (evt) => {
    const detail = (evt as CustomEvent<ToastDetail>).detail;
    if (detail && detail.message) {
      showToast(detail);
    }
  });
}