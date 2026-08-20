"use client";

import { Car, Compass, Plane, UtensilsCrossed, ShieldAlert, Sparkles, Shield } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard.tsx";
import DetailField from "./DetailField.tsx";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

type Props = {
  privateVehicle?: string | null;
  vehiclePreference?: string | null;
  guideLanguage?: string | null;
  guideScope?: string | null;
  domesticFlights?: string | null;
  intlFlights?: string | null;
  railCruise?: string | null;
  transportClass?: string | null;
  mealPlan?: string | null;
  diningLevel?: string | null;
  experiencesIncluded?: string | null;
  optionalActivities?: string | null;
  visaFasttrack?: string | null;
  meetAssist?: string | null;
  insurance?: string | null;
  otherServices?: string | null;
};

export default function ServiceScopeCard({
  privateVehicle = "Yes",
  vehiclePreference,
  guideLanguage = "English",
  guideScope = "Full-trip guide",
  domesticFlights = "Yes",
  intlFlights = "No",
  railCruise,
  transportClass,
  mealPlan = "Breakfast only",
  diningLevel,
  experiencesIncluded = "All planned experiences",
  optionalActivities,
  visaFasttrack = "No",
  meetAssist = "No",
  insurance = "No",
  otherServices,
}: Props) {
  return (
    <DetailSectionCard
      title="Service Scope & Logistical Inclusions"
      subtitle="Vehicles, guides, flights, cruise, culinary level & VIP airport services"
      icon={<Car size={18} aria-hidden="true" />}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Private Vehicle & Driver"
          value={privateVehicle === "Yes" ? `Yes (${vehiclePreference || "Private luxury vehicle"})` : privateVehicle || "Yes"}
          icon={<Car size={13} aria-hidden="true" />}
          badge
          badgeVariant="accent"
        />

        <DetailField
          label="Guide Coverage & Language"
          value={`${guideScope || "Full-trip guide"} (${guideLanguage || "English"})`}
          icon={<Compass size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Domestic Flight Booking"
          value={domesticFlights || "Yes (Included in quote)"}
          icon={<Plane size={13} aria-hidden="true" />}
        />

        <DetailField
          label="International Flights"
          value={intlFlights || "No (Booked by client/advisor)"}
        />

        <DetailField
          label="Flight / Transport Class"
          value={transportClass || "Economy / Business as requested"}
        />

        <DetailField
          label="Scenic Rail & Private Cruises"
          value={railCruise}
          emptyFallback="Standard itinerary routing"
        />

        <DetailField
          label="Meal Plan & Inclusions"
          value={mealPlan || "Breakfast daily"}
          icon={<UtensilsCrossed size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Dining Level & Reservations"
          value={diningLevel || "Curated authentic & premium local"}
        />

        <DetailField
          label="Planned Experiences Inclusion"
          value={experiencesIncluded || "All planned experiences included"}
          badge
          badgeVariant="success"
        />

        <DetailField
          label="VIP Fast-Track Immigration"
          value={visaFasttrack || "No"}
          icon={<ShieldAlert size={13} aria-hidden="true" />}
          badge={visaFasttrack === "Yes"}
          badgeVariant={visaFasttrack === "Yes" ? "warning" : "default"}
        />

        <DetailField
          label="Airport Meet & Assist"
          value={meetAssist || "No"}
          badge={meetAssist === "Yes"}
          badgeVariant={meetAssist === "Yes" ? "warning" : "default"}
        />

        <DetailField
          label="Travel Insurance Assistance"
          value={insurance || "No"}
          icon={<Shield size={13} aria-hidden="true" />}
        />
      </div>

      {optionalActivities ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5 mb-1")}>
            <Sparkles size={13} aria-hidden="true" />
            <span>Optional Activities & Special Requests</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{optionalActivities}</p>
        </div>
      ) : null}

      {otherServices ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] block mb-1")}>
            Additional Ancillary Services
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{otherServices}</p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
