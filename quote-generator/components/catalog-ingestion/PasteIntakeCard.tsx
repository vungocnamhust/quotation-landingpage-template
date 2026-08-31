"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionSourceChannel, IngestionSourceDocumentType } from "./types.ts";

const CHANNEL_OPTIONS: Array<{ value: IngestionSourceChannel; label: string }> = [
  { value: "email", label: "Email" },
  { value: "zalo", label: "Zalo" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "portal", label: "Supplier portal" },
  { value: "in_person", label: "In person" },
  { value: "internal", label: "Internal note" },
];

const DOCUMENT_TYPE_OPTIONS: Array<{ value: IngestionSourceDocumentType; label: string }> = [
  { value: "rate_sheet", label: "Rate sheet" },
  { value: "contract", label: "Contract" },
  { value: "amendment", label: "Amendment" },
  { value: "quotation", label: "Quotation" },
  { value: "promotion", label: "Promotion" },
  { value: "manual_note", label: "Manual note" },
];

interface Props {
  isExtracting: boolean;
  errorMessage: string | null;
  onExtract: (input: { rawText: string; sourceChannel: IngestionSourceChannel; sourceDocumentType: IngestionSourceDocumentType }) => void;
}

export function PasteIntakeCard({ isExtracting, errorMessage, onExtract }: Props) {
  const [rawText, setRawText] = useState("");
  const [sourceChannel, setSourceChannel] = useState<IngestionSourceChannel>("email");
  const [sourceDocumentType, setSourceDocumentType] = useState<IngestionSourceDocumentType>("rate_sheet");

  const canExtract = rawText.trim().length > 0 && !isExtracting;

  return (
    <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-xs">
      <div>
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          Paste a tariff email or message
        </h2>
        <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
          The Extractor never computes prices or dates itself — it only transcribes verbatim
          text for the deterministic parser to interpret.
        </p>
      </div>

      <textarea
        value={rawText}
        onChange={(event) => setRawText(event.target.value)}
        rows={10}
        placeholder="Paste the supplier's raw email/message text here…"
        className={cn(
          getTypographyClassName("bodyMd"),
          "w-full resize-y rounded-[var(--radius-input)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] outline-none focus:border-[var(--color-accent)]",
        )}
      />

      <div className="flex flex-wrap gap-4">
        <label className="flex flex-col gap-1">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Channel</span>
          <select
            value={sourceChannel}
            onChange={(event) => setSourceChannel(event.target.value as IngestionSourceChannel)}
            className={cn(
              getTypographyClassName("bodySm"),
              "rounded-[var(--radius-input)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]",
            )}
          >
            {CHANNEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Document type</span>
          <select
            value={sourceDocumentType}
            onChange={(event) => setSourceDocumentType(event.target.value as IngestionSourceDocumentType)}
            className={cn(
              getTypographyClassName("bodySm"),
              "rounded-[var(--radius-input)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]",
            )}
          >
            {DOCUMENT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {errorMessage ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-danger)]")}>{errorMessage}</p>
      ) : null}

      <button
        type="button"
        disabled={!canExtract}
        onClick={() => onExtract({ rawText, sourceChannel, sourceDocumentType })}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "flex w-fit items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        <Sparkles size={18} aria-hidden="true" />
        <span>{isExtracting ? "Extracting…" : "Extract"}</span>
      </button>
    </section>
  );
}
