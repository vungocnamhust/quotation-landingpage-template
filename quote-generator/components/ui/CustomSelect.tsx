"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

export interface CustomSelectOption {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
}

export interface CustomSelectProps {
  value: string | null | undefined;
  onChange: (value: string) => void;
  options: CustomSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  buttonClassName?: string;
  menuClassName?: string;
  size?: "sm" | "md" | "lg";
  "aria-label"?: string;
}

export default function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "Select an option",
  disabled = false,
  className,
  buttonClassName,
  menuClassName,
  size = "md",
  "aria-label": ariaLabel,
}: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);

  const selectedIndex = options.findIndex((opt) => opt.id === value);
  const selectedOption = selectedIndex >= 0 ? options[selectedIndex] : null;

  // Initialize highlighted index when opened
  const [prevIsOpen, setPrevIsOpen] = useState(isOpen);
  if (isOpen !== prevIsOpen) {
    setPrevIsOpen(isOpen);
    if (isOpen) {
      setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
    }
  }

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
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

  const handleSelectOption = useCallback(
    (optionId: string) => {
      onChange(optionId);
      setIsOpen(false);
      buttonRef.current?.focus();
    },
    [onChange]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement | HTMLDivElement>) => {
    if (disabled) return;

    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev < options.length - 1 ? prev + 1 : 0));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : options.length - 1));
        break;
      case "Home":
        e.preventDefault();
        setHighlightedIndex(0);
        break;
      case "End":
        e.preventDefault();
        setHighlightedIndex(options.length - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (options[highlightedIndex]) {
          handleSelectOption(options[highlightedIndex].id);
        }
        break;
      case "Escape":
      case "Tab":
        setIsOpen(false);
        break;
    }
  };

  const sizeClasses = {
    sm: "min-h-9 px-3 rounded-lg",
    md: "min-h-11 px-3.5 rounded-[var(--radius-button)]",
    lg: "min-h-12 px-4 rounded-xl",
  }[size];

  return (
    <div
      ref={containerRef}
      className={cn("relative inline-block w-full text-left", className)}
      onKeyDown={handleKeyDown}
    >
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={ariaLabel ?? placeholder}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        className={cn(
          size === "sm" ? getTypographyClassName("bodySm") : getTypographyClassName("bodyMd"),
          "flex w-full items-center justify-between gap-3 border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] cursor-pointer",
          "border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)]",
          "hover:border-[var(--color-accent)] hover:bg-[var(--color-surface-hover)]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          sizeClasses,
          isOpen && "border-[var(--color-accent)] ring-2 ring-[var(--color-accent-wash)]",
          buttonClassName
        )}
      >
        <span className="truncate">
          {selectedOption ? selectedOption.label : (
            <span className="text-[var(--color-muted)]">{placeholder}</span>
          )}
        </span>
        <svg
          className={cn(
            "h-4 w-4 shrink-0 text-[var(--color-muted)] transition-transform duration-200",
            isOpen && "rotate-180 text-[var(--color-accent)]"
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          ref={listboxRef}
          className={cn(
            "absolute left-0 top-[calc(100%+0.375rem)] z-50 min-w-full overflow-hidden rounded-xl border p-1.5 shadow-xl transition-all duration-150 animate-in fade-in zoom-in-95",
            "border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] backdrop-blur-md",
            menuClassName
          )}
          style={{
            boxShadow:
              "0 12px 32px -4px rgba(0, 0, 0, 0.12), 0 4px 12px -2px rgba(0, 0, 0, 0.08)",
          }}
          role="listbox"
          tabIndex={-1}
        >
          <div className="max-h-60 overflow-y-auto p-0.5 space-y-0.5">
            {options.map((option, index) => {
              const isSelected = option.id === value;
              const isHighlighted = index === highlightedIndex;
              return (
                <div
                  key={option.id}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelectOption(option.id)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={cn(
                    "group flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors duration-150 cursor-pointer select-none",
                    isSelected
                      ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                      : isHighlighted
                        ? "bg-[var(--color-surface-hover)] text-[var(--color-on-surface)]"
                        : "text-[var(--color-on-surface)]"
                  )}
                >
                  <div className="flex flex-col min-w-0">
                    <span
                      className={cn(
                        getTypographyClassName("bodyMd"),
                        "truncate block"
                      )}
                    >
                      {option.label}
                    </span>
                    {option.description ? (
                      <span
                        className={cn(
                          getTypographyClassName("caption"),
                          "truncate text-[var(--color-muted)] group-hover:text-[var(--color-on-surface)]"
                        )}
                      >
                        {option.description}
                      </span>
                    ) : null}
                  </div>

                  {isSelected && (
                    <svg
                      className="h-4 w-4 shrink-0 text-[var(--color-accent)]"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2.5"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
