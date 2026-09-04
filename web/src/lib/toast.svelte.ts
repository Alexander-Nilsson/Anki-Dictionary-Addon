/**
 * Lightweight toast notifications for the dictionary shell.
 *
 * Fired from the compat layer (copy / send-to-field / export) so quick
 * actions get a subtle confirmation. The store is shared module state — the
 * <Toaster /> component renders it reactively.
 */

export interface Toast {
  id: number;
  message: string;
}

const toasts = $state<Toast[]>([]);

let nextToastId = 1;

/** Show a toast; it auto-dismisses after a short delay. */
export function showToast(message: string): void {
  const id = nextToastId++;
  toasts.push({ id, message });
  window.setTimeout(() => {
    const index = toasts.findIndex((toast) => toast.id === id);
    if (index !== -1) toasts.splice(index, 1);
  }, 1800);
}

export { toasts };