"use client";

import { useEffect, useState } from "react";
import { Package, Plus, Trash2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { createProduct, getDestination, updateProduct, type ProductInput, type ProductProfile } from "../../lib/quotationApi.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { AccommodationSelect } from "../accommodation/AccommodationSelect.tsx";
import { DestinationSelect } from "../destination/DestinationSelect.tsx";
import type { DestinationRef } from "../destination/types.ts";
import { SupplierSelect } from "../supplier/SupplierSelect.tsx";
import { RatePanel } from "./rates/RatePanel.tsx";
import {
  CATEGORY_OPTIONS,
  DEFAULT_CHARGE_UNIT_BY_CATEGORY,
  isOtherSubcategory,
  SUBCATEGORY_BY_CATEGORY,
  SUGGESTED_ATTRIBUTE_KEYS_BY_CATEGORY,
  type ProductCategory,
  type ProductCategoryAttributeValue,
} from "./types.ts";

export type ProductDrawerMode = "create" | "edit" | null;

type Props = {
  mode: ProductDrawerMode;
  editingProduct?: ProductProfile | null;
  presetCategory?: ProductCategory;
  presetDestinationId?: string;
  onClose: () => void;
  onSaved: (saved: ProductProfile) => void;
  onMutate: () => Promise<unknown>;
};

const UNIT_OPTIONS = ["room", "person", "vehicle", "group", "ticket", "flight_seat", "visa_case", "set"];
const TIME_BASIS_OPTIONS = ["night", "day", "trip"];

const ORIGIN_ELIGIBLE_CATEGORIES: ProductCategory[] = ["transportation", "flights"];

const blankDraft = (category: ProductCategory, destinationId: string): ProductInput => ({
  destination_id: destinationId,
  origin_destination_id: null,
  category,
  title: "",
  supplier_id: null,
  property_id: null,
  subcategory: null,
  subcategory_note: null,
  supplier_product_name: null,
  unit: null,
  time_basis: null,
  default_min_pax: null,
  default_max_pax: null,
  category_attributes: {},
});

function toDraft(product: ProductProfile): ProductInput {
  return {
    destination_id: product.destination_id,
    origin_destination_id: product.origin_destination_id ?? null,
    category: product.category,
    title: product.title,
    supplier_id: product.supplier_id ?? null,
    property_id: product.property_id ?? null,
    subcategory: product.subcategory ?? null,
    subcategory_note: product.subcategory_note ?? null,
    supplier_product_name: product.supplier_product_name ?? null,
    unit: product.unit,
    time_basis: product.time_basis,
    default_min_pax: product.default_min_pax ?? null,
    default_max_pax: product.default_max_pax ?? null,
    category_attributes: product.category_attributes ?? {},
  };
}

function FormField({
  label,
  value,
  type = "text",
  onChange,
  disabled,
  required,
}: {
  label: string;
  value: string | number;
  type?: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        {label}
        {required ? <span className="text-[var(--color-accent)] ml-0.5">*</span> : null}
      </span>
      <input
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:opacity-60"
        )}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  disabled,
  formatLabel,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  disabled?: boolean;
  formatLabel?: (option: string) => string;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
        )}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {formatLabel ? formatLabel(opt.value) : opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ProductManageDrawer({
  mode,
  editingProduct,
  presetCategory = "experience",
  presetDestinationId = "",
  onClose,
  onSaved,
  onMutate,
}: Props) {
  const { toast } = useToast();
  const [draft, setDraft] = useState<ProductInput>(
    editingProduct ? toDraft(editingProduct) : blankDraft(presetCategory, presetDestinationId)
  );
  const [destinationRef, setDestinationRef] = useState<DestinationRef | null>(null);
  const [originDestinationRef, setOriginDestinationRef] = useState<DestinationRef | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [newAttributeKey, setNewAttributeKey] = useState("");

  useEffect(() => {
    if (!mode) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mode, onClose]);

  useEffect(() => {
    if (!editingProduct?.destination_id) return;
    let cancelled = false;
    getDestination(editingProduct.destination_id)
      .then((destination) => {
        if (!cancelled) setDestinationRef({ id: destination.id, name: destination.name, slug: destination.slug });
      })
      .catch(() => {
        // Destination lookup is a display convenience only; draft.destination_id already holds the id.
      });
    return () => {
      cancelled = true;
    };
  }, [editingProduct?.destination_id]);

  useEffect(() => {
    if (!editingProduct?.origin_destination_id) return;
    let cancelled = false;
    getDestination(editingProduct.origin_destination_id)
      .then((destination) => {
        if (!cancelled) setOriginDestinationRef({ id: destination.id, name: destination.name, slug: destination.slug });
      })
      .catch(() => {
        // Destination lookup is a display convenience only; draft.origin_destination_id already holds the id.
      });
    return () => {
      cancelled = true;
    };
  }, [editingProduct?.origin_destination_id]);

  if (!mode) return null;

  const setDraftField = <K extends keyof ProductInput>(key: K, next: ProductInput[K]) =>
    setDraft((current) => ({ ...current, [key]: next }));

  const handleCategoryChange = (nextCategory: ProductCategory) => {
    const [defaultUnit, defaultTimeBasis] = DEFAULT_CHARGE_UNIT_BY_CATEGORY[nextCategory];
    const originEligible = ORIGIN_ELIGIBLE_CATEGORIES.includes(nextCategory);
    if (!originEligible) setOriginDestinationRef(null);
    setDraft((current) => ({
      ...current,
      category: nextCategory,
      subcategory: null,
      subcategory_note: null,
      unit: defaultUnit,
      time_basis: defaultTimeBasis,
      property_id: nextCategory === "accommodation" ? current.property_id : null,
      origin_destination_id: originEligible ? current.origin_destination_id : null,
    }));
  };

  const subcategoryOptions = SUBCATEGORY_BY_CATEGORY[draft.category];
  const suggestedAttributeKeys = SUGGESTED_ATTRIBUTE_KEYS_BY_CATEGORY[draft.category];
  const attributeEntries = Object.entries(draft.category_attributes ?? {});

  const setAttribute = (key: string, value: ProductCategoryAttributeValue) =>
    setDraftField("category_attributes", { ...(draft.category_attributes ?? {}), [key]: value });

  const removeAttribute = (key: string) => {
    const next = { ...(draft.category_attributes ?? {}) };
    delete next[key];
    setDraftField("category_attributes", next);
  };

  const saveProduct = async () => {
    if (!draft.title.trim() || !draft.destination_id) {
      const warningMsg = "Title and destination are required.";
      setMessage(warningMsg);
      toast(warningMsg, "warning");
      return;
    }
    setPending(true);
    try {
      const saved = editingProduct ? await updateProduct(editingProduct.id, draft) : await createProduct(draft);
      await onMutate();
      toast(`Product "${saved.title}" saved successfully.`, "success");
      onSaved(saved);
      onClose();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Product could not be saved.";
      setMessage(errMsg);
      toast(errMsg, "error");
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={editingProduct ? "Edit Product" : "Add Product"}
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs"
    >
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              {editingProduct ? "Edit Product" : "Add Product"}
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              A sellable service variant — location + category + supplier + variant. No pricing here (15.3).
            </p>
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
          <SelectField
            label="Category"
            value={draft.category}
            options={CATEGORY_OPTIONS.map((c) => ({ value: c, label: c.replace(/_/g, " ") }))}
            onChange={(v) => handleCategoryChange(v as ProductCategory)}
            disabled={pending}
          />

          <FormField label="Title" value={draft.title} onChange={(v) => setDraftField("title", v)} disabled={pending} required />

          {ORIGIN_ELIGIBLE_CATEGORIES.includes(draft.category) ? (
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Origin (optional)</span>
                <DestinationSelect
                  value={originDestinationRef?.name ?? null}
                  onChange={(_name, ref) => {
                    setOriginDestinationRef(ref ?? null);
                    setDraftField("origin_destination_id", ref?.id ?? null);
                  }}
                  disabled={pending}
                />
              </label>
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Destination<span className="text-[var(--color-accent)] ml-0.5">*</span>
                </span>
                <DestinationSelect
                  value={destinationRef?.name ?? null}
                  onChange={(_name, ref) => {
                    setDestinationRef(ref ?? null);
                    setDraftField("destination_id", ref?.id ?? "");
                  }}
                  disabled={pending}
                />
              </label>
            </div>
          ) : (
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Destination<span className="text-[var(--color-accent)] ml-0.5">*</span>
              </span>
              <DestinationSelect
                value={destinationRef?.name ?? null}
                onChange={(_name, ref) => {
                  setDestinationRef(ref ?? null);
                  setDraftField("destination_id", ref?.id ?? "");
                }}
                disabled={pending}
              />
            </label>
          )}

          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Subcategory"
              value={draft.subcategory ?? ""}
              options={[{ value: "", label: "(none)" }, ...subcategoryOptions]}
              onChange={(v) => setDraftField("subcategory", v || null)}
              disabled={pending}
            />
            {isOtherSubcategory(draft.subcategory) ? (
              <FormField
                label="Subcategory note"
                value={draft.subcategory_note ?? ""}
                onChange={(v) => setDraftField("subcategory_note", v || null)}
                disabled={pending}
              />
            ) : null}
          </div>

          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Supplier (optional)</span>
            <SupplierSelect
              value={draft.supplier_id ?? null}
              onChange={(id) => setDraftField("supplier_id", id)}
              disabled={pending}
              placeholder="No supplier yet — data now, DMC later"
            />
          </label>

          {draft.category === "accommodation" ? (
            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Accommodation property (for content/photos)
              </span>
              <AccommodationSelect
                value={draft.property_id ?? null}
                destinationId={draft.destination_id || undefined}
                onChange={(_profile, id) => setDraftField("property_id", id)}
                allowCustom={false}
                disabled={pending}
              />
            </label>
          ) : null}

          <FormField
            label="Supplier product name (source fact, immutable after create)"
            value={draft.supplier_product_name ?? ""}
            onChange={(v) => setDraftField("supplier_product_name", v || null)}
            disabled={pending || !!editingProduct}
          />

          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Charge unit"
              value={draft.unit ?? DEFAULT_CHARGE_UNIT_BY_CATEGORY[draft.category][0]}
              options={UNIT_OPTIONS.map((u) => ({ value: u, label: u.replace(/_/g, " ") }))}
              onChange={(v) => setDraftField("unit", v as ProductInput["unit"])}
              disabled={pending}
            />
            <SelectField
              label="Time basis"
              value={draft.time_basis ?? DEFAULT_CHARGE_UNIT_BY_CATEGORY[draft.category][1]}
              options={TIME_BASIS_OPTIONS.map((t) => ({ value: t, label: t }))}
              onChange={(v) => setDraftField("time_basis", v as ProductInput["time_basis"])}
              disabled={pending}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField
              label="Default min pax"
              type="number"
              value={draft.default_min_pax ?? ""}
              onChange={(v) => setDraftField("default_min_pax", v === "" ? null : Number(v))}
              disabled={pending}
            />
            <FormField
              label="Default max pax"
              type="number"
              value={draft.default_max_pax ?? ""}
              onChange={(v) => setDraftField("default_max_pax", v === "" ? null : Number(v))}
              disabled={pending}
            />
          </div>

          <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
            <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>
              Category attributes
            </legend>
            <div className="flex flex-col gap-2">
              {attributeEntries.map(([key, value]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className={cn(getTypographyClassName("bodySm"), "w-1/3 truncate text-[var(--color-muted)]")}>{key}</span>
                  <input
                    type="text"
                    value={String(value)}
                    disabled={pending}
                    onChange={(e) => setAttribute(key, e.target.value)}
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => removeAttribute(key)}
                    className="text-[var(--color-muted)] hover:text-rose-600 cursor-pointer"
                    aria-label={`Remove ${key}`}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <select
                  value=""
                  disabled={pending}
                  onChange={(e) => {
                    if (e.target.value) {
                      setAttribute(e.target.value, "");
                      setNewAttributeKey("");
                    }
                  }}
                  className={cn(
                    getTypographyClassName("bodySm"),
                    "min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                  )}
                >
                  <option value="">+ Suggested key…</option>
                  {suggestedAttributeKeys
                    .filter((key) => !(key in (draft.category_attributes ?? {})))
                    .map((key) => (
                      <option key={key} value={key}>
                        {key}
                      </option>
                    ))}
                </select>
                <input
                  type="text"
                  value={newAttributeKey}
                  disabled={pending}
                  onChange={(e) => setNewAttributeKey(e.target.value)}
                  placeholder="custom_key"
                  className={cn(
                    getTypographyClassName("bodySm"),
                    "min-h-9 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                  )}
                />
                <button
                  type="button"
                  disabled={pending || !newAttributeKey.trim()}
                  onClick={() => {
                    setAttribute(newAttributeKey.trim(), "");
                    setNewAttributeKey("");
                  }}
                  className={cn(
                    getTypographyClassName("caption"),
                    "flex items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer disabled:opacity-50"
                  )}
                >
                  <Plus size={12} aria-hidden="true" />
                  <span>Add</span>
                </button>
              </div>
            </div>
          </fieldset>

          <div className="flex flex-wrap gap-3 mt-2">
            <button
              type="button"
              disabled={pending}
              onClick={() => void saveProduct()}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
              )}
            >
              <span className="inline-flex items-center gap-2">
                <Package size={16} aria-hidden="true" />
                {pending ? "Saving…" : "Save Product"}
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

        {editingProduct ? (
          <div className="mt-6 border-t border-[var(--color-border)] pt-6">
            <RatePanel
              productId={editingProduct.id}
              productCategory={editingProduct.category}
              defaultCurrency={null}
            />
          </div>
        ) : null}

        {message ? (
          <p aria-live="polite" className={cn(getTypographyClassName("bodySm"), "mt-4 text-[var(--color-muted)]")}>
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export default ProductManageDrawer;
