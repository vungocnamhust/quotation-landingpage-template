"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import {
  MapPin,
  Search,
  X,
  Check,
  Loader2,
  Sparkles,
  ArrowRight,
  Plane,
  RotateCcw,
  Sparkle,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { DestinationRef } from "./types.ts";
import { useDestinationSearch } from "./useDestinationSearch.ts";
import {
  formatRouteString,
  parseRouteTokens,
} from "../../lib/rules/routeRules.ts";

export type RouteSequenceInputProps = {
  values?: DestinationRef[];
  destinations?: string[];
  onChange?: (values: DestinationRef[], formattedString: string) => void;
  routingConstraints?: string;
  onRoutingConstraintsChange?: (constraints: string) => void;
  onApplyToItinerary?: (values: DestinationRef[]) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "compact";
  showConstraintsField?: boolean;
  showApplyButton?: boolean;
  className?: string;
};

export function RouteSequenceInput({
  values = [],
  destinations = [],
  onChange,
  routingConstraints = "",
  onRoutingConstraintsChange,
  onApplyToItinerary,
  label = "Route Sequence & Destinations",
  placeholder = "+ Add next destination or paste route…",
  disabled = false,
  readOnly = false,
  required = false,
  size = "md",
  variant = "default",
  showConstraintsField = true,
  showApplyButton = true,
  className,
}: RouteSequenceInputProps) {
  const generatedId = useId();
  const inputId = `route-sequence-${generatedId}`;
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Normalize initial items from either DestinationRef[] or string[]
  const effectiveValues: DestinationRef[] =
    values.length > 0
      ? values
      : destinations.map((d, idx) => ({
          id: `dst_${d.toLowerCase().replace(/[^a-z0-9]/g, "_") || idx}`,
          name: d,
          slug: d.toLowerCase().replace(/\s+/g, "-"),
        }));

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const { results, isLoading, hasQuery } = useDestinationSearch(query);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setQuery("");
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const commitItems = useCallback(
    (nextItems: DestinationRef[]) => {
      const formatted = formatRouteString(nextItems);
      onChange?.(nextItems, formatted);
    },
    [onChange]
  );

  const handleSelect = useCallback(
    (item: DestinationRef) => {
      const next = [...effectiveValues, item];
      commitItems(next);
      setQuery("");
      setIsOpen(false);
      inputRef.current?.focus();
    },
    [effectiveValues, commitItems]
  );

  const handleRemoveChip = useCallback(
    (indexToRemove: number) => {
      if (disabled || readOnly) return;
      const next = effectiveValues.filter((_, i) => i !== indexToRemove);
      commitItems(next);
    },
    [disabled, readOnly, effectiveValues, commitItems]
  );

  const handleMoveChip = useCallback(
    (fromIndex: number, toIndex: number) => {
      if (disabled || readOnly) return;
      if (toIndex < 0 || toIndex >= effectiveValues.length) return;
      const next = [...effectiveValues];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      commitItems(next);
    },
    [disabled, readOnly, effectiveValues, commitItems]
  );

  const handleClearAll = useCallback(() => {
    if (disabled || readOnly) return;
    commitItems([]);
    setQuery("");
    inputRef.current?.focus();
  }, [disabled, readOnly, commitItems]);

  const handlePaste = useCallback(
    (e: ClipboardEvent<HTMLInputElement>) => {
      const pastedText = e.clipboardData.getData("text");
      const tokens = parseRouteTokens(pastedText);

      if (tokens.length > 1) {
        e.preventDefault();
        const newItems: DestinationRef[] = tokens.map((token, idx) => ({
          id: `dst_${token.toLowerCase().replace(/[^a-z0-9]/g, "_")}_${Date.now()}_${idx}`,
          name: token,
          slug: token.toLowerCase().replace(/\s+/g, "-"),
        }));
        const next = [...effectiveValues, ...newItems];
        commitItems(next);
        setQuery("");
        setIsOpen(false);
      }
    },
    [effectiveValues, commitItems]
  );

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
        if (results.length > 0 && results[highlightedIndex]) {
          handleSelect(results[highlightedIndex]);
        } else if (query.trim()) {
          const customRef: DestinationRef = {
            id: `dst_${query.trim().toLowerCase().replace(/[^a-z0-9]/g, "_")}`,
            name: query.trim(),
            slug: query.trim().toLowerCase().replace(/\s+/g, "-"),
          };
          handleSelect(customRef);
        }
      } else if (e.key === "Escape") {
        setIsOpen(false);
      }
    } else if (e.key === "Backspace" && !query && effectiveValues.length > 0) {
      handleRemoveChip(effectiveValues.length - 1);
    }
  };

  const isCompact = size === "sm" || variant === "compact";
  const arrivalCity = effectiveValues[0]?.name ?? null;
  const departureCity =
    effectiveValues[effectiveValues.length - 1]?.name ?? null;

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Top Header Label */}
      <div className="flex items-center justify-between">
        <label
          htmlFor={inputId}
          className={cn(
            getTypographyClassName("label"),
            "flex items-center gap-1.5 text-[var(--color-on-surface)]",
            disabled ? "opacity-60" : ""
          )}
        >
          <MapPin size={14} className="text-[var(--color-accent)]" />
          <span>{label}</span>
          {required ? (
            <span className="text-[var(--color-accent)]">*</span>
          ) : null}
        </label>

        {effectiveValues.length > 0 && !disabled && !readOnly ? (
          <button
            type="button"
            onClick={handleClearAll}
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 text-[var(--color-muted)] hover:text-rose-600 transition-colors cursor-pointer"
            )}
          >
            <RotateCcw size={11} />
            <span>Clear Route</span>
          </button>
        ) : null}
      </div>

      {/* Main Route Sequence Box with Connected Arrow Chips */}
      <div
        ref={containerRef}
        className={cn(
          "relative flex flex-col gap-2.5 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 shadow-2xs transition-all duration-200",
          "focus-within:border-[var(--color-accent)] focus-within:ring-2 focus-within:ring-[var(--color-accent-wash)]",
          disabled
            ? "cursor-not-allowed opacity-60 bg-[var(--color-surface-muted)]"
            : ""
        )}
      >
        {/* Interactive Route Flow Chain */}
        <div className="flex flex-wrap items-center gap-2">
          {effectiveValues.map((ref, index) => {
            const isFirst = index === 0;
            const isLast = index === effectiveValues.length - 1;

            return (
              <div key={ref.id || index} className="flex items-center gap-2">
                {/* Destination Chip */}
                <div
                  className={cn(
                    "group inline-flex items-center gap-1.5 rounded-full border shadow-2xs transition-all",
                    isFirst
                      ? "border-emerald-300 bg-emerald-50/80 text-emerald-950"
                      : isLast
                        ? "border-amber-300 bg-amber-50/80 text-amber-950"
                        : "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-on-surface)]",
                    isCompact ? "px-2.5 py-0.5" : "px-3 py-1"
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                      isFirst
                        ? "bg-emerald-600 text-white"
                        : isLast
                          ? "bg-amber-600 text-white"
                          : "bg-[var(--color-border-strong)] text-[var(--color-on-surface)]"
                    )}
                  >
                    {index + 1}
                  </span>

                  <span className={cn(getTypographyClassName("bodySm"), "font-medium")}>
                    {ref.name}
                  </span>

                  {!disabled && !readOnly ? (
                    <button
                      type="button"
                      onClick={() => handleRemoveChip(index)}
                      className="ml-0.5 rounded-full p-0.5 text-[var(--color-muted)] hover:bg-black/10 hover:text-rose-600 transition-colors cursor-pointer"
                      aria-label={`Remove ${ref.name}`}
                    >
                      <X size={12} aria-hidden="true" />
                    </button>
                  ) : null}
                </div>

                {/* Connecting Directional Arrow */}
                {!isLast ? (
                  <div
                    className="flex items-center text-[var(--color-accent)] opacity-80"
                    aria-hidden="true"
                  >
                    <ArrowRight size={14} className="stroke-[2.5]" />
                  </div>
                ) : null}
              </div>
            );
          })}

          {/* Inline Autocomplete Input */}
          <div className="relative min-w-[200px] flex-1">
            <div className="flex items-center gap-1.5 px-2">
              <Search
                size={14}
                className="text-[var(--color-muted)] shrink-0"
                aria-hidden="true"
              />
              <input
                ref={inputRef}
                id={inputId}
                type="text"
                disabled={disabled}
                readOnly={readOnly}
                value={query}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                aria-controls={isOpen ? `${inputId}-listbox` : undefined}
                role="combobox"
                placeholder={
                  effectiveValues.length > 0
                    ? "+ Add next stop (e.g. Hue)…"
                    : placeholder
                }
                onFocus={() => {
                  if (!disabled && !readOnly) setIsOpen(true);
                }}
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (!isOpen) setIsOpen(true);
                  setHighlightedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                className={cn(
                  getTypographyClassName("bodySm"),
                  "w-full bg-transparent text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none"
                )}
              />
              {isLoading ? (
                <Loader2
                  size={14}
                  className="animate-spin text-[var(--color-accent)] shrink-0"
                />
              ) : null}
            </div>
          </div>
        </div>

        {/* Floating Catalog Autocomplete Menu */}
        {isOpen && (
          <div
            id={`${inputId}-listbox`}
            role="listbox"
            aria-label="Destination suggestions"
            className="absolute left-0 top-[calc(100%+0.35rem)] z-50 min-w-full overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-1.5 shadow-xl transition-all animate-in fade-in zoom-in-95"
            style={{
              boxShadow:
                "0 12px 32px -4px rgba(0, 0, 0, 0.14), 0 4px 12px -2px rgba(0, 0, 0, 0.08)",
            }}
          >
            {/* Header info */}
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
                    <span>Matching Destinations</span>
                  </>
                ) : (
                  <>
                    <Sparkles
                      size={11}
                      className="text-[var(--color-accent)]"
                      aria-hidden="true"
                    />
                    <span>Suggested Next Destinations</span>
                  </>
                )}
              </span>
              <span className={cn(getTypographyClassName("caption"))}>
                Press Enter or click to add
              </span>
            </div>

            {/* Results items */}
            <div className="max-h-56 overflow-y-auto space-y-0.5 p-0.5">
              {results.length > 0 ? (
                results.map((item, index) => {
                  const isHighlighted = index === highlightedIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      role="option"
                      aria-selected={isHighlighted}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      onClick={() => handleSelect(item)}
                      className={cn(
                        "group flex w-full items-center justify-between gap-3 rounded-lg px-2.5 py-2 text-left transition-colors cursor-pointer",
                        isHighlighted
                          ? "bg-[var(--color-surface-hover)] text-[var(--color-on-surface)]"
                          : "text-[var(--color-on-surface)]"
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)] group-hover:text-[var(--color-accent)]">
                          <MapPin size={12} />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span
                            className={cn(
                              getTypographyClassName("bodySm"),
                              "truncate font-medium"
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
                              Alias: {item.matchedFrom}
                            </span>
                          ) : null}
                        </div>
                      </div>
                      <span
                        className={cn(
                          getTypographyClassName("caption"),
                          "text-[var(--color-accent)] opacity-0 group-hover:opacity-100 transition-opacity"
                        )}
                      >
                        + Add to route
                      </span>
                    </button>
                  );
                })
              ) : (
                <div className="py-3 px-3 text-center">
                  <p
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "text-[var(--color-muted)]"
                    )}
                  >
                    No catalog destination found.
                  </p>
                  {query.trim() ? (
                    <button
                      type="button"
                      onClick={() => {
                        handleSelect({
                          id: `dst_${query.trim().toLowerCase().replace(/[^a-z0-9]/g, "_")}`,
                          name: query.trim(),
                          slug: query.trim().toLowerCase().replace(/\s+/g, "-"),
                        });
                      }}
                      className={cn(
                        getTypographyClassName("caption"),
                        "mt-1.5 text-[var(--color-accent)] hover:underline cursor-pointer"
                      )}
                    >
                      Use custom: &quot;{query.trim()}&quot;
                    </button>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Gateway Summary Badge & 1-Click Sync Button */}
      {effectiveValues.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] px-3 py-2 border border-[var(--color-border)]">
          <div className="flex items-center gap-2 text-[var(--color-on-surface)]">
            <Plane
              size={14}
              className="text-[var(--color-accent)] shrink-0"
              aria-hidden="true"
            />
            <span className={cn(getTypographyClassName("caption"))}>
              <strong className="text-emerald-700">In:</strong> {arrivalCity || "TBD"}
              {" • "}
              <strong className="text-amber-700">Out:</strong> {departureCity || "TBD"}
              {" • "}
              <span>
                {effectiveValues.length} Destinations ({Math.max(0, effectiveValues.length - 1)} Legs)
              </span>
            </span>
          </div>

          {showApplyButton && onApplyToItinerary && !disabled && !readOnly ? (
            <button
              type="button"
              onClick={() => onApplyToItinerary(effectiveValues)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex items-center gap-1.5 rounded-full bg-[var(--color-surface)] px-3 py-1 text-[var(--color-accent)] border border-[var(--color-accent)]/30 hover:bg-[var(--color-accent-wash)] transition-colors shadow-2xs cursor-pointer"
              )}
            >
              <Sparkle size={12} className="text-[var(--color-accent)]" />
              <span>Sync to Itinerary Days</span>
            </button>
          ) : null}
        </div>
      ) : null}

      {/* Dedicated Field for Fixed Flights & Dates Constraints */}
      {showConstraintsField ? (
        <label className="flex flex-col gap-1.5 pt-1">
          <span
            className={cn(
              getTypographyClassName("label"),
              "text-[var(--color-muted)]"
            )}
          >
            Fixed Flights & Timing Constraints (Optional)
          </span>
          <textarea
            rows={2}
            disabled={disabled}
            placeholder="e.g. International flights already booked (VN50 arriving 06:30 on Nov 01), Halong Cruise departs Nov 03 12:00..."
            value={routingConstraints}
            onChange={(e) => onRoutingConstraintsChange?.(e.target.value)}
            className={cn(
              getTypographyClassName("bodyMd"),
              "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
            )}
          />
        </label>
      ) : null}
    </div>
  );
}
