"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Truck } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { createSupplier, updateSupplier, type SupplierInput, type SupplierProfile } from "../../lib/quotationApi.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";

export type SupplierDrawerMode = "create" | "edit" | null;

type Props = {
  mode: SupplierDrawerMode;
  editingSupplier?: SupplierProfile | null;
  onClose: () => void;
  onSaved: (saved: SupplierProfile) => void;
  onMutate: () => Promise<unknown>;
};

const SUPPLIER_TYPES: string[] = [
  "direct",
  "dmc",
  "wholesaler",
  "bedbank",
  "ota",
  "freelancer",
  "gov",
  "other",
];

const PREFERRED_STATUSES: string[] = ["preferred", "recommended", "standard", "backup", "do_not_use"];

const QUALITY_TIERS: string[] = ["ultra_luxury", "luxury", "premium", "standard", "value"];

const blankDraft = (): SupplierInput => ({
  name: "",
  legal_name: "",
  supplier_type: "dmc",
  country: "",
  city: "",
  default_currency: "USD",
  preferred_status: "standard",
  quality_tier: null,
  contact_json: {},
  payment_terms_json: null,
  cancellation_policy_json: { tiers: [], no_show_penalty_percent: 100 },
  child_policy_json: { bands: [] },
  credit_terms_days: 0,
});

function toDraft(supplier: SupplierProfile): SupplierInput {
  return {
    name: supplier.name,
    legal_name: supplier.legal_name ?? "",
    supplier_type: supplier.supplier_type,
    country: supplier.country ?? "",
    city: supplier.city ?? "",
    destination_id: supplier.destination_id ?? undefined,
    default_currency: supplier.default_currency,
    preferred_status: supplier.preferred_status,
    quality_tier: supplier.quality_tier ?? null,
    contact_json: supplier.contact_json ?? {},
    payment_terms_json: supplier.payment_terms_json ?? null,
    cancellation_policy_json: supplier.cancellation_policy_json ?? { tiers: [], no_show_penalty_percent: 100 },
    child_policy_json: supplier.child_policy_json ?? { bands: [] },
    bank_details_ref: supplier.bank_details_ref ?? "",
    tax_code: supplier.tax_code ?? "",
    credit_terms_days: supplier.credit_terms_days ?? 0,
    internal_notes: supplier.internal_notes ?? "",
  };
}

export function SupplierPreferredStatusBadge({ status }: { status?: string | null }) {
  const value = status || "standard";
  const badgeClasses: Record<string, string> = {
    preferred: "bg-amber-50 text-amber-800 border-amber-300",
    recommended: "bg-emerald-50 text-emerald-700 border-emerald-200",
    standard: "bg-neutral-100 text-neutral-700 border-neutral-200",
    backup: "bg-sky-50 text-sky-700 border-sky-200",
    do_not_use: "bg-rose-600 text-white border-rose-700",
  };

  return (
    <span
      className={cn(
        getTypographyClassName("caption"),
        "inline-flex items-center rounded-full px-2 py-0.5 border",
        badgeClasses[value] || badgeClasses.standard
      )}
    >
      {value.replace(/_/g, " ")}
    </span>
  );
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
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  disabled?: boolean;
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
          <option key={opt} value={opt}>
            {opt.replace(/_/g, " ")}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SupplierManageDrawer(props: Props) {
  const { mode, onClose, editingSupplier } = props;

  useEffect(() => {
    if (!mode) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mode, onClose]);

  if (!mode) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={editingSupplier ? "Edit Supplier" : "Add Supplier"}
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs"
    >
      <SupplierManageDrawerContent
        key={editingSupplier ? `edit:${editingSupplier.id}` : `create:${mode}`}
        {...props}
      />
    </div>
  );
}

function SupplierManageDrawerContent({ editingSupplier, onClose, onSaved, onMutate }: Props) {
  const { toast } = useToast();
  const [draft, setDraft] = useState<SupplierInput>(editingSupplier ? toDraft(editingSupplier) : blankDraft());
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");

  const setDraftField = <K extends keyof SupplierInput>(key: K, next: SupplierInput[K]) =>
    setDraft((current) => ({ ...current, [key]: next }));

  const cancellationTiers = draft.cancellation_policy_json?.tiers ?? [];
  const childBands = draft.child_policy_json?.bands ?? [];

  const addCancellationTier = () =>
    setDraftField("cancellation_policy_json", {
      tiers: [...cancellationTiers, { days_before_service_min: 0, penalty_percent: 0 }],
      no_show_penalty_percent: draft.cancellation_policy_json?.no_show_penalty_percent ?? 100,
      note: draft.cancellation_policy_json?.note,
    });

  const updateCancellationTier = (index: number, field: "days_before_service_min" | "penalty_percent", value: number) => {
    const next = cancellationTiers.map((tier, i) => (i === index ? { ...tier, [field]: value } : tier));
    setDraftField("cancellation_policy_json", {
      tiers: next,
      no_show_penalty_percent: draft.cancellation_policy_json?.no_show_penalty_percent ?? 100,
      note: draft.cancellation_policy_json?.note,
    });
  };

  const removeCancellationTier = (index: number) =>
    setDraftField("cancellation_policy_json", {
      tiers: cancellationTiers.filter((_, i) => i !== index),
      no_show_penalty_percent: draft.cancellation_policy_json?.no_show_penalty_percent ?? 100,
      note: draft.cancellation_policy_json?.note,
    });

  const addChildBand = () =>
    setDraftField("child_policy_json", {
      bands: [...childBands, { age_min: 0, age_max: 11, charge_percent: 50 }],
      infant_age_max: draft.child_policy_json?.infant_age_max,
      note: draft.child_policy_json?.note,
    });

  const updateChildBand = (index: number, field: "age_min" | "age_max" | "charge_percent", value: number) => {
    const next = childBands.map((band, i) => (i === index ? { ...band, [field]: value } : band));
    setDraftField("child_policy_json", {
      bands: next,
      infant_age_max: draft.child_policy_json?.infant_age_max,
      note: draft.child_policy_json?.note,
    });
  };

  const removeChildBand = (index: number) =>
    setDraftField("child_policy_json", {
      bands: childBands.filter((_, i) => i !== index),
      infant_age_max: draft.child_policy_json?.infant_age_max,
      note: draft.child_policy_json?.note,
    });

  const saveSupplier = async () => {
    if (!draft.name.trim() || !draft.supplier_type || !draft.default_currency.trim()) {
      const warningMsg = "Name, supplier type, and default currency are required.";
      setMessage(warningMsg);
      toast(warningMsg, "warning");
      return;
    }
    setPending(true);
    try {
      const saved = editingSupplier ? await updateSupplier(editingSupplier.id, draft) : await createSupplier(draft);
      await onMutate();
      toast(`Supplier "${saved.name}" saved successfully.`, "success");
      onSaved(saved);
      onClose();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Supplier could not be saved.";
      setMessage(errMsg);
      toast(errMsg, "error");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
      <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              {editingSupplier ? "Edit Supplier" : "Add Supplier"}
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              Creditor-side registry entry — hotels, DMCs, wholesalers, and other vendors we pay.
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
          <FormField label="Supplier Name" value={draft.name} onChange={(v) => setDraftField("name", v)} disabled={pending} required />
          <FormField
            label="Legal Name"
            value={draft.legal_name || ""}
            onChange={(v) => setDraftField("legal_name", v)}
            disabled={pending}
          />

          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Supplier Type"
              value={draft.supplier_type}
              options={SUPPLIER_TYPES}
              onChange={(v) => setDraftField("supplier_type", v as SupplierInput["supplier_type"])}
              disabled={pending}
            />
            <FormField
              label="Default Currency"
              value={draft.default_currency}
              onChange={(v) => setDraftField("default_currency", v.toUpperCase())}
              disabled={pending}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Country" value={draft.country || ""} onChange={(v) => setDraftField("country", v)} disabled={pending} />
            <FormField label="City" value={draft.city || ""} onChange={(v) => setDraftField("city", v)} disabled={pending} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Preferred Status"
              value={draft.preferred_status || "standard"}
              options={PREFERRED_STATUSES}
              onChange={(v) => setDraftField("preferred_status", v as SupplierInput["preferred_status"])}
              disabled={pending}
            />
            <SelectField
              label="Quality Tier"
              value={draft.quality_tier || "standard"}
              options={QUALITY_TIERS}
              onChange={(v) => setDraftField("quality_tier", v as SupplierInput["quality_tier"])}
              disabled={pending}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField
              label="Contact Person"
              value={draft.contact_json?.person || ""}
              onChange={(v) => setDraftField("contact_json", { ...draft.contact_json, person: v })}
              disabled={pending}
            />
            <FormField
              label="Contact Email"
              type="email"
              value={draft.contact_json?.email || ""}
              onChange={(v) => setDraftField("contact_json", { ...draft.contact_json, email: v })}
              disabled={pending}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField
              label="Contact Phone"
              value={draft.contact_json?.phone || ""}
              onChange={(v) => setDraftField("contact_json", { ...draft.contact_json, phone: v })}
              disabled={pending}
            />
            <FormField
              label="Website"
              value={draft.contact_json?.website || ""}
              onChange={(v) => setDraftField("contact_json", { ...draft.contact_json, website: v })}
              disabled={pending}
            />
          </div>

          {/* Payment terms (A.1) */}
          <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
            <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>Payment terms</legend>
            <div className="grid grid-cols-2 gap-3">
              <FormField
                label="Deposit %"
                type="number"
                value={draft.payment_terms_json?.deposit_percent ?? ""}
                onChange={(v) =>
                  setDraftField("payment_terms_json", { ...draft.payment_terms_json, deposit_percent: v === "" ? null : Number(v) })
                }
                disabled={pending}
              />
              <FormField
                label="Deposit due (days after confirm)"
                type="number"
                value={draft.payment_terms_json?.deposit_due_days_after_confirm ?? ""}
                onChange={(v) =>
                  setDraftField("payment_terms_json", {
                    ...draft.payment_terms_json,
                    deposit_due_days_after_confirm: v === "" ? null : Number(v),
                  })
                }
                disabled={pending}
              />
            </div>
            <div className="mt-3">
              <FormField
                label="Balance due (days before service)"
                type="number"
                value={draft.payment_terms_json?.balance_due_days_before_service ?? ""}
                onChange={(v) =>
                  setDraftField("payment_terms_json", {
                    ...draft.payment_terms_json,
                    balance_due_days_before_service: v === "" ? null : Number(v),
                  })
                }
                disabled={pending}
              />
            </div>
          </fieldset>

          {/* Cancellation policy (A.2) */}
          <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
            <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>Cancellation tiers</legend>
            <div className="flex flex-col gap-2">
              {cancellationTiers.map((tier, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="number"
                    value={tier.days_before_service_min}
                    disabled={pending}
                    onChange={(e) => updateCancellationTier(index, "days_before_service_min", Number(e.target.value))}
                    placeholder="Days before"
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 w-28 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>days → penalty</span>
                  <input
                    type="number"
                    value={tier.penalty_percent}
                    disabled={pending}
                    onChange={(e) => updateCancellationTier(index, "penalty_percent", Number(e.target.value))}
                    placeholder="%"
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 w-20 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => removeCancellationTier(index)}
                    className="ml-auto text-[var(--color-muted)] hover:text-rose-600 cursor-pointer"
                    aria-label="Remove tier"
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                disabled={pending}
                onClick={addCancellationTier}
                className={cn(
                  getTypographyClassName("caption"),
                  "flex w-fit items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
                )}
              >
                <Plus size={12} aria-hidden="true" />
                <span>Add tier</span>
              </button>
            </div>
          </fieldset>

          {/* Child policy (A.3) */}
          <fieldset className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3">
            <legend className={cn(getTypographyClassName("label"), "px-1 text-[var(--color-muted)]")}>Child age bands</legend>
            <div className="flex flex-col gap-2">
              {childBands.map((band, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="number"
                    value={band.age_min}
                    disabled={pending}
                    onChange={(e) => updateChildBand(index, "age_min", Number(e.target.value))}
                    placeholder="Age min"
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 w-20 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>–</span>
                  <input
                    type="number"
                    value={band.age_max}
                    disabled={pending}
                    onChange={(e) => updateChildBand(index, "age_max", Number(e.target.value))}
                    placeholder="Age max"
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 w-20 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <input
                    type="number"
                    value={band.charge_percent}
                    disabled={pending}
                    onChange={(e) => updateChildBand(index, "charge_percent", Number(e.target.value))}
                    placeholder="% of adult"
                    className={cn(
                      getTypographyClassName("bodySm"),
                      "min-h-9 w-24 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2"
                    )}
                  />
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => removeChildBand(index)}
                    className="ml-auto text-[var(--color-muted)] hover:text-rose-600 cursor-pointer"
                    aria-label="Remove band"
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                disabled={pending}
                onClick={addChildBand}
                className={cn(
                  getTypographyClassName("caption"),
                  "flex w-fit items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
                )}
              >
                <Plus size={12} aria-hidden="true" />
                <span>Add age band</span>
              </button>
            </div>
          </fieldset>

          <div className="grid grid-cols-2 gap-3">
            <FormField
              label="Bank details ref"
              value={draft.bank_details_ref || ""}
              onChange={(v) => setDraftField("bank_details_ref", v)}
              disabled={pending}
            />
            <FormField
              label="Credit terms (days)"
              type="number"
              value={draft.credit_terms_days ?? 0}
              onChange={(v) => setDraftField("credit_terms_days", Number(v) || 0)}
              disabled={pending}
            />
          </div>

          <div className="flex flex-wrap gap-3 mt-2">
            <button
              type="button"
              disabled={pending}
              onClick={() => void saveSupplier()}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
              )}
            >
              <span className="inline-flex items-center gap-2">
                <Truck size={16} aria-hidden="true" />
                {pending ? "Saving…" : "Save Supplier"}
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
    );
}

export default SupplierManageDrawer;
