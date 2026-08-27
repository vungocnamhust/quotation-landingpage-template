"use client";

import { useState } from "react";
import { CircleDollarSign } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { useToast } from "../../staff-workspace/ToastProvider.tsx";
import { PriceLinesEditor } from "./PriceLinesEditor.tsx";
import { useProductRates } from "./useProductRates.ts";
import {
  blankPriceLine,
  CHANNEL_OPTIONS,
  DOCUMENT_TYPE_OPTIONS,
  RATE_BASIS_OPTIONS,
  type RateAggregateInput,
  type RateProfile,
} from "./types.ts";

export type RateDrawerMode = "create" | "edit" | "supersede" | null;

type Props = {
  mode: RateDrawerMode;
  productId: string;
  productCategory?: string;
  defaultCurrency?: string | null;
  /** When supplied by Costing, initialise a one-day rate covering the service date. */
  defaultValidityDate?: string | null;
  /** Costing creates a draft and immediately passes it through the existing activation gate. */
  activateOnSave?: boolean;
  editingRate?: RateProfile | null;
  onClose: () => void;
  onSaved: (rate: RateProfile) => void | Promise<void>;
};

function toInput(
  rate: RateProfile | null | undefined,
  productId: string,
  defaultCurrency?: string | null,
  defaultValidityDate?: string | null,
): RateAggregateInput {
  if (!rate) {
    const validityDate = defaultValidityDate || new Date().toISOString().slice(0, 10);
    return {
      product_id: productId,
      currency: defaultCurrency ?? null,
      rate_basis: "net",
      commission_pct: null,
      valid_from: validityDate,
      valid_to: validityDate,
      season_name: null,
      blackout_json: [],
      min_pax: null,
      max_pax: null,
      tax_included: false,
      tax_pct: null,
      supplements_json: [],
      inclusions_json: [],
      exclusions_json: [],
      source_reference: null,
      source_id: null,
      source: { supplier_id: "", document_type: "manual_note", channel: "internal" },
      lines: [blankPriceLine()],
    };
  }
  return {
    product_id: rate.product_id,
    currency: rate.currency,
    rate_basis: rate.rate_basis,
    commission_pct: rate.commission_pct ?? null,
    valid_from: rate.valid_from,
    valid_to: rate.valid_to,
    season_name: rate.season_name ?? null,
    blackout_json: rate.blackout_json ?? [],
    min_pax: rate.min_pax ?? null,
    max_pax: rate.max_pax ?? null,
    tax_included: rate.tax_included,
    tax_pct: rate.tax_pct ?? null,
    supplements_json: rate.supplements_json ?? [],
    inclusions_json: rate.inclusions_json ?? [],
    exclusions_json: rate.exclusions_json ?? [],
    payment_terms_json: rate.payment_terms_json ?? null,
    cancellation_policy_json: rate.cancellation_policy_json ?? null,
    child_policy_json: rate.child_policy_json ?? null,
    source_reference: rate.source_reference ?? null,
    source_id: rate.source?.id ?? null,
    lines: rate.lines.map((line) => ({ ...line })),
  };
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{children}</span>;
}

const inputClass = cn(
  getTypographyClassName("bodyMd"),
  "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:opacity-60"
);

export function RateEditorDrawer(props: Props) {
  if (!props.mode) return null;

  return (
    <RateEditorDrawerContent
      key={`${props.mode}:${props.productId}:${props.editingRate?.id ?? "new"}:${props.defaultValidityDate ?? "today"}`}
      {...props}
      mode={props.mode}
    />
  );
}

function RateEditorDrawerContent({
  mode,
  productId,
  productCategory,
  defaultCurrency,
  defaultValidityDate,
  activateOnSave = false,
  editingRate,
  onClose,
  onSaved,
}: Omit<Props, "mode"> & { mode: Exclude<RateDrawerMode, null> }) {
  const { toast } = useToast();
  const { createDraft, updateDraft, activate, supersede } = useProductRates(productId);
  const [draft, setDraft] = useState<RateAggregateInput>(
    toInput(mode === "supersede" || mode === "edit" ? editingRate : null, productId, defaultCurrency, defaultValidityDate)
  );
  const [createdDraftId, setCreatedDraftId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");

  const setField = <K extends keyof RateAggregateInput>(key: K, value: RateAggregateInput[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const showOccupancy = productCategory === "accommodation";

  const save = async () => {
    if (!draft.valid_from || !draft.valid_to || draft.lines.length === 0) {
      const warningMsg = "Validity dates and at least one price line are required.";
      setMessage(warningMsg);
      toast(warningMsg, "warning");
      return;
    }
    setPending(true);
    try {
      let savedRate: RateProfile;
      if (mode === "edit" && editingRate) {
        savedRate = await updateDraft(editingRate.id, draft);
        toast("Rate draft saved.", "success");
      } else if (mode === "supersede" && editingRate) {
        savedRate = await supersede(editingRate.id, draft);
        toast("New rate version is now active — the old one is frozen.", "success");
      } else if (createdDraftId) {
        savedRate = await updateDraft(createdDraftId, draft);
      } else {
        savedRate = await createDraft(draft);
        setCreatedDraftId(savedRate.id);
      }

      if (activateOnSave && mode === "create") {
        savedRate = await activate(savedRate.id);
        toast("Rate created and activated.", "success");
      } else if (mode === "create") {
        toast("Rate draft created.", "success");
      }

      await onSaved(savedRate);
      onClose();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Rate could not be saved.";
      setMessage(errMsg);
      toast(errMsg, "error");
    } finally {
      setPending(false);
    }
  };

  const title = mode === "supersede" ? "New Rate Version (Supersede)" : mode === "edit" ? "Edit Draft Rate" : "New Rate";

  return (
    <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{title}</h2>
            {mode === "supersede" ? (
              <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-amber-600")}>
                Creates a new version — the current rate freezes as &ldquo;superseded&rdquo; and is never edited again.
              </p>
            ) : (
              <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
                Supplier NET cost for one product, one currency (15.3).
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3.5 transition-all cursor-pointer"
            )}
          >
            Close
          </button>
        </div>

        <div className="mt-6 grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-2">
              <FieldLabel>Currency</FieldLabel>
              <input
                className={inputClass}
                value={draft.currency ?? ""}
                disabled={pending}
                placeholder="defaults to supplier currency"
                onChange={(e) => setField("currency", e.target.value.toUpperCase() || null)}
              />
            </label>
            <label className="flex flex-col gap-2">
              <FieldLabel>Rate basis</FieldLabel>
              <select
                className={inputClass}
                value={draft.rate_basis}
                disabled={pending}
                onChange={(e) => setField("rate_basis", e.target.value as RateAggregateInput["rate_basis"])}
              >
                {RATE_BASIS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {draft.rate_basis === "gross_commissionable" ? (
            <label className="flex flex-col gap-2">
              <FieldLabel>Commission % (bps, e.g. 1000 = 10%)</FieldLabel>
              <input
                type="number"
                className={inputClass}
                value={draft.commission_pct ?? ""}
                disabled={pending}
                onChange={(e) => setField("commission_pct", e.target.value === "" ? null : Number(e.target.value))}
              />
            </label>
          ) : null}

          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-2">
              <FieldLabel>Valid from</FieldLabel>
              <input
                type="date"
                className={inputClass}
                value={draft.valid_from}
                disabled={pending}
                onChange={(e) => setField("valid_from", e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-2">
              <FieldLabel>Valid to</FieldLabel>
              <input
                type="date"
                className={inputClass}
                value={draft.valid_to}
                disabled={pending}
                onChange={(e) => setField("valid_to", e.target.value)}
              />
            </label>
          </div>

          <label className="flex flex-col gap-2">
            <FieldLabel>Season name</FieldLabel>
            <input
              className={inputClass}
              value={draft.season_name ?? ""}
              disabled={pending}
              onChange={(e) => setField("season_name", e.target.value || null)}
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-2">
              <FieldLabel>Min pax</FieldLabel>
              <input
                type="number"
                className={inputClass}
                value={draft.min_pax ?? ""}
                disabled={pending}
                onChange={(e) => setField("min_pax", e.target.value === "" ? null : Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col gap-2">
              <FieldLabel>Max pax</FieldLabel>
              <input
                type="number"
                className={inputClass}
                value={draft.max_pax ?? ""}
                disabled={pending}
                onChange={(e) => setField("max_pax", e.target.value === "" ? null : Number(e.target.value))}
              />
            </label>
          </div>

          <PriceLinesEditor
            lines={draft.lines}
            currency={draft.currency ?? defaultCurrency ?? "USD"}
            showOccupancy={showOccupancy}
            disabled={pending}
            onChange={(next) => setField("lines", next)}
          />

          <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
            <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>
              Source (where did this price come from?)
            </legend>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-2">
                <FieldLabel>Document type</FieldLabel>
                <select
                  className={inputClass}
                  value={draft.source?.document_type ?? "manual_note"}
                  disabled={pending}
                  onChange={(e) =>
                    setField("source", {
                      supplier_id: draft.source?.supplier_id ?? "",
                      ...draft.source,
                      document_type: e.target.value as never,
                    })
                  }
                >
                  {DOCUMENT_TYPE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-2">
                <FieldLabel>Channel</FieldLabel>
                <select
                  className={inputClass}
                  value={draft.source?.channel ?? "internal"}
                  disabled={pending}
                  onChange={(e) =>
                    setField("source", {
                      supplier_id: draft.source?.supplier_id ?? "",
                      ...draft.source,
                      channel: e.target.value as never,
                    })
                  }
                >
                  {CHANNEL_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="mt-3 flex flex-col gap-2">
              <FieldLabel>Source reference (e.g. email subject, contract #)</FieldLabel>
              <input
                className={inputClass}
                value={draft.source_reference ?? ""}
                disabled={pending}
                onChange={(e) => setField("source_reference", e.target.value || null)}
              />
            </label>
          </fieldset>

          <div className="flex flex-wrap gap-3 mt-2">
            <button
              type="button"
              disabled={pending}
              onClick={() => void save()}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
              )}
            >
              <span className="inline-flex items-center gap-2">
                <CircleDollarSign size={16} aria-hidden="true" />
                {pending ? "Saving…" : mode === "supersede" ? "Create New Version" : "Save Rate"}
              </span>
            </button>
            <button
              type="button"
              disabled={pending}
              onClick={onClose}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all cursor-pointer"
              )}
            >
              Cancel
            </button>
          </div>
        </div>

        {message ? (
          <p aria-live="polite" className={cn(getTypographyClassName("bodySm"), "mt-4 text-[var(--color-muted)]")}>
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export default RateEditorDrawer;
