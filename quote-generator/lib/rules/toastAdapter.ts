/**
 * Layer 2: Canonical Adapter for Toast and Screen Notification Signals.
 * Bridges Backend DTO errors, Validation Gate results, and Domain signals into unified Toast items.
 */

import type { ToastType } from "../../components/staff-workspace/ToastProvider.tsx";
import type { ClientGateResult } from "./validationGates.ts";
import { apiErrorMessage } from "../apiError.ts";

export type ToastPayload = {
  message: string;
  type: ToastType;
  scope?: string;
  field?: string;
};

export const toastAdapter = {
  /**
   * Adapts any API or network error into a friendly toast notification.
   */
  fromApiError(error: unknown, fallback: string = "An unexpected error occurred."): ToastPayload {
    const message = apiErrorMessage(error) || fallback;
    return {
      message,
      type: "error",
    };
  },

  /**
   * Adapts a client-side gate validation result into a toast notification.
   * Returns null if all gates passed.
   */
  fromGateResult(gateResult: ClientGateResult): ToastPayload | null {
    if (gateResult.passed && gateResult.warnings.length === 0) {
      return null;
    }

    if (gateResult.errors.length > 0) {
      const firstError = gateResult.errors[0];
      const count = gateResult.errors.length;
      const extra = count > 1 ? ` (+${count - 1} other issue${count > 2 ? "s" : ""})` : "";
      return {
        message: `${firstError.message}${extra}`,
        type: "error",
        field: firstError.field,
      };
    }

    if (gateResult.warnings.length > 0) {
      const firstWarning = gateResult.warnings[0];
      return {
        message: firstWarning.message,
        type: "warning",
        field: firstWarning.field,
      };
    }

    return null;
  },

  /**
   * Creates a standard success toast payload.
   */
  fromSuccess(message: string, scope?: string): ToastPayload {
    return {
      message,
      type: "success",
      scope,
    };
  },

  /**
   * Creates a standard info toast payload.
   */
  fromInfo(message: string, scope?: string): ToastPayload {
    return {
      message,
      type: "info",
      scope,
    };
  },

  /**
   * Creates a standard warning toast payload.
   */
  fromWarning(message: string, scope?: string, field?: string): ToastPayload {
    return {
      message,
      type: "warning",
      scope,
      field,
    };
  },
};
