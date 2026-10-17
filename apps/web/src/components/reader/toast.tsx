"use client";

import { useEffect } from "react";

import type { Toast } from "./use-item-actions";

const TOAST_MS = 6000;

/** A small status message at the bottom of the screen, with Undo when there is something to undo. */
export function UndoToast({ toast, onDismiss }: { toast: Toast | null; onDismiss: () => void }) {
  const id = toast?.id;
  useEffect(() => {
    if (id === undefined) return;
    const timer = setTimeout(onDismiss, TOAST_MS);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  if (!toast) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 bottom-6 z-50 flex justify-center px-4"
    >
      <div className="flex items-center gap-3 rounded-md bg-ink px-4 py-2 font-sans text-sm text-paper shadow-lg">
        <span>{toast.message}</span>
        {toast.undo ? (
          <button
            type="button"
            onClick={() => {
              toast.undo?.();
              onDismiss();
            }}
            className="font-semibold underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-paper"
          >
            Undo
          </button>
        ) : null}
      </div>
    </div>
  );
}
