"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { ShieldCheck, UserCheck, Calendar, Clock, Flag } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import DetailField from "./DetailField";
import { listTravelDesigners, type TravelDesignerProfile } from "../../../lib/quotationApi";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  brandId?: string | null;
  travelDesignerId?: string | null;
  priority?: string | null;
  leadSource?: string | null;
  quoteDeadline?: string | null;
  decisionDate?: string | null;
  status?: string | null;
  createdAt?: string;
};

const BRANDS_MAP: Record<string, string> = {
  selvara: "Selvara Journeys",
  capella_travel: "Capella Travel",
  vietnam_safar: "Vietnam Safar",
};

export default function LeadManagementCard({
  brandId = "selvara",
  travelDesignerId,
  priority = "normal",
  leadSource,
  quoteDeadline,
  decisionDate,
  status = "new",
}: Props) {
  const { data: designerData } = useSWR("travel-designers-active", () =>
    listTravelDesigners({ active: "all" })
  );

  const assignedDesigner = useMemo(() => {
    if (!travelDesignerId || !designerData?.items) return null;
    return designerData.items.find((d: TravelDesignerProfile) => d.id === travelDesignerId) || null;
  }, [travelDesignerId, designerData]);

  const brandName = (brandId && BRANDS_MAP[brandId]) || brandId || "Selvara Journeys";

  const priorityVariant =
    priority === "hot" ? "danger" : priority === "warm" ? "warning" : "default";

  return (
    <DetailSectionCard
      title="Lead & Ownership Management"
      subtitle="Brand allocation, designer assignment, and quotation urgency"
      icon={<ShieldCheck size={18} aria-hidden="true" />}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Brand Identity"
          value={brandName}
          badge
          badgeVariant="accent"
        />

        <DetailField
          label="Lead Priority"
          value={priority ? priority.toUpperCase() : "NORMAL"}
          icon={<Flag size={13} aria-hidden="true" />}
          badge
          badgeVariant={priorityVariant}
        />

        <DetailField
          label="Lead Source"
          value={leadSource || "Website"}
        />

        <DetailField
          label="Request Status"
          value={(status || "new").replace("_", " ").toUpperCase()}
          badge
          badgeVariant={status === "quotation_created" ? "success" : "default"}
        />

        <DetailField
          label="Quote Deadline"
          icon={<Clock size={13} aria-hidden="true" />}
          value={quoteDeadline}
          emptyFallback="Not specified"
        />

        <DetailField
          label="Client Decision Date"
          icon={<Calendar size={13} aria-hidden="true" />}
          value={decisionDate}
          emptyFallback="Not specified"
        />
      </div>

      {/* Travel Designer Assignment Module */}
      <div className="mt-1 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
        <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-2")}>
          <UserCheck size={14} className="text-[var(--color-accent)]" aria-hidden="true" />
          <span>Assigned Travel Designer</span>
        </span>

        {assignedDesigner ? (
          <div className="flex items-center gap-3">
            <div className={cn(getTypographyClassName("cardTitle"), "flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)] text-white")}>
              {assignedDesigner.name ? assignedDesigner.name.charAt(0).toUpperCase() : "D"}
            </div>
            <div className="min-w-0 flex-1">
              <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)] truncate")}>
                {assignedDesigner.name}
              </p>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] truncate")}>
                {assignedDesigner.email} {assignedDesigner.phone ? `• ${assignedDesigner.phone}` : ""}
              </p>
            </div>
          </div>
        ) : (
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
            {travelDesignerId ? `Designer ID: ${travelDesignerId}` : "Unassigned (Default Team Pool)"}
          </p>
        )}
      </div>
    </DetailSectionCard>
  );
}
