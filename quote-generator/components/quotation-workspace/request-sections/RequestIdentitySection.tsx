"use client";

import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import CustomSelect from "../../ui/CustomSelect";
import { TravelDesignerSelect } from "../../travel-designer/TravelDesignerSelect";
import { PartnerSelect } from "../../partner/PartnerSelect";
import QuoteRequestRoleSelector from "../QuoteRequestRoleSelector";
import type { QuoteRequestFormState } from "../../../lib/quoteRequestPayload";

type Props = {
  state: QuoteRequestFormState;
  onChange: (updater: (prev: QuoteRequestFormState) => QuoteRequestFormState) => void;
  disabled?: boolean;
};

const BRANDS = [
  { id: "selvara", label: "Selvara Journeys" },
  { id: "capella_travel", label: "Capella Travel" },
  { id: "vietnam_safar", label: "Vietnam Safar" },
];

const PRIORITIES = [
  { id: "normal", label: "Normal" },
  { id: "warm", label: "Warm" },
  { id: "hot", label: "Hot" },
];

const LEAD_SOURCES = [
  "Website",
  "Partner Referral",
  "Repeat Guest",
  "Direct Call",
  "Email Enquiry",
  "Trade Show",
  "Other",
];

const CONTACT_METHODS = ["Email", "WhatsApp", "Phone Call", "Any"];

const MARKETS = [
  "North America (US/CA)",
  "United Kingdom (UK)",
  "Western Europe",
  "Australia / NZ",
  "GCC / Middle East",
  "Southeast Asia",
  "India",
  "Domestic Vietnam",
  "Other",
];

function Field({
  label,
  value,
  type = "text",
  placeholder,
  required = false,
  disabled = false,
  min,
  onChange,
}: {
  label: string;
  value: string | number;
  type?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  min?: number;
  onChange: (val: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
        {label}
        {required ? <span className="text-[var(--color-accent)] ml-0.5">*</span> : null}
      </span>
      <input
        type={type}
        disabled={disabled}
        required={required}
        placeholder={placeholder}
        min={min}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          getTypographyClassName("bodyMd"),
          "min-h-11 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
        )}
      />
    </label>
  );
}

export function RequestIdentitySection({ state, onChange, disabled = false }: Props) {
  const isTraveller = state.role === "traveller";

  return (
    <>
      {/* 1. Internal & Lead Management Card */}
      <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        <div className="flex flex-col gap-1">
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Internal & Lead Management
          </h2>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
            Assign brand identity, designer ownership and set quotation urgency.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Brand <span className="text-[var(--color-accent)]">*</span>
            </span>
            <CustomSelect
              options={BRANDS}
              value={state.brand_id}
              onChange={(val) => onChange((prev) => ({ ...prev, brand_id: val }))}
              placeholder="Select brand"
            />
          </label>

          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Lead Priority
            </span>
            <CustomSelect
              options={PRIORITIES}
              value={state.priority}
              onChange={(val) =>
                onChange((prev) => ({ ...prev, priority: val as "normal" | "warm" | "hot" }))
              }
              placeholder="Priority"
            />
          </label>

          <Field
            label="Quote Deadline"
            type="date"
            disabled={disabled}
            value={state.quote_deadline}
            onChange={(val) => onChange((prev) => ({ ...prev, quote_deadline: val }))}
          />

          <Field
            label="Client Decision Date"
            type="date"
            disabled={disabled}
            value={state.decision_date}
            onChange={(val) => onChange((prev) => ({ ...prev, decision_date: val }))}
          />

          <label className="flex flex-col gap-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
              Lead Source
            </span>
            <CustomSelect
              options={LEAD_SOURCES.map((s) => ({ id: s, label: s }))}
              value={state.lead_source}
              onChange={(val) => onChange((prev) => ({ ...prev, lead_source: val }))}
              placeholder="Select source"
            />
          </label>
        </div>


        {/* Travel Designer Ownership Selector */}
        <div className="border-t border-[var(--color-border)] pt-4">
          <TravelDesignerSelect
            label="Travel Designer Ownership"
            value={state.travel_designer_id}
            brandId={state.brand_id}
            disabled={disabled}
            onChange={(profileId) =>
              onChange((prev) => ({ ...prev, travel_designer_id: profileId }))
            }
          />
        </div>
      </section>

      {/* 2. Persona & Contacts Card */}
      <section className="flex flex-col gap-6 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-6">
        {/* Persona Selector Tabs */}
        <QuoteRequestRoleSelector
          value={state.role}
          onChange={(role) => onChange((prev) => ({ ...prev, role }))}
        />

        {/* Honeypot field (hidden from human users) */}
        <div className="hidden" aria-hidden="true">
          <label htmlFor="contact-website">Website</label>
          <input
            id="contact-website"
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={state.website}
            onChange={(e) => onChange((prev) => ({ ...prev, website: e.target.value }))}
          />
        </div>

        <hr className="border-[var(--color-border)]" />

        {isTraveller ? (
          /* Traveller Persona Inputs */
          <div className="flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field
                label="First name"
                required
                disabled={disabled}
                value={state.first_name}
                onChange={(val) => onChange((prev) => ({ ...prev, first_name: val }))}
              />
              <Field
                label="Last name"
                required
                disabled={disabled}
                value={state.last_name}
                onChange={(val) => onChange((prev) => ({ ...prev, last_name: val }))}
              />
              <Field
                label="Email"
                type="email"
                required
                disabled={disabled}
                value={state.email}
                onChange={(val) => onChange((prev) => ({ ...prev, email: val }))}
              />
              <Field
                label="Phone / WhatsApp"
                type="tel"
                disabled={disabled}
                value={state.phone}
                onChange={(val) => onChange((prev) => ({ ...prev, phone: val }))}
              />
              <Field
                label="Country of residence"
                disabled={disabled}
                value={state.country}
                onChange={(val) => onChange((prev) => ({ ...prev, country: val }))}
              />
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Preferred contact
                </span>
                <CustomSelect
                  options={CONTACT_METHODS.map((m) => ({ id: m, label: m }))}
                  value={state.preferred_contact}
                  onChange={(val) => onChange((prev) => ({ ...prev, preferred_contact: val }))}
                  placeholder="Select contact method"
                />
              </label>
            </div>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Client Context & Relationship History
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Referral source, previous journeys with us, specific celebrations or client background..."
                value={state.client_context}
                onChange={(e) => onChange((prev) => ({ ...prev, client_context: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>
          </div>
        ) : (
          /* Advisor Persona Inputs */
          <div className="flex flex-col gap-5">
            {/* Partner / Luxury Agency Selector */}
            <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
              <PartnerSelect
                label="Linked Partner Agency"
                value={state.partner_id}
                disabled={disabled}
                onChange={(partnerId, partner) => {
                  onChange((prev) => {
                    if (!partner) {
                      return { ...prev, partner_id: partnerId };
                    }
                    const nameParts = (partner.contact_name || "").trim().split(/\s+/);
                    const firstName = nameParts[0] || "";
                    const lastName = nameParts.slice(1).join(" ") || "";
                    return {
                      ...prev,
                      partner_id: partnerId,
                      advisor_company: partner.company_name,
                      advisor_first_name: firstName,
                      advisor_last_name: lastName,
                      advisor_email: partner.email,
                      advisor_phone: partner.phone || "",
                      advisor_market: partner.market || prev.advisor_market,
                      commission: partner.default_commission_rate,
                      currency: partner.preferred_currency || prev.currency,
                    };
                  });
                }}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field
                label="Client / Lead Guest Name"
                placeholder="e.g. The Vance Family / Mr. John Doe"
                disabled={disabled}
                value={state.client_name}
                onChange={(val) => onChange((prev) => ({ ...prev, client_name: val }))}
              />
              <Field
                label="Agency / Company"
                required
                disabled={disabled}
                value={state.advisor_company}
                onChange={(val) => onChange((prev) => ({ ...prev, advisor_company: val }))}
              />
              <Field
                label="Advisor First name"
                required
                disabled={disabled}
                value={state.advisor_first_name}
                onChange={(val) => onChange((prev) => ({ ...prev, advisor_first_name: val }))}
              />
              <Field
                label="Advisor Last name"
                required
                disabled={disabled}
                value={state.advisor_last_name}
                onChange={(val) => onChange((prev) => ({ ...prev, advisor_last_name: val }))}
              />
              <Field
                label="Advisor Email"
                type="email"
                required
                disabled={disabled}
                value={state.advisor_email}
                onChange={(val) => onChange((prev) => ({ ...prev, advisor_email: val }))}
              />
              <Field
                label="Advisor Phone / WhatsApp"
                type="tel"
                disabled={disabled}
                value={state.advisor_phone}
                onChange={(val) => onChange((prev) => ({ ...prev, advisor_phone: val }))}
              />
              <label className="flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                  Advisor Market
                </span>
                <CustomSelect
                  options={MARKETS.map((m) => ({ id: m, label: m }))}
                  value={state.advisor_market}
                  onChange={(val) => onChange((prev) => ({ ...prev, advisor_market: val }))}
                  placeholder="Select market"
                />
              </label>
            </div>

            <label className="flex flex-col gap-2">
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Client Context & Relationship History
              </span>
              <textarea
                rows={2}
                disabled={disabled}
                placeholder="Referral source, previous bookings, advisor expectations, relationship history, decision-maker notes..."
                value={state.client_context}
                onChange={(e) => onChange((prev) => ({ ...prev, client_context: e.target.value }))}
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
                )}
              />
            </label>
          </div>
        )}
      </section>
    </>
  );
}
