"use client";

import { useDeferredValue, useId, useState } from "react";
import useSWR from "swr";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { quotationFetch } from "../../lib/apiError";
import type { DestinationRef } from "./factsTypes";

const API_BASE =
  process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
export type { DestinationRef } from "./factsTypes";
type SearchResponse = { items: DestinationRef[] };
const fetchJson = async <T,>(url: string): Promise<T> => {
  return quotationFetch<T>(url, undefined, "Destination search failed.");
};
const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)]",
);

export function DestinationInput({
  value,
  onChange,
  onSelect,
  disabled = false,
  label = "Destination",
}: {
  value: string | null;
  onChange: (value: string | null) => void;
  onSelect?: (ref: DestinationRef | null) => void;
  disabled?: boolean;
  label?: string;
}) {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");
  const displayValue = editing ? query : (value ?? "");
  const deferred = useDeferredValue(query);
  const id = useId();
  const { data, error, isLoading } = useSWR<SearchResponse>(
    deferred.trim().length >= 2
      ? `${API_BASE}/api/v2/destinations?query=${encodeURIComponent(deferred)}&limit=8`
      : null,
    fetchJson,
  );
  const select = (item: DestinationRef) => {
    setQuery("");
    setEditing(false);
    setMessage("");
    onChange(item.name);
    onSelect?.(item);
  };
  return (
    <div className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "text-[var(--color-muted)]",
        )}
      >
        {label}
      </span>
      <input
        aria-describedby={message ? id : undefined}
        className={inputClass}
        disabled={disabled}
        value={displayValue}
        onFocus={() => {
          setEditing(true);
          setQuery(value ?? "");
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setMessage(
            event.target.value ? "Select a destination from the catalog." : "",
          );
          onChange(null);
          onSelect?.(null);
        }}
        onBlur={() => {
          if (query && query !== value)
            setMessage(
              "Destination not found. Select an item from the catalog.",
            );
          setEditing(false);
        }}
        placeholder="Search destination"
      />
      {data?.items.length ? (
        <div className="flex flex-wrap gap-2">
          {data.items.map((item) => (
            <button
              type="button"
              key={item.id}
              disabled={disabled}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => select(item)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 text-[var(--color-on-surface)]",
              )}
            >
              {item.name}
            </button>
          ))}
        </div>
      ) : null}
      {isLoading ? (
        <p
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]",
          )}
        >
          Searching catalog…
        </p>
      ) : null}
      {error ? (
        <p
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-accent)]",
          )}
        >
          Destination catalog is unavailable. Refresh after the service is
          restored.
        </p>
      ) : null}
      {message ? (
        <p
          id={id}
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-accent)]",
          )}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}

export function DestinationMultiSelect({
  refs,
  onChange,
  disabled = false,
}: {
  refs: DestinationRef[];
  onChange: (refs: DestinationRef[]) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);
  const { data, error, isLoading } = useSWR<SearchResponse>(
    deferred.trim().length >= 2
      ? `${API_BASE}/api/v2/destinations?query=${encodeURIComponent(deferred)}&limit=8`
      : null,
    fetchJson,
  );
  const add = (item: DestinationRef) => {
    if (!refs.some((ref) => ref.id === item.id)) onChange([...refs, item]);
    setQuery("");
  };
  return (
    <div className="flex flex-col gap-2">
      <span
        className={cn(
          getTypographyClassName("label"),
          "text-[var(--color-muted)]",
        )}
      >
        Destinations
      </span>
      <div className="flex min-h-11 flex-wrap items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-2">
        {refs.map((ref) => (
          <button
            type="button"
            key={ref.id}
            disabled={disabled}
            onClick={() => onChange(refs.filter((item) => item.id !== ref.id))}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-8 rounded-[var(--radius-button)] border border-[var(--color-border)] px-2 text-[var(--color-on-surface)]",
            )}
          >
            {ref.name} ×
          </button>
        ))}
        <input
          className={cn(
            getTypographyClassName("bodyMd"),
            "min-h-8 min-w-40 flex-1 bg-transparent px-1 text-[var(--color-on-surface)]",
          )}
          disabled={disabled}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") event.preventDefault();
          }}
          placeholder="Search destination"
        />
      </div>
      {data?.items.length ? (
        <div className="flex flex-wrap gap-2">
          {data.items.map((item) => (
            <button
              type="button"
              key={item.id}
              disabled={disabled}
              onClick={() => add(item)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 text-[var(--color-on-surface)]",
              )}
            >
              {item.name}
            </button>
          ))}
        </div>
      ) : null}
      {isLoading ? (
        <p
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-muted)]",
          )}
        >
          Searching catalog…
        </p>
      ) : null}
      {error ? (
        <p
          className={cn(
            getTypographyClassName("caption"),
            "text-[var(--color-accent)]",
          )}
        >
          Destination catalog is unavailable. Refresh after the service is
          restored.
        </p>
      ) : null}
    </div>
  );
}
