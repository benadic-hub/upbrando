import { useEffect } from "react";
import { useUiStore } from "@/store/ui.store";

function toneClass(type: "success" | "error" | "info") {
  if (type === "success") {
    return "border-emerald-300 bg-emerald-50 text-emerald-800";
  }
  if (type === "error") {
    return "border-red-300 bg-red-50 text-red-800";
  }
  return "border-border bg-surface text-text";
}

export function ToastViewport() {
  const toasts = useUiStore((state) => state.toasts);
  const removeToast = useUiStore((state) => state.removeToast);

  useEffect(() => {
    const timers = toasts.map((toast) =>
      window.setTimeout(() => {
        removeToast(toast.id);
      }, 3500)
    );
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [toasts, removeToast]);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-sm flex-col gap-2">
      {toasts.map((toast) => (
        <div key={toast.id} className={`pointer-events-auto rounded-md border px-3 py-2 text-sm shadow-sm ${toneClass(toast.type)}`}>
          {toast.message}
        </div>
      ))}
    </div>
  );
}
