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
import { CheckCircle2, XCircle, AlertTriangle, Info, Loader2, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

export type ToastType = "success" | "error" | "info" | "warning" | "loading";
export type NotificationAction = { label: string; onClick: () => void };

export type ToastItem = {
  id: string;
  message: string;
  type: ToastType;
  persistent?: boolean;
  action?: NotificationAction;
  scope?: string;
};

export type ToastOptions = {
  persistent?: boolean;
  action?: NotificationAction;
  scope?: string;
};

export type PromiseToastMessages<T> = {
  loading: string;
  success: string | ((data: T) => string);
  error: string | ((error: unknown) => string);
};

interface ToastContextValue {
  toast: (message: string, type?: ToastType, options?: ToastOptions) => string;
  notify: (input: Omit<ToastItem, "id">) => string;
  dismiss: (id: string) => void;
  clearScope: (scope: string) => void;
  promise: <T>(
    promiseFn: Promise<T> | (() => Promise<T>),
    messages: PromiseToastMessages<T>,
    options?: { scope?: string }
  ) => Promise<T>;
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

  const notify = useCallback((input: Omit<ToastItem, "id">): string => {
    const id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).substring(2, 9);

    setToasts((prev) => {
      const retained = input.scope ? prev.filter((item) => item.scope !== input.scope) : prev;
      return [...retained, { ...input, id }];
    });

    if (!input.persistent && input.type !== "loading") {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, input.type === "error" || input.type === "warning" ? 6000 : 4000);
    }

    return id;
  }, []);

  const toast = useCallback(
    (message: string, type: ToastType = "info", options?: ToastOptions): string => {
      return notify({
        message,
        type,
        persistent: options?.persistent,
        action: options?.action,
        scope: options?.scope,
      });
    },
    [notify]
  );

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearScope = useCallback((scope: string) => {
    setToasts((prev) => prev.filter((item) => item.scope !== scope));
  }, []);

  const promise = useCallback(
    async <T,>(
      promiseOrFn: Promise<T> | (() => Promise<T>),
      messages: PromiseToastMessages<T>,
      options?: { scope?: string }
    ): Promise<T> => {
      const toastScope = options?.scope ?? `promise-${Math.random().toString(36).slice(2, 8)}`;
      notify({
        message: messages.loading,
        type: "loading",
        persistent: true,
        scope: toastScope,
      });

      try {
        const promiseInstance = typeof promiseOrFn === "function" ? promiseOrFn() : promiseOrFn;
        const result = await promiseInstance;
        const successMsg =
          typeof messages.success === "function" ? messages.success(result) : messages.success;
        notify({
          message: successMsg,
          type: "success",
          scope: toastScope,
        });
        return result;
      } catch (err: unknown) {
        const errorMsg =
          typeof messages.error === "function" ? messages.error(err) : messages.error;
        notify({
          message: errorMsg,
          type: "error",
          persistent: true,
          scope: toastScope,
        });
        throw err;
      }
    },
    [notify]
  );

  const icons: Record<ToastType, ReactNode> = {
    success: <CheckCircle2 size={16} aria-hidden="true" />,
    error: <XCircle size={16} aria-hidden="true" />,
    warning: <AlertTriangle size={16} aria-hidden="true" />,
    info: <Info size={16} aria-hidden="true" />,
    loading: <Loader2 size={16} className="animate-spin" aria-hidden="true" />,
  };

  return (
    <ToastContext.Provider value={{ toast, notify, dismiss, clearScope, promise }}>
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
                  role={t.type === "error" || t.type === "warning" ? "alert" : "status"}
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
                      onClick={() => {
                        t.action?.onClick();
                        dismiss(t.id);
                      }}
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
