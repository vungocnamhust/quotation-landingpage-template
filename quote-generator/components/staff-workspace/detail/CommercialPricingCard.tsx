"use client";

import { CircleDollarSign, Percent, ShieldCheck, FileText } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import DetailField from "./DetailField";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  isB2B?: boolean;
  budget?: number | null;
  budgetBasis?: string | null;
  currency?: string | null;
  pricingType?: string | null;
  commission?: number | null;
  showCommission?: string | null;
  priceDisplay?: string | null;
  targetGp?: number | null;
  minimumGp?: number | null;
  contingency?: number | null;
  paymentFee?: number | null;
  taxTreatment?: string | null;
  discountCap?: string | null;
  quoteValidity?: string | null;
  paymentTerms?: string | null;
};

export default function CommercialPricingCard({
  isB2B = false,
  budget,
  budgetBasis,
  currency = "USD",
  pricingType,
  commission,
  showCommission,
  priceDisplay,
  targetGp,
  minimumGp,
  contingency,
  paymentFee,
  taxTreatment,
  discountCap,
  quoteValidity,
  paymentTerms,
}: Props) {
  return (
    <DetailSectionCard
      title="Commercial & Pricing Parameters"
      subtitle="Client budget targets, pricing structure, profit margins & payment conditions"
      icon={<CircleDollarSign size={18} aria-hidden="true" />}
      headerBadge={
        budget ? (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "rounded-full bg-[var(--color-accent-wash)] px-2.5 py-0.5 border border-[var(--color-accent)] text-[var(--color-accent)]"
            )}
          >
            {currency} {budget.toLocaleString()}
          </span>
        ) : null
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <DetailField
          label="Budget Target"
          value={budget ? `${currency} ${budget.toLocaleString()}` : undefined}
          emptyFallback="Open / Not specified"
          badge={Boolean(budget)}
          badgeVariant="accent"
        />

        <DetailField
          label="Budget Basis"
          value={budgetBasis || "Total trip"}
        />

        <DetailField
          label="Quotation Currency"
          value={currency || "USD"}
          badge
        />

        <DetailField
          label="Pricing Structure"
          value={pricingType || "Gross (Direct selling)"}
        />

        <DetailField
          label="Price Display Style"
          value={priceDisplay || "Total journey price"}
          badge
          badgeVariant="default"
        />

        {isB2B ? (
          <>
            <DetailField
              label="Advisor Commission %"
              value={commission ? `${commission}%` : undefined}
              icon={<Percent size={13} aria-hidden="true" />}
              emptyFallback="0% (Net)"
              badge={Boolean(commission)}
              badgeVariant="success"
            />

            <DetailField
              label="Show Commission to Client"
              value={showCommission || "No"}
              badge={showCommission !== "No"}
              badgeVariant={showCommission !== "No" ? "warning" : "default"}
            />
          </>
        ) : null}

        <DetailField
          label="Target Gross Profit (GP)"
          value={targetGp ? `${targetGp}%` : undefined}
          emptyFallback="25.0% (Default)"
        />

        <DetailField
          label="Minimum Floor GP"
          value={minimumGp ? `${minimumGp}%` : undefined}
          emptyFallback="18.0%"
        />

        <DetailField
          label="Contingency Buffer"
          value={contingency ? `${contingency}%` : undefined}
          emptyFallback="3.0%"
        />

        <DetailField
          label="Payment Processing Fee"
          value={paymentFee ? `${paymentFee}%` : undefined}
          emptyFallback="Included / 0%"
        />

        <DetailField
          label="Tax / VAT Treatment"
          value={taxTreatment || "Inclusive / Destination tax compliant"}
          icon={<ShieldCheck size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Max Discount Authority"
          value={discountCap}
          emptyFallback="Standard manager approval"
        />

        <DetailField
          label="Quotation Validity"
          value={quoteValidity || "14 days / Subject to live room availability"}
        />
      </div>

      {paymentTerms ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-1.5")}>
            <FileText size={13} aria-hidden="true" />
            <span>Payment & Cancellation Conditions to Quote</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] whitespace-pre-wrap")}>
            {paymentTerms}
          </p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
