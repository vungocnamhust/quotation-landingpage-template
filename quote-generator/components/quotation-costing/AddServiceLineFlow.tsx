"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Plus } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { listProductRates, type RateProfile } from "../../lib/quotationApi.ts";
import { CATEGORY_OPTIONS, DEFAULT_CHARGE_UNIT_BY_CATEGORY, SUBCATEGORY_BY_CATEGORY, type ProductCategory, type ProductProfile } from "../product/types.ts";
import { ProductSelect } from "../product/ProductSelect.tsx";
import { RateEditorDrawer } from "../product/rates/RateEditorDrawer.tsx";
import { emptyServiceLineDraft, draftToWriteInput, type ServiceLineDraftForm } from "../../lib/rules/costingAdapter.ts";
import type { ServiceLineWriteInput } from "./types.ts";

export interface AddServiceLineFlowProps {
  sheetCurrency: string;
  disabled?: boolean;
  onAdd: (input: Omit<ServiceLineWriteInput, "base_costing_revision">) => Promise<unknown>;
}

type Mode = "catalog" | "manual";

const inputClass = cn(
  getTypographyClassName("bodySm"),
  "h-9 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)]",
);

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{label}</span>
      {children}
    </div>
  );
}

export function AddServiceLineFlow({ sheetCurrency, disabled, onAdd }: AddServiceLineFlowProps) {
  const [mode, setMode] = useState<Mode>("catalog");
  const [draft, setDraft] = useState<ServiceLineDraftForm>(() => emptyServiceLineDraft({ qtyUnit: 1, qtyTime: 1 }));
  const [selectedProduct, setSelectedProduct] = useState<ProductProfile | null>(null);
  const [rateDrawerOpen, setRateDrawerOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: rateList, mutate: mutateRates } = useSWR(
    draft.productId ? ["product-rates", draft.productId, draft.serviceDate] : null,
    ([, productId, onDate]) => listProductRates(productId, { lifecycle: "active", onDate: onDate || undefined }),
    { revalidateOnFocus: false },
  );

  const selectedRate: RateProfile | undefined = useMemo(
    () => rateList?.items.find((rate) => rate.id === draft.rateId),
    [rateList, draft.rateId],
  );

  const needsFx = Boolean(
    (mode === "catalog" && selectedRate && selectedRate.currency !== sheetCurrency) ||
      (mode === "manual" && draft.costCurrency && draft.costCurrency !== sheetCurrency),
  );

  const canSubmit =
    mode === "catalog"
      ? Boolean(draft.productId && draft.rateId && draft.priceLineId) && (!needsFx || Boolean(draft.fxRatePpm))
      : Boolean(draft.category && draft.title && draft.unit && draft.timeBasis && draft.unitCostMinor !== null && draft.costCurrency) &&
        (!needsFx || Boolean(draft.fxRatePpm));

  const resetDraft = () => {
    setDraft(emptyServiceLineDraft({ qtyUnit: 1, qtyTime: 1 }));
    setSelectedProduct(null);
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      const { base_costing_revision, ...rest } = draftToWriteInput(draft, 0);
      void base_costing_revision;
      const result = await onAdd(rest);
      if (result) resetDraft();
    } finally {
      setIsSubmitting(false);
    }
  };

  const category = draft.category as ProductCategory | null;

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-center gap-1 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-1 w-fit">
        {(["catalog", "manual"] as Mode[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setMode(tab)}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] px-3 py-1.5 cursor-pointer transition-colors",
              mode === tab ? "bg-[var(--color-surface)] text-[var(--color-on-surface)] shadow-2xs" : "text-[var(--color-muted)]",
            )}
          >
            {tab === "catalog" ? "Pick from catalog" : "Type manually"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Field label="Day #">
          <input
            type="number"
            min={1}
            value={draft.dayNumber ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, dayNumber: e.target.value ? Number(e.target.value) : null }))}
            className={inputClass}
            placeholder="whole trip"
          />
        </Field>
        <Field label="Qty (unit)">
          <input
            type="number"
            min={1}
            value={draft.qtyUnit}
            onChange={(e) => setDraft((d) => ({ ...d, qtyUnit: Math.max(1, Number(e.target.value) || 1) }))}
            className={inputClass}
          />
        </Field>
        <Field label="Qty (time)">
          <input
            type="number"
            min={1}
            value={draft.qtyTime}
            onChange={(e) => setDraft((d) => ({ ...d, qtyTime: Math.max(1, Number(e.target.value) || 1) }))}
            className={inputClass}
          />
        </Field>
        <Field label="Service date">
          <input
            type="date"
            value={draft.serviceDate ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, serviceDate: e.target.value || null }))}
            className={inputClass}
          />
        </Field>
      </div>

      {mode === "catalog" ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="md:col-span-3">
            <ProductSelect
              value={draft.productId}
              onChange={(productId, product) => {
                setSelectedProduct(product ?? null);
                setDraft((d) => ({ ...d, productId, rateId: null, priceLineId: null }));
              }}
              size="sm"
              allowManage={false}
              placeholder="Select a product..."
            />
          </div>
          {draft.productId ? (
            <div className="flex flex-col gap-2">
              <button
                type="button"
                disabled={disabled}
                onClick={() => setRateDrawerOpen(true)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "flex w-fit items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent-wash)] disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
                )}
              >
                <Plus size={14} aria-hidden="true" />
                <span>Tạo bảng giá mới cho sản phẩm này</span>
              </button>
              {rateList?.items.length === 0 ? (
                <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  No active rate covers this service date.
                </p>
              ) : null}
              <Field label="Rate">
                <select
                  value={draft.rateId ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, rateId: e.target.value || null, priceLineId: null }))}
                  className={inputClass}
                >
                  <option value="">Select rate...</option>
                  {(rateList?.items ?? []).map((rate) => (
                    <option key={rate.id} value={rate.id}>
                      {rate.season_name || rate.valid_from} — {rate.valid_from}..{rate.valid_to} ({rate.currency})
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          ) : null}
          {selectedRate ? (
            <Field label="Price line">
              <select
                value={draft.priceLineId ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, priceLineId: e.target.value ? Number(e.target.value) : null }))}
                className={inputClass}
              >
                <option value="">Select price line...</option>
                {selectedRate.lines.map((line) => (
                  <option key={line.id} value={line.id}>
                    {line.price_for}/{line.occupancy_basis} · {line.unit} · {(line.amount_minor / (selectedRate.currency === "VND" ? 1 : 100)).toLocaleString()} {selectedRate.currency}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          {needsFx ? (
            <Field label={`FX rate ppm (${selectedRate?.currency} → ${sheetCurrency})`}>
              <input
                type="number"
                min={1}
                value={draft.fxRatePpm ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, fxRatePpm: e.target.value ? Number(e.target.value) : null }))}
                className={inputClass}
                placeholder="e.g. 1000000 = 1:1"
              />
            </Field>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Field label="Category">
            <select
              value={draft.category ?? ""}
              onChange={(e) => setDraft((d) => {
                const nextCategory = (e.target.value || null) as ProductCategory | null;
                const defaults = nextCategory ? DEFAULT_CHARGE_UNIT_BY_CATEGORY[nextCategory] : null;
                return {
                  ...d,
                  category: nextCategory,
                  subcategory: null,
                  unit: defaults ? defaults[0] : d.unit,
                  timeBasis: defaults ? defaults[1] : d.timeBasis,
                };
              })}
              className={inputClass}
            >
              <option value="">Select category...</option>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          {category ? (
            <Field label="Subcategory">
              <select
                value={draft.subcategory ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, subcategory: e.target.value || null }))}
                className={inputClass}
              >
                <option value="">None</option>
                {SUBCATEGORY_BY_CATEGORY[category].map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          <Field label="Title">
            <input
              type="text"
              value={draft.title ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value || null }))}
              className={inputClass}
              placeholder="e.g. E-visa processing"
            />
          </Field>
          <Field label="Unit">
            <input
              type="text"
              value={draft.unit ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, unit: e.target.value || null }))}
              className={inputClass}
            />
          </Field>
          <Field label="Time basis">
            <input
              type="text"
              value={draft.timeBasis ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, timeBasis: e.target.value || null }))}
              className={inputClass}
            />
          </Field>
          <Field label="Unit cost (minor)">
            <input
              type="number"
              min={0}
              value={draft.unitCostMinor ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, unitCostMinor: e.target.value ? Number(e.target.value) : null }))}
              className={inputClass}
            />
          </Field>
          <Field label="Cost currency">
            <input
              type="text"
              value={draft.costCurrency ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, costCurrency: e.target.value.toUpperCase() || null }))}
              className={inputClass}
              placeholder={sheetCurrency}
            />
          </Field>
          {needsFx ? (
            <Field label={`FX rate ppm (${draft.costCurrency} → ${sheetCurrency})`}>
              <input
                type="number"
                min={1}
                value={draft.fxRatePpm ?? ""}
                onChange={(e) => setDraft((d) => ({ ...d, fxRatePpm: e.target.value ? Number(e.target.value) : null }))}
                className={inputClass}
                placeholder="e.g. 1000000 = 1:1"
              />
            </Field>
          ) : null}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Field label="Sell override (minor, optional)">
          <input
            type="number"
            min={0}
            value={draft.sellOverrideMinor ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, sellOverrideMinor: e.target.value ? Number(e.target.value) : null }))}
            className={inputClass}
            placeholder="leave blank to use markup"
          />
        </Field>
        <Field label="Note">
          <input
            type="text"
            value={draft.note ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value || null }))}
            className={inputClass}
          />
        </Field>
      </div>

      <button
        type="button"
        disabled={disabled || isSubmitting || !canSubmit}
        onClick={handleSubmit}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "flex w-fit items-center gap-1.5 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
        )}
      >
        <Plus size={14} aria-hidden="true" />
        <span>Add line</span>
      </button>

      <RateEditorDrawer
        mode={rateDrawerOpen ? "create" : null}
        productId={draft.productId ?? ""}
        productCategory={selectedProduct?.category}
        defaultCurrency={sheetCurrency}
        defaultValidityDate={draft.serviceDate}
        activateOnSave
        editingRate={null}
        onClose={() => setRateDrawerOpen(false)}
        onSaved={(activeRate) => {
          // The activation response is authoritative. Seed it immediately so a
          // momentary list revalidation failure cannot strand an active rate in
          // the drawer or make the service-line draft lose its selection.
          void mutateRates(
            (current) => ({
              items: [activeRate, ...(current?.items ?? []).filter((rate) => rate.id !== activeRate.id)],
              total: Math.max(current?.total ?? 0, 1),
            }),
            { revalidate: false },
          );
          setDraft((current) => ({
            ...current,
            rateId: activeRate.id,
            priceLineId: activeRate.lines.length === 1 ? activeRate.lines[0].id ?? null : null,
          }));
          void mutateRates();
        }}
      />
    </div>
  );
}

export default AddServiceLineFlow;
