"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { MapPin, Search, X, Check, Loader2, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { DestinationRef, DestinationSelectProps } from "./types.ts";
import { useDestinationSearch } from "./useDestinationSearch.ts";

export function DestinationSelect({
  mode = "single",
  value,
  values = [],
  onChange,
  onSelect,
  label,
  placeholder = "Search destination…",
  disabled = false,
  readOnly = false,
  required = false,
  size = "md",
  variant = "default",
  allowCustom = true,
  className,
  inputClassName,
  menuClassName,
  error,
  helperText,
  "aria-label": ariaLabel,
  id: customId,
}: DestinationSelectProps) {
  const generatedId = useId();
  const inputId = customId || generatedId;
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Extract single mode initial string value
  const singleValueName =
    typeof value === "string" ? value : value?.name ?? "";

  const [query, setQuery] = useState(() => (mode === "single" ? singleValueName : ""));
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const { results, isLoading, error: searchError, hasQuery } =
    useDestinationSearch(query);

  const [prevSingleValue, setPrevSingleValue] = useState(singleValueName);
  if (singleValueName !== prevSingleValue) {
    setPrevSingleValue(singleValueName);
    if (!isOpen && mode === "single") {
      setQuery(singleValueName);
    }
  }

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        if (mode === "single") {
          // If custom input allowed and query changed, update or reset
          if (allowCustom && query.trim() && query !== singleValueName) {
            onChange?.(query.trim(), null);
            onSelect?.(null);
          } else {
            setQuery(singleValueName);
          }
        } else {
          setQuery("");
        }
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, mode, allowCustom, query, singleValueName, onChange, onSelect]);

  const handleSelect = useCallback(
    (item: DestinationRef) => {
      if (mode === "single") {
        setQuery(item.name);
        setIsOpen(false);
        onChange?.(item.name, item);
        onSelect?.(item);
      } else {
        const exists = values.some(
          (v) =>
            v.id === item.id ||
            v.name.toLowerCase() === item.name.toLowerCase()
        );
        if (!exists) {
          const next = [...values, item];
          onChange?.(next);
        }
        setQuery("");
        inputRef.current?.focus();
      }
    },
    [mode, values, onChange, onSelect]
  );

  const handleRemoveChip = useCallback(
    (refToRemove: DestinationRef) => {
      if (disabled || readOnly) return;
      const next = values.filter(
        (v) => v.id !== refToRemove.id && v.name !== refToRemove.name
      );
      onChange?.(next);
    },
    [disabled, readOnly, values, onChange]
  );

  const handleClearSingle = useCallback(() => {
    if (disabled || readOnly) return;
    setQuery("");
    onChange?.(null, null);
    onSelect?.(null);
    inputRef.current?.focus();
  }, [disabled, readOnly, onChange, onSelect]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (disabled || readOnly) return;

    if (!isOpen && (e.key === "ArrowDown" || e.key === "Enter")) {
      setIsOpen(true);
      return;
    }

    if (isOpen) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < results.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : results.length - 1
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (results[highlightedIndex]) {
          handleSelect(results[highlightedIndex]);
        } else if (allowCustom && query.trim()) {
          const customRef: DestinationRef = {
            id: `custom_${Date.now()}`,
            name: query.trim(),
            slug: query.trim().toLowerCase().replace(/\s+/g, "-"),
          };
          handleSelect(customRef);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        if (mode === "single") setQuery(singleValueName);
      }
    } else if (
      mode === "multiple" &&
      e.key === "Backspace" &&
      !query &&
      values.length > 0
    ) {
      handleRemoveChip(values[values.length - 1]);
    }
  };

  const sizeClasses = {
    sm: "min-h-9 px-2.5 rounded-lg",
    md: "min-h-11 px-3.5 rounded-[var(--radius-button)]",
    lg: "min-h-12 px-4 rounded-xl",
  }[size];

  const isCompact = variant === "compact" || size === "sm";

  return (
    <div
      ref={containerRef}
      className={cn("relative flex w-full flex-col gap-1.5", className)}
    >
      {label ? (
        <label
          htmlFor={inputId}
          className={cn(
            getTypographyClassName("label"),
            "flex items-center justify-between text-[var(--color-muted)]",
            disabled ? "opacity-60" : ""
          )}
        >
          <span>
            {label}
            {required ? (
              <span className="text-[var(--color-accent)] ml-0.5">*</span>
            ) : null}
          </span>
        </label>
      ) : null}

      {/* Input container */}
      <div
        className={cn(
          "relative flex items-center transition-all duration-200",
          mode === "multiple" ? "min-h-11 flex-wrap gap-1.5 p-1.5" : "",
          "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)]",
          "focus-within:border-[var(--color-accent)] focus-within:ring-2 focus-within:ring-[var(--color-accent-wash)]",
          disabled
            ? "cursor-not-allowed opacity-60 bg-[var(--color-surface-muted)]"
            : "",
          error ? "border-rose-500 ring-1 ring-rose-500/20" : ""
        )}
      >
        {/* Left Icon (single mode) */}
        {mode === "single" ? (
          <div className="pointer-events-none pl-3 text-[var(--color-muted)]">
            <MapPin size={isCompact ? 14 : 16} aria-hidden="true" />
          </div>
        ) : null}

        {/* Multiple Mode Chips */}
        {mode === "multiple"
          ? values.map((ref) => (
              <span
                key={ref.id}
                className={cn(
                  getTypographyClassName("caption"),
                  "inline-flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-1 text-[var(--color-on-surface)]"
                )}
              >
                <span>{ref.name}</span>
                {!disabled && !readOnly ? (
                  <button
                    type="button"
                    onClick={() => handleRemoveChip(ref)}
                    className="ml-0.5 rounded-full p-0.5 text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                    aria-label={`Remove ${ref.name}`}
                  >
                    <X size={12} aria-hidden="true" />
                  </button>
                ) : null}
              </span>
            ))
          : null}

        {/* Text Input */}
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          disabled={disabled}
          readOnly={readOnly}
          value={query}
          aria-label={ariaLabel || label || placeholder}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-controls={isOpen ? `${inputId}-listbox` : undefined}
          role="combobox"
          placeholder={
            mode === "multiple" && values.length > 0
              ? "+ Add destination…"
              : placeholder
          }
          onFocus={() => {
            if (!disabled && !readOnly) {
              setIsOpen(true);
            }
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
            setHighlightedIndex(0);
          }}
          onKeyDown={handleKeyDown}
          className={cn(
            isCompact
              ? getTypographyClassName("bodySm")
              : getTypographyClassName("bodyMd"),
            "w-full flex-1 bg-transparent text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none",
            mode === "single"
              ? cn(sizeClasses, "pl-2 pr-8")
              : "min-w-[120px] px-2 py-1",
            inputClassName
          )}
        />

        {/* Action icons right */}
        <div className="absolute right-2.5 flex items-center gap-1 text-[var(--color-muted)]">
          {isLoading ? (
            <Loader2
              size={15}
              className="animate-spin text-[var(--color-accent)]"
            />
          ) : mode === "single" && query && !disabled && !readOnly ? (
            <button
              type="button"
              onClick={handleClearSingle}
              className="rounded-full p-1 hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
              aria-label="Clear destination"
            >
              <X size={14} aria-hidden="true" />
            </button>
          ) : (
            <Search size={14} className="opacity-50" aria-hidden="true" />
          )}
        </div>
      </div>

      {/* Floating Popover Dropdown */}
      {isOpen && (
        <div
          id={`${inputId}-listbox`}
          role="listbox"
          aria-label="Destination suggestions"
          className={cn(
            "absolute left-0 top-[calc(100%+0.25rem)] z-50 min-w-full overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-1.5 shadow-xl transition-all animate-in fade-in zoom-in-95",
            menuClassName
          )}
          style={{
            boxShadow:
              "0 12px 32px -4px rgba(0, 0, 0, 0.12), 0 4px 12px -2px rgba(0, 0, 0, 0.08)",
          }}
        >
          {/* Header indicator */}
          <div className="flex items-center justify-between px-2.5 py-1 text-[var(--color-muted)]">
            <span
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1"
              )}
            >
              {hasQuery ? (
                <>
                  <Search size={11} aria-hidden="true" />
                  <span>Matching Catalog Destinations</span>
                </>
              ) : (
                <>
                  <Sparkles
                    size={11}
                    className="text-[var(--color-accent)]"
                    aria-hidden="true"
                  />
                  <span>Popular & Recommended Destinations</span>
                </>
              )}
            </span>
            {isLoading ? (
              <span className={cn(getTypographyClassName("caption"))}>
                Searching…
              </span>
            ) : null}
          </div>

          {/* Results list */}
          <div className="max-h-56 overflow-y-auto space-y-0.5 p-0.5">
            {results.length > 0 ? (
              results.map((item, index) => {
                const isSelected =
                  mode === "single"
                    ? singleValueName.toLowerCase() === item.name.toLowerCase()
                    : values.some(
                        (v) =>
                          v.id === item.id ||
                          v.name.toLowerCase() === item.name.toLowerCase()
                      );
                const isHighlighted = index === highlightedIndex;

                return (
                  <button
                    key={item.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    onClick={() => handleSelect(item)}
                    className={cn(
                      "group flex w-full items-center justify-between gap-3 rounded-lg px-2.5 py-2 text-left transition-colors cursor-pointer",
                      isHighlighted
                        ? "bg-[var(--color-surface-hover)] text-[var(--color-on-surface)]"
                        : "text-[var(--color-on-surface)]",
                      isSelected &&
                        "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md border transition-colors",
                          isSelected
                            ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                            : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] group-hover:text-[var(--color-on-surface)]"
                        )}
                      >
                        <MapPin size={13} />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span
                          className={cn(
                            getTypographyClassName("bodySm"),
                            "truncate"
                          )}
                        >
                          {item.name}
                        </span>
                        {item.matchedFrom ? (
                          <span
                            className={cn(
                              getTypographyClassName("caption"),
                              "text-[var(--color-muted)]"
                            )}
                          >
                            Matched alias: {item.matchedFrom}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {isSelected ? (
                      <Check
                        size={14}
                        className="shrink-0 text-[var(--color-accent)]"
                      />
                    ) : null}
                  </button>
                );
              })
            ) : (
              <div className="py-4 px-3 text-center">
                <p
                  className={cn(
                    getTypographyClassName("bodySm"),
                    "text-[var(--color-muted)]"
                  )}
                >
                  No destination found in catalog.
                </p>
                {allowCustom && query.trim() ? (
                  <button
                    type="button"
                    onClick={() => {
                      const customRef: DestinationRef = {
                        id: `custom_${Date.now()}`,
                        name: query.trim(),
                        slug: query.trim().toLowerCase().replace(/\s+/g, "-"),
                      };
                      handleSelect(customRef);
                    }}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "mt-2 inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1.5 text-[var(--color-accent)] hover:bg-[var(--color-accent-wash)] transition-colors cursor-pointer"
                    )}
                  >
                    <span>
                      Use &ldquo;{query.trim()}&rdquo; as custom destination
                    </span>
                  </button>
                ) : null}
              </div>
            )}
          </div>

          {searchError ? (
            <p
              className={cn(
                getTypographyClassName("caption"),
                "border-t border-[var(--color-border)] px-2.5 py-1.5 text-[var(--color-accent)]"
              )}
            >
              {searchError}
            </p>
          ) : null}
        </div>
      )}

      {/* Error or Helper message */}
      {error ? (
        <p
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-accent)]"
          )}
        >
          {error}
        </p>
      ) : helperText ? (
        <p
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

export default DestinationSelect;
