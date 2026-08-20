"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { User, Briefcase, Mail, Phone, Globe, MessageSquare, Building2, Sparkles } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard.tsx";
import DetailField from "./DetailField.tsx";
import { listPartners, type PartnerProfile } from "../../../lib/quotationApi.ts";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

type Props = {
  role: "traveller" | "advisor";
  customerName?: string | null;
  clientName?: string | null;
  email?: string | null;
  phone?: string | null;
  companyName?: string | null;
  market?: string | null;
  preferredContact?: string | null;
  clientContext?: string | null;
  partnerId?: string | null;
};

export default function ClientIdentityCard({
  role,
  customerName,
  clientName,
  email,
  phone,
  companyName,
  market,
  preferredContact = "Email",
  clientContext,
  partnerId,
}: Props) {
  const isTraveller = role === "traveller";

  const { data: partnersData } = useSWR(
    !isTraveller && partnerId ? "partners-all" : null,
    () => listPartners({ active: "all" })
  );

  const linkedPartner = useMemo(() => {
    if (!partnerId || !partnersData?.items) return null;
    return partnersData.items.find((p: PartnerProfile) => p.id === partnerId) || null;
  }, [partnerId, partnersData]);

  return (
    <DetailSectionCard
      title={isTraveller ? "Traveller Profile & Contacts" : "B2B Partner & Travel Advisor"}
      subtitle={
        isTraveller
          ? "Direct B2C traveller contact information & personal context"
          : "Trade partner agency, advisor contact & end-client guest"
      }
      icon={
        isTraveller ? (
          <User size={18} aria-hidden="true" />
        ) : (
          <Briefcase size={18} aria-hidden="true" />
        )
      }
      headerBadge={
        <span
          className={cn(
            getTypographyClassName("caption"),
            "rounded-full px-2.5 py-0.5 border",
            isTraveller
              ? "bg-sky-50 text-sky-700 border-sky-200"
              : "bg-purple-50 text-purple-700 border-purple-200"
          )}
        >
          {isTraveller ? "B2C TRAVELLER" : "B2B ADVISOR"}
        </span>
      }
    >
      {!isTraveller ? (
        /* End-Client Guest Profile Card for B2B */
        <div className="rounded-[var(--radius-card)] border border-[var(--color-accent)] bg-[var(--color-accent-wash)] p-4">
          <div className="flex items-center gap-2 mb-1 text-[var(--color-accent)]">
            <Sparkles size={16} aria-hidden="true" />
            <span className={cn(getTypographyClassName("label"))}>
              End-Client / Lead Guest Name
            </span>
          </div>
          <p className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            {clientName || "Valued Private Guests (Client name unassigned)"}
          </p>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] mt-0.5")}>
            Generated quotation will be addressed to this traveller while linking the advisor below.
          </p>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label={isTraveller ? "Full Name" : "Advisor Contact Person"}
          value={customerName}
          copyable
          emptyFallback="Not specified"
        />

        {!isTraveller ? (
          <DetailField
            label="Agency / Luxury Company"
            value={companyName}
            icon={<Building2 size={13} aria-hidden="true" />}
            badge
            badgeVariant="accent"
            emptyFallback="Independent / Unspecified"
          />
        ) : null}

        <DetailField
          label="Email Address"
          value={email}
          href={email ? `mailto:${email}` : undefined}
          icon={<Mail size={13} aria-hidden="true" />}
          copyable
          emptyFallback="Not specified"
        />

        <DetailField
          label="Phone / WhatsApp"
          value={phone}
          href={phone ? `tel:${phone}` : undefined}
          icon={<Phone size={13} aria-hidden="true" />}
          copyable
          emptyFallback="Not specified"
        />

        <DetailField
          label={isTraveller ? "Country of Residence" : "Advisor Market / Region"}
          value={market}
          icon={<Globe size={13} aria-hidden="true" />}
          emptyFallback="Not specified"
        />

        {isTraveller ? (
          <DetailField
            label="Preferred Contact Channel"
            value={preferredContact || "Email"}
            badge
          />
        ) : null}

        {!isTraveller && linkedPartner ? (
          <DetailField
            label="Partner Tier & Agreement"
            value={`${linkedPartner.tier || "Standard"} • Comm: ${linkedPartner.default_commission_rate}% (${linkedPartner.preferred_currency})`}
            badge
            badgeVariant="success"
          />
        ) : null}
      </div>

      {/* Client Context & Relationship History */}
      {clientContext ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-1.5")}>
            <MessageSquare size={13} aria-hidden="true" />
            <span>Relationship History & Client Context</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)] whitespace-pre-wrap")}>
            {clientContext}
          </p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
