"use client";

import { useCallback, useMemo, useRef, type ChangeEvent } from "react";
import { isValidIsoDate } from "../../lib/rules/datesRules";

export interface UseDateInputOptions {
  value?: string | null;
  mode?: "iso" | "text";
  min?: string | null;
  max?: string | null;
  disabled?: boolean;
  readOnly?: boolean;
  onChange?: (value: string | null) => void;
}

export function useDateInput({
  value,
  mode = "iso",
  min,
  max,
  disabled = false,
  readOnly = false,
  onChange,
}: UseDateInputOptions) {
  const inputRef = useRef<HTMLInputElement>(null);

  const displayValue = value ?? "";
  const hasValue = Boolean(value && value.trim().length > 0);

  // Validation against min and max in ISO mode
  const validationError = useMemo(() => {
    if (mode !== "iso" || !value || !isValidIsoDate(value)) {
      return null;
    }
    if (min && isValidIsoDate(min) && value < min) {
      return `Date cannot be earlier than ${min}`;
    }
    if (max && isValidIsoDate(max) && value > max) {
      return `Date cannot be later than ${max}`;
    }
    return null;
  }, [mode, value, min, max]);

  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      if (disabled || readOnly) return;
      const nextVal = e.target.value;
      onChange?.(nextVal.trim() ? nextVal : null);
    },
    [disabled, readOnly, onChange]
  );

  const handleClear = useCallback(() => {
    if (disabled || readOnly) return;
    onChange?.(null);
    inputRef.current?.focus();
  }, [disabled, readOnly, onChange]);

  const triggerPicker = useCallback(() => {
    if (disabled || readOnly) return;
    if (inputRef.current) {
      try {
        if (typeof inputRef.current.showPicker === "function") {
          inputRef.current.showPicker();
        } else {
          inputRef.current.focus();
        }
      } catch {
        inputRef.current.focus();
      }
    }
  }, [disabled, readOnly]);

  return {
    inputRef,
    displayValue,
    hasValue,
    validationError,
    handleInputChange,
    handleClear,
    triggerPicker,
  };
}
