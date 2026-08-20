"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { ChevronDown, Search, X, Check, Loader2, Sparkles, User, Settings2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { TravelDesignerProfile, TravelDesignerSelectProps } from "./types.ts";
import { useTravelDesignerSearch } from "./useTravelDesignerSearch.ts";
import { ProfileAvatar, TravelDesignerManageDrawer, type TravelDesignerDrawerMode } from "./TravelDesignerManageDrawer.tsx";

export function TravelDesignerSelect({
  value,
  brandId,
  onChange,
  label,
  placeholder = "Select Travel Designer...",
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
}: TravelDesignerSelectProps) {
  const generatedId = useId();
  const selectId = customId || generatedId;
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [drawerMode, setDrawerMode] = useState<TravelDesignerDrawerMode>(null);

  const { items, isLoading, mutate } = useTravelDesignerSearch(query, {
    active: "true",
    initialSelectedId: value,
  });

  const activeProfiles = items.filter((p) => p.isActive);
  const selectedProfile = items.find((p) => p.id === value) ?? null;

  // Close popover on outside click
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

  // Focus search input when popover opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = useCallback(
    (profile: TravelDesignerProfile) => {
      onChange?.(profile.id, profile);
      setIsOpen(false);
      setQuery("");
    },
    [onChange]
  );

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onChange?.(null, null);
    },
    [onChange]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < activeProfiles.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeProfiles[highlightedIndex]) {
        handleSelect(activeProfiles[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      setQuery("");
    }
  };

  const sizeClasses = {
    sm: "min-h-9 px-2.5 py-1",
    md: "min-h-11 px-3 py-2",
    lg: "min-h-13 px-4 py-2.5",
  };

  const isInteractive = !disabled && !readOnly;

  return (
    <div className={cn("relative flex flex-col gap-1.5 w-full", className)} ref={containerRef}>
      {/* Optional Label */}
      {label ? (
        <label
          htmlFor={selectId}
          className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center justify-between")}
        >
          <span>
            {label}
            {required ? <span className="text-[var(--color-accent)] ml-0.5">*</span> : null}
          </span>
          {allowManage && isInteractive ? (
            <button
              type="button"
              onClick={() => setDrawerMode("manage")}
              className="flex items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
            >
              <Settings2 size={12} aria-hidden="true" />
              <span>Manage</span>
            </button>
          ) : null}
        </label>
      ) : null}

      {/* Main Trigger Button */}
      <button
        id={selectId}
        type="button"
        disabled={disabled}
        onClick={() => isInteractive && setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel || label || placeholder}
        className={cn(
          "flex w-full items-center justify-between gap-2.5 rounded-[var(--radius-button)] border text-left transition-all",
          sizeClasses[size],
          variant === "inline"
            ? "border-transparent bg-transparent hover:bg-[var(--color-surface-muted)] shadow-none"
            : variant === "compact"
            ? "border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xs"
            : "border-[var(--color-border-strong)] bg-[var(--color-surface)] shadow-2xs",
          isOpen ? "ring-2 ring-[var(--color-focus)] border-transparent" : "",
          error ? "border-rose-500 ring-1 ring-rose-500" : "",
          disabled ? "opacity-60 cursor-not-allowed bg-[var(--color-surface-muted)]" : "cursor-pointer",
          getTypographyClassName("bodyMd")
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          {selectedProfile ? (
            <>
              <ProfileAvatar profile={selectedProfile} size={size} />
              <div className="min-w-0 flex-1">
                <span className="block truncate text-[var(--color-on-surface)]">
                  {selectedProfile.name}
                </span>
                {variant !== "compact" && (
                  <span className={cn(getTypographyClassName("caption"), "block truncate text-[var(--color-muted)]")}>
                    {selectedProfile.email}
                  </span>
                )}
              </div>
            </>
          ) : (
            <span className="text-[var(--color-muted)] truncate">{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0 text-[var(--color-muted)]">
          {selectedProfile && isInteractive ? (
            <span
              role="button"
              tabIndex={0}
              onClick={handleClear}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.stopPropagation();
                  onChange?.(null);
                }
              }}
              className="rounded-full p-1 hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-on-surface)] transition-colors cursor-pointer"
              title="Clear selection"
              aria-label="Clear designer selection"
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

      {/* Dropdown Popover */}
      {isOpen ? (
        <div
          role="presentation"
          className="absolute top-full left-0 z-50 mt-1.5 w-full min-w-[280px] rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2 shadow-xl animate-in fade-in-0 zoom-in-95 duration-150"
        >
          {/* Search Input */}
          <div className="relative mb-2">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-muted)]"
              aria-hidden="true"
            />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setHighlightedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Search designer by name..."
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
                aria-label="Clear search query"
              >
                <X size={14} aria-hidden="true" />
              </button>
            ) : null}
          </div>

          {/* Listbox */}
          <div
            role="listbox"
            aria-label="Travel Designers"
            className="flex max-h-60 flex-col gap-1 overflow-y-auto overflow-x-hidden py-0.5"
          >
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-[var(--color-muted)]">
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                <span className={cn(getTypographyClassName("caption"))}>Loading designers...</span>
              </div>
            ) : activeProfiles.length === 0 ? (
              <div className="py-6 text-center text-[var(--color-muted)]">
                <User size={24} className="mx-auto mb-1 opacity-40" aria-hidden="true" />
                <p className={cn(getTypographyClassName("bodySm"))}>No designers match &quot;{query}&quot;</p>
                {allowManage ? (
                  <button
                    type="button"
                    onClick={() => {
                      setIsOpen(false);
                      setDrawerMode("create");
                    }}
                    className={cn(
                      getTypographyClassName("caption"),
                      "mt-2 text-[var(--color-accent)] hover:underline cursor-pointer"
                    )}
                  >
                    + Create new designer
                  </button>
                ) : null}
              </div>
            ) : (
              activeProfiles.map((profile, index) => {
                const isSelected = profile.id === value;
                const isHighlighted = index === highlightedIndex;

                return (
                  <button
                    key={profile.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(profile)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2.5 rounded-[var(--radius-button)] px-2.5 py-2 text-left transition-colors cursor-pointer",
                      isHighlighted
                        ? "bg-[var(--color-surface-muted)] text-[var(--color-on-surface)]"
                        : "text-[var(--color-on-surface)]",
                      isSelected ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]" : ""
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <ProfileAvatar profile={profile} size="sm" />
                      <div className="min-w-0 flex-1">
                        <span className="block truncate">{profile.name}</span>
                        <span
                          className={cn(
                            getTypographyClassName("caption"),
                            "block truncate text-[var(--color-muted)]"
                          )}
                        >
                          {profile.email}
                        </span>
                      </div>
                    </div>

                    {isSelected ? (
                      <Check size={16} className="text-[var(--color-accent)] shrink-0" aria-hidden="true" />
                    ) : null}
                  </button>
                );
              })
            )}
          </div>

          {/* Quick Actions Footer */}
          {allowManage ? (
            <div className="mt-2 flex items-center justify-between border-t border-[var(--color-border)] pt-2 px-1">
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  setDrawerMode("create");
                }}
                className={cn(
                  getTypographyClassName("caption"),
                  "flex items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
                )}
              >
                <Sparkles size={12} aria-hidden="true" />
                <span>+ New Designer</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  setDrawerMode("manage");
                }}
                className={cn(
                  getTypographyClassName("caption"),
                  "text-[var(--color-muted)] hover:text-[var(--color-on-surface)] cursor-pointer"
                )}
              >
                Manage all
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Validation Error & Helper Text */}
      {error ? (
        <span className={cn(getTypographyClassName("caption"), "text-rose-600")}>{error}</span>
      ) : helperText ? (
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{helperText}</span>
      ) : null}

      {/* Manage / Create Drawer Modal */}
      {drawerMode ? (
        <TravelDesignerManageDrawer
          mode={drawerMode}
          brandId={brandId}
          profiles={items}
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
