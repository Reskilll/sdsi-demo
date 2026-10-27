import { reactive, readonly } from 'vue';
import type { ToastKind, ToastMessage } from '../types/ui';

const toasts = reactive<ToastMessage[]>([]);
const timers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 1;

function dismiss(id: number): void {
  const index = toasts.findIndex((toast) => toast.id === id);
  if (index >= 0) toasts.splice(index, 1);
  const timer = timers.get(id);
  if (timer !== undefined) {
    clearTimeout(timer);
    timers.delete(id);
  }
}

function notify(message: string, kind: ToastKind = 'info', durationMs = 5000): number {
  const id = nextId++;
  toasts.push({ id, kind, message });
  while (toasts.length > 4) {
    const oldest = toasts[0];
    if (!oldest) break;
    dismiss(oldest.id);
  }
  if (durationMs > 0) {
    timers.set(
      id,
      setTimeout(() => dismiss(id), durationMs),
    );
  }
  return id;
}

export function useToasts() {
  return {
    toasts: readonly(toasts),
    notify,
    dismiss,
  };
}
