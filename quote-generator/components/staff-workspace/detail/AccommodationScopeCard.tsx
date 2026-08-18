"use client";

import { Building2, BedDouble, Layers } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard";
import DetailField from "./DetailField";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

type Props = {
  hotelLevel?: string | null;
  preferredHotel?: string | null;
  roomType?: string | null;
  bedding?: string | null;
  connecting?: string | null;
  suiteInterest?: string | null;
  hotelStyle?: string | null;
};

export default function AccommodationScopeCard({
  hotelLevel,
  preferredHotel,
  roomType,
  bedding,
  connecting,
  suiteInterest,
  hotelStyle,
}: Props) {
  const hasData = Boolean(
    hotelLevel || preferredHotel || roomType || bedding || connecting || suiteInterest || hotelStyle
  );

  return (
    <DetailSectionCard
      title="Accommodation Scope"
      subtitle="Hotel tiers, preferred properties, room specifications & bedding"
      icon={<Building2 size={18} aria-hidden="true" />}
      headerBadge={
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          {hasData ? "Specified" : "Standard Default"}
        </span>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Hotel Category / Level"
          value={hotelLevel || "5-Star Classic Luxury (Default)"}
          badge
          badgeVariant="accent"
        />

        <DetailField
          label="Hotel Architectural Style"
          value={hotelStyle || "Heritage & boutique luxury"}
          icon={<Layers size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Preferred Hotel / Resort Brands"
          value={preferredHotel}
          emptyFallback="Open to designer recommendations"
        />

        <DetailField
          label="Room Category Preference"
          value={roomType || "Standard / Lead-in luxury"}
          icon={<BedDouble size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Bedding Configuration"
          value={bedding || "King / Double"}
        />

        <DetailField
          label="Connecting Rooms Required?"
          value={connecting || "No"}
          badge={connecting === "Yes"}
          badgeVariant={connecting === "Yes" ? "warning" : "default"}
        />
      </div>

      {suiteInterest ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] block mb-1")}>
            Suite / Villa Upgrades & View Preferences
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{suiteInterest}</p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
