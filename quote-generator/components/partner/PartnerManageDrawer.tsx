"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import {
  createPartner,
  updatePartner,
  updatePartnerStatus,
  type PartnerInput,
  type PartnerProfile,
} from "../../lib/quotationApi";

export type PartnerDrawerMode = "create" | "edit" | "manage" | null;

type Props = {
  mode: PartnerDrawerMode;
  partners: PartnerProfile[];
  editingPartner?: PartnerProfile | null;
  onClose: () => void;
  onSaved: (saved: PartnerProfile) => void;
  onMutate: () => Promise<unknown>;
};

const blankDraft = (): PartnerInput => ({
  company_name: "",
  contact_name: "",
  email: "",
  phone: "",
  market: "",
  tier: "Standard",
  default_commission_rate: 10.0,
  preferred_currency: "USD",
  notes: "",
});

export function PartnerTierBadge({ tier }: { tier?: string | null }) {
  const t = tier || "Standard";
  const badgeClasses: Record<string, string> = {
    VIP: "bg-amber-50 text-amber-800 border-amber-300",
    Preferred: "bg-purple-50 text-purple-700 border-purple-200",
    "Black Diamond": "bg-neutral-900 text-neutral-100 border-neutral-700",
    Standard: "bg-neutral-100 text-neutral-700 border-neutral-200",
  };

  return (
    <span
      className={cn(
        getTypographyClassName("caption"),
        "inline-flex items-center rounded-full px-2 py-0.5 border",
        badgeClasses[t] || badgeClasses.Standard
      )}
    >
      {t}
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

export function PartnerManageDrawer({
  mode,
  partners,
  editingPartner,
  onClose,
  onSaved,
  onMutate,
}: Props) {
  const [currentMode, setCurrentMode] = useState<PartnerDrawerMode>(mode);
  const [editing, setEditing] = useState<PartnerProfile | null>(editingPartner ?? null);
  const [draft, setDraft] = useState<PartnerInput>(() =>
    editingPartner
      ? {
          company_name: editingPartner.company_name,
          contact_name: editingPartner.contact_name,
          email: editingPartner.email,
          phone: editingPartner.phone || "",
          market: editingPartner.market || "",
          tier: editingPartner.tier || "Standard",
          default_commission_rate: editingPartner.default_commission_rate ?? 10.0,
          preferred_currency: editingPartner.preferred_currency || "USD",
          notes: editingPartner.notes || "",
        }
      : blankDraft()
  );
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  if (!currentMode) return null;

  const setDraftField = <K extends keyof PartnerInput>(key: K, next: PartnerInput[K]) =>
    setDraft((current) => ({ ...current, [key]: next }));

  const openEdit = (partner: PartnerProfile) => {
    setEditing(partner);
    setDraft({
      company_name: partner.company_name,
      contact_name: partner.contact_name,
      email: partner.email,
      phone: partner.phone || "",
      market: partner.market || "",
      tier: partner.tier || "Standard",
      default_commission_rate: partner.default_commission_rate ?? 10.0,
      preferred_currency: partner.preferred_currency || "USD",
      notes: partner.notes || "",
    });
    setCurrentMode("edit");
    setMessage("");
  };

  const savePartner = async () => {
    if (!draft.company_name.trim() || !draft.contact_name.trim() || !draft.email.trim()) {
      setMessage("Company name, contact name, and email are required.");
      return;
    }
    setPending(true);
    try {
      const saved = editing
        ? await updatePartner(editing.id, draft)
        : await createPartner(draft);
      await onMutate();
      onSaved(saved);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Partner could not be saved.");
    } finally {
      setPending(false);
    }
  };

  const toggleStatus = async (partner: PartnerProfile) => {
    setPending(true);
    try {
      await updatePartnerStatus(partner.id, !partner.is_active);
      await onMutate();
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Partner status could not be updated.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={currentMode === "manage" ? "Manage Partners" : "Partner Profile"}
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs"
    >
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
              {currentMode === "manage"
                ? "Manage B2B Partners"
                : editing
                ? "Edit Partner Agency"
                : "Add Partner Agency"}
            </h2>
            <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
              {currentMode === "manage"
                ? "Registered travel agencies, wholesale partners, and trade contacts."
                : "This partner profile can be selected when receiving advisor quote requests."}
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

        {currentMode === "manage" ? (
          <div className="mt-6 flex flex-col gap-3">
            {partners.map((partner) => (
              <article
                key={partner.id}
                className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3 shadow-2xs"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-accent-wash)] text-[var(--color-accent)] shrink-0">
                  <Building2 size={16} aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className={cn(getTypographyClassName("bodyMd"), "truncate text-[var(--color-on-surface)]")}>
                      {partner.company_name}
                    </p>
                    <PartnerTierBadge tier={partner.tier} />
                  </div>
                  <p className={cn(getTypographyClassName("caption"), "truncate text-[var(--color-muted)]")}>
                    {partner.contact_name} • {partner.email} · {partner.is_active ? "Active" : "Inactive"}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => openEdit(partner)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all cursor-pointer"
                  )}
                >
                  Edit
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void toggleStatus(partner)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    partner.is_active
                      ? "min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                      : "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3 shadow-2xs border border-transparent transition-all cursor-pointer"
                  )}
                >
                  {partner.is_active ? "Deactivate" : "Reactivate"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="mt-6 grid gap-4">
            <FormField
              label="Agency / Company Name"
              value={draft.company_name}
              onChange={(next) => setDraftField("company_name", next)}
              disabled={pending}
              required
            />
            <FormField
              label="Primary Contact Person"
              value={draft.contact_name}
              onChange={(next) => setDraftField("contact_name", next)}
              disabled={pending}
              required
            />
            <FormField
              label="Email Address"
              type="email"
              value={draft.email}
              onChange={(next) => setDraftField("email", next)}
              disabled={pending}
              required
            />
            <FormField
              label="Phone Number"
              value={draft.phone || ""}
              onChange={(next) => setDraftField("phone", next)}
              disabled={pending}
            />
            <FormField
              label="Market / Country"
              value={draft.market || ""}
              onChange={(next) => setDraftField("market", next)}
              disabled={pending}
            />

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Partner Tier</span>
                <select
                  value={draft.tier || "Standard"}
                  disabled={pending}
                  onChange={(e) => setDraftField("tier", e.target.value)}
                  className={cn(
                    getTypographyClassName("bodyMd"),
                    "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
                  )}
                >
                  <option value="Standard">Standard</option>
                  <option value="Preferred">Preferred</option>
                  <option value="VIP">VIP</option>
                  <option value="Black Diamond">Black Diamond</option>
                </select>
              </label>

              <FormField
                label="Default Commission (%)"
                type="number"
                value={draft.default_commission_rate ?? 10.0}
                onChange={(next) => setDraftField("default_commission_rate", parseFloat(next) || 0)}
                disabled={pending}
              />
            </div>

            <div className="flex flex-wrap gap-3 mt-2">
              <button
                type="button"
                disabled={pending}
                onClick={() => void savePartner()}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50 cursor-pointer"
                )}
              >
                {pending ? "Saving…" : "Save Partner"}
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
        )}

        {message ? (
          <p aria-live="polite" className={cn(getTypographyClassName("bodySm"), "mt-4 text-[var(--color-muted)]")}>
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}
