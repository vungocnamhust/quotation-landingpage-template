"use client";

import { useId } from "react";
import { Calendar, X } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import type { DateInputProps } from "./types";
import { useDateInput } from "./useDateInput";

export function DateInput({
  mode = "iso",
  value,
  onChange,
  label,
  labelAction,
  placeholder,
  min,
  max,
  required = false,
  disabled = false,
  readOnly = false,
  size = "md",
  variant = "default",
  allowClear = true,
  error,
  helperText,
  className,
  inputClassName,
  "aria-label": ariaLabel,
  id: customId,
}: DateInputProps) {
  const generatedId = useId();
  const inputId = customId || generatedId;
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;

  const {
    inputRef,
    displayValue,
    hasValue,
    validationError,
    handleInputChange,
    handleClear,
    triggerPicker,
  } = useDateInput({
    value,
    mode,
    min,
    max,
    disabled,
    readOnly,
    onChange,
  });

  const activeError = error || validationError;

  // Size mapping
  const sizeClasses = {
    sm: "h-9",
    md: "min-h-11",
    lg: "min-h-12",
  }[size];

  const typographyClass = {
    sm: getTypographyClassName("bodySm"),
    md: getTypographyClassName("bodyMd"),
    lg: getTypographyClassName("bodyLg"),
  }[size];

  const iconSize = size === "sm" ? 14 : size === "lg" ? 18 : 16;

  return (
    <div
      className={cn(
        "flex flex-col gap-1.5",
        variant === "inline" ? "sm:flex-row sm:items-center sm:gap-3" : "",
        className
      )}
    >
      {/* Label & Optional Action */}
      {label ? (
        <div className="flex items-center justify-between gap-1.5">
          <label
            htmlFor={inputId}
            className={cn(
              getTypographyClassName("label"),
              "flex items-center text-[var(--color-muted)]",
              disabled ? "opacity-60" : ""
            )}
          >
            <span>{label}</span>
            {required ? (
              <span className="text-[var(--color-accent)] ml-0.5">*</span>
            ) : null}
          </label>

          {labelAction ? (
            <div className="flex items-center">{labelAction}</div>
          ) : null}
        </div>
      ) : null}

      {/* Input container */}
      <div
        className={cn(
          "relative flex items-center transition-all duration-200",
          sizeClasses,
          "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)]",
          "focus-within:border-[var(--color-accent)] focus-within:ring-2 focus-within:ring-[var(--color-accent-wash)]",
          disabled
            ? "cursor-not-allowed opacity-60 bg-[var(--color-surface-muted)]"
            : "",
          activeError ? "border-rose-500 ring-1 ring-rose-500/20" : ""
        )}
      >
        {/* Left Calendar Icon */}
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled || readOnly}
          onClick={triggerPicker}
          className="flex items-center pl-3 pr-1 text-[var(--color-muted)] transition-colors hover:text-[var(--color-on-surface)] disabled:cursor-not-allowed disabled:hover:text-[var(--color-muted)] cursor-pointer"
          aria-label={label ? `Open date picker for ${label}` : "Open date picker"}
        >
          <Calendar size={iconSize} aria-hidden="true" />
        </button>

        {/* Date / Text Input */}
        <input
          ref={inputRef}
          id={inputId}
          type={mode === "iso" ? "date" : "text"}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          value={displayValue}
          min={min || undefined}
          max={max || undefined}
          placeholder={placeholder}
          aria-label={ariaLabel || label || placeholder || "Date"}
          aria-invalid={Boolean(activeError)}
          aria-describedby={
            activeError ? errorId : helperText ? helperId : undefined
          }
          onChange={handleInputChange}
          className={cn(
            typographyClass,
            "w-full flex-1 bg-transparent text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none pl-1 pr-8",
            mode === "iso" ? "cursor-pointer" : "",
            inputClassName
          )}
        />

        {/* Right Action: Clear Button */}
        {allowClear && hasValue && !disabled && !readOnly ? (
          <div className="absolute right-2.5 flex items-center text-[var(--color-muted)]">
            <button
              type="button"
              onClick={handleClear}
              className="rounded-full p-1 hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
              aria-label={label ? `Clear ${label}` : "Clear date"}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        ) : null}
      </div>

      {/* Error Message */}
      {activeError ? (
        <p
          id={errorId}
          className={cn(
            getTypographyClassName("caption"),
            "text-rose-600 flex items-center gap-1"
          )}
          role="alert"
        >
          {activeError}
        </p>
      ) : helperText ? (
        <p
          id={helperId}
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]"
          )}
        >
          {helperText}
        </p>
      ) : null}
    </div>
  );
}
