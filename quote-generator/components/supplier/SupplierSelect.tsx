"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown, Search, X, Check, Loader2, Truck, Plus } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { SupplierProfile, SupplierSelectProps } from "./types.ts";
import { useSupplierSearch } from "./useSupplierSearch.ts";
import { SupplierManageDrawer, SupplierPreferredStatusBadge, type SupplierDrawerMode } from "./SupplierManageDrawer.tsx";

export function SupplierSelect({
  value,
  onChange,
  label,
  placeholder = "Select Supplier...",
  disabled = false,
  readOnly = false,
  required = false,
  size = "md",
  variant = "default",
  allowManage = true,
  className,
  error,
  helperText,
  "aria-label": ariaLabel,
  id: customId,
}: SupplierSelectProps) {
  const generatedId = useId();
  const selectId = customId || generatedId;
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [drawerMode, setDrawerMode] = useState<SupplierDrawerMode>(null);

  const { items, isLoading, mutate } = useSupplierSearch(query, {
    active: "true",
    initialSelectedId: value,
  });

  const activeSuppliers = items.filter((s) => s.is_active);
  const selectedSupplier = items.find((s) => s.id === value) ?? null;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = (supplier: SupplierProfile) => {
    onChange?.(supplier.id, supplier);
    setIsOpen(false);
    setQuery("");
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange?.(null, null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev < activeSuppliers.length - 1 ? prev + 1 : prev));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        break;
      case "Enter":
        e.preventDefault();
        if (activeSuppliers[highlightedIndex]) {
          handleSelect(activeSuppliers[highlightedIndex]);
        }
        break;
      case "Escape":
        e.preventDefault();
        setIsOpen(false);
        break;
    }
  };

  const sizeClasses = {
    sm: "min-h-9 px-2.5 py-1",
    md: "min-h-11 px-3 py-2",
    lg: "min-h-13 px-4 py-2.5",
  };

  const variantClasses = {
    default: "rounded-[var(--radius-button)] shadow-2xs border-[var(--color-border-strong)] bg-[var(--color-surface)]",
    compact: "rounded-[var(--radius-button)] shadow-2xs border-[var(--color-border)] bg-[var(--color-surface)]",
    inline: "border-transparent bg-transparent hover:bg-[var(--color-surface-muted)]",
  };

  const isInteractive = !disabled && !readOnly;

  return (
    <div ref={containerRef} className={cn("relative flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between">
        {label ? (
          <label
            htmlFor={selectId}
            className={cn(getTypographyClassName("label"), "flex items-center gap-1 text-[var(--color-muted)]", disabled && "opacity-60")}
          >
            <span>{label}</span>
            {required ? <span className="text-[var(--color-accent)]">*</span> : null}
          </label>
        ) : null}

        {allowManage ? (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setDrawerMode("create")}
            className={cn(
              getTypographyClassName("caption"),
              "text-[var(--color-accent)] hover:underline flex items-center gap-0.5 cursor-pointer disabled:opacity-50"
            )}
          >
            <Plus size={12} aria-hidden="true" />
            <span>Add supplier</span>
          </button>
        ) : null}
      </div>

      <button
        id={selectId}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel || label || "Select Supplier"}
        onClick={() => isInteractive && setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className={cn(
          "flex w-full items-center justify-between gap-2 text-left transition-all border outline-none",
          sizeClasses[size],
          variantClasses[variant],
          error
            ? "border-rose-500 ring-1 ring-rose-500"
            : isOpen
            ? "border-[var(--color-accent)] ring-2 ring-[var(--color-focus)]"
            : "border-[var(--color-border-strong)] hover:border-[var(--color-accent)]",
          !isInteractive && "cursor-default bg-[var(--color-surface-muted)]",
          isInteractive && "cursor-pointer bg-[var(--color-surface)]"
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <Truck size={16} className="shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
          {selectedSupplier ? (
            <div className="flex flex-col min-w-0">
              <span className={cn(getTypographyClassName("bodySm"), "truncate text-[var(--color-on-surface)]")}>
                {selectedSupplier.name}
              </span>
              <span className={cn(getTypographyClassName("caption"), "truncate text-[var(--color-muted)]")}>
                {[selectedSupplier.supplier_type, selectedSupplier.country].filter(Boolean).join(" · ")}
              </span>
            </div>
          ) : (
            <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)] truncate")}>{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0 text-[var(--color-muted)]">
          {selectedSupplier && isInteractive ? (
            <span
              role="button"
              tabIndex={0}
              onClick={handleClear}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.stopPropagation();
                  onChange?.(null, null);
                }
              }}
              className="rounded-full p-1 hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
              title="Clear supplier"
              aria-label="Clear supplier selection"
            >
              <X size={14} aria-hidden="true" />
            </span>
          ) : null}
          <ChevronDown
            size={16}
            className={cn("transition-transform duration-200", isOpen ? "rotate-180 text-[var(--color-accent)]" : "")}
            aria-hidden="true"
          />
        </div>
      </button>

      {isOpen ? (
        <div
          role="presentation"
          className="absolute top-full left-0 z-50 mt-1.5 w-full min-w-[300px] rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2 shadow-xl animate-in fade-in-0 zoom-in-95 duration-150"
        >
          <div className="relative mb-2">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]" aria-hidden="true" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setHighlightedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Search supplier name or legal name..."
              className={cn(
                getTypographyClassName("bodySm"),
                "h-9 w-full rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] pl-8 pr-8 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:border-[var(--color-accent)] focus:bg-[var(--color-surface)] focus:outline-none"
              )}
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] cursor-pointer"
                aria-label="Clear query"
              >
                <X size={14} aria-hidden="true" />
              </button>
            ) : null}
          </div>

          <div role="listbox" aria-label="Suppliers" className="flex max-h-60 flex-col gap-1 overflow-y-auto overflow-x-hidden py-0.5">
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-[var(--color-muted)]">
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                <span className={cn(getTypographyClassName("caption"))}>Loading suppliers...</span>
              </div>
            ) : activeSuppliers.length === 0 ? (
              <div className="py-6 text-center text-[var(--color-muted)]">
                <Truck size={24} className="mx-auto mb-1 opacity-40" aria-hidden="true" />
                <p className={cn(getTypographyClassName("bodySm"))}>No suppliers match &quot;{query}&quot;</p>
                {allowManage ? (
                  <button
                    type="button"
                    onClick={() => {
                      setIsOpen(false);
                      setDrawerMode("create");
                    }}
                    className={cn(getTypographyClassName("caption"), "mt-2 text-[var(--color-accent)] hover:underline cursor-pointer")}
                  >
                    + Add supplier
                  </button>
                ) : null}
              </div>
            ) : (
              activeSuppliers.map((supplier, index) => {
                const isSelected = supplier.id === value;
                const isHighlighted = index === highlightedIndex;

                return (
                  <button
                    key={supplier.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(supplier)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2.5 rounded-[var(--radius-button)] px-2.5 py-2 text-left transition-colors cursor-pointer",
                      isHighlighted ? "bg-[var(--color-surface-muted)] text-[var(--color-on-surface)]" : "text-[var(--color-on-surface)]",
                      isSelected ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]" : ""
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="block truncate">{supplier.name}</span>
                        <SupplierPreferredStatusBadge status={supplier.preferred_status} />
                      </div>
                      <span className={cn(getTypographyClassName("caption"), "block truncate text-[var(--color-muted)]")}>
                        {supplier.supplier_type} • {supplier.default_currency}
                      </span>
                    </div>

                    {isSelected ? <Check size={16} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" /> : null}
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : null}

      {error ? (
        <span className={cn(getTypographyClassName("caption"), "text-rose-600")}>{error}</span>
      ) : helperText ? (
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{helperText}</span>
      ) : null}

      {drawerMode ? (
        <SupplierManageDrawer
          mode={drawerMode}
          onClose={() => setDrawerMode(null)}
          onSaved={(saved) => {
            onChange?.(saved.id, saved);
          }}
          onMutate={mutate}
        />
      ) : null}
    </div>
  );
}
