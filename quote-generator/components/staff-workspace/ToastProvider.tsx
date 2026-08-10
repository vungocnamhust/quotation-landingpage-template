"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

export type ToastType = "success" | "error" | "info";
export type NotificationAction = { label: string; onClick: () => void };

export type ToastItem = {
  id: string;
  message: string;
  type: ToastType;
  persistent?: boolean;
  action?: NotificationAction;
  scope?: string;
};

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
  notify: (input: Omit<ToastItem, "id">) => void;
  dismiss: (id: string) => void;
  clearScope: (scope: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const emptySubscribe = () => () => {};

function useIsMounted() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const mounted = useIsMounted();

  useEffect(() => {
    if (!toasts.length) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setToasts([]);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [toasts.length]);

  const notify = useCallback((input: Omit<ToastItem, "id">) => {
    const id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).substring(2, 9);

    setToasts((prev) => {
      const retained = input.scope ? prev.filter((item) => item.scope !== input.scope) : prev;
      return [...retained, { ...input, id }];
    });

    if (!input.persistent) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4000);
    }
  }, []);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    notify({ message, type });
  }, [notify]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearScope = useCallback((scope: string) => {
    setToasts((prev) => prev.filter((item) => item.scope !== scope));
  }, []);

  const icons: Record<ToastType, ReactNode> = {
    success: <CheckCircle2 size={16} aria-hidden="true" />,
    error: <XCircle size={16} aria-hidden="true" />,
    info: <Info size={16} aria-hidden="true" />,
  };

  return (
    <ToastContext.Provider value={{ toast, notify, dismiss, clearScope }}>
      {children}
      {mounted
        ? createPortal(
            <div
              role="region"
              aria-label="Notifications"
              aria-live="polite"
              className="toast-region"
            >
              {toasts.map((t) => (
                <div
                  key={t.id}
                  role="alert"
                  className={cn("toast-item", `toast-item--${t.type}`)}
                >
                  <span
                    className={cn(
                      "toast-item__icon",
                      `toast-item__icon--${t.type}`
                    )}
                  >
                    {icons[t.type]}
                  </span>
                  <p
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "toast-item__message"
                    )}
                  >
                    {t.message}
                  </p>
                  {t.action ? (
                    <button
                      type="button"
                      onClick={t.action.onClick}
                      className={cn(getTypographyClassName("buttonSecondary"), "toast-item__action")}
                    >
                      {t.action.label}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => dismiss(t.id)}
                    aria-label="Dismiss notification"
                    className="toast-item__close"
                  >
                    <X size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>,
            document.body
          )
        : null}
    </ToastContext.Provider>
  );
}
