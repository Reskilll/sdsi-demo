/**
 * Renders active toast notifications with Lucide icons and animation.
 */

'use client';

import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToast } from './toast-provider';

const ICONS = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const COLORS = {
  success: {
    bg: 'bg-emerald-900/80',
    border: 'border-emerald-600/50',
    icon: 'text-emerald-400',
    text: 'text-emerald-100',
  },
  error: {
    bg: 'bg-red-900/80',
    border: 'border-red-600/50',
    icon: 'text-red-400',
    text: 'text-red-100',
  },
  warning: {
    bg: 'bg-amber-900/80',
    border: 'border-amber-600/50',
    icon: 'text-amber-400',
    text: 'text-amber-100',
  },
  info: {
    bg: 'bg-blue-900/80',
    border: 'border-blue-600/50',
    icon: 'text-blue-400',
    text: 'text-blue-100',
  },
};

export default function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type];
        const color = COLORS[toast.type];

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto ${color.bg} ${color.border} border backdrop-blur-md rounded-xl px-4 py-3 shadow-lg shadow-black/30 animate-slide-in`}
          >
            <div className="flex items-start gap-3">
              <Icon className={`w-5 h-5 ${color.icon} shrink-0 mt-0.5`} />
              <div className={`flex-1 min-w-0 ${color.text}`}>
                <p className="text-sm font-semibold">{toast.title}</p>
                {toast.message ? (
                  <p className="text-xs opacity-80 mt-0.5">{toast.message}</p>
                ) : null}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className={`shrink-0 opacity-60 hover:opacity-100 transition-opacity ${color.text}`}
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}