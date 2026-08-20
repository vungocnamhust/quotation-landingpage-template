"use client";

import { MapPin, Calendar, Users, BedDouble, AlertCircle, Plane, ArrowRight } from "lucide-react";
import DetailSectionCard from "./DetailSectionCard.tsx";
import DetailField from "./DetailField.tsx";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { formatRouteString } from "../../../lib/rules/routeRules.ts";

type Props = {
  destinations?: string[];
  startDate?: string | null;
  endDate?: string | null;
  rawDatesText?: string | null;
  travelTiming?: string | null;
  arrivalCity?: string | null;
  departureCity?: string | null;
  adults?: number | null;
  childrenCount?: number | null;
  kidAges?: number[];
  infants?: number | null;
  roomConfiguration?: string | null;
  routingConstraints?: string | null;
};

export default function JourneyRoutingCard({
  destinations = [],
  startDate,
  endDate,
  rawDatesText,
  travelTiming,
  arrivalCity,
  departureCity,
  adults = 2,
  childrenCount = 0,
  kidAges = [],
  infants = 0,
  roomConfiguration,
  routingConstraints,
}: Props) {
  const datesText =
    rawDatesText ||
    (startDate ? `${startDate} ${endDate ? `→ ${endDate}` : ""}` : "Dates flexible / undecided");

  const destinationsText = formatRouteString(destinations) || "Not specified";

  return (
    <DetailSectionCard
      title="Journey Essentials & Routing"
      subtitle="Destination route, travel dates, party headcount & room setups"
      icon={<MapPin size={18} aria-hidden="true" />}
    >
      {/* Visual Connected Route Chain */}
      {destinations.length > 0 ? (
        <div className="flex flex-col gap-1.5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Planned Route Sequence:
          </span>
          <div className="flex flex-wrap items-center gap-2">
            {destinations.map((dest, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 shadow-2xs",
                    idx === 0
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                      : idx === destinations.length - 1
                        ? "border-amber-300 bg-amber-50 text-amber-900"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)]"
                  )}
                >
                  <span className={cn(getTypographyClassName("overline"), "opacity-70")}>{idx + 1}.</span>
                  <span>{dest}</span>
                </span>
                {idx < destinations.length - 1 ? (
                  <ArrowRight size={13} className="text-[var(--color-accent)] opacity-80" aria-hidden="true" />
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <DetailField
          label="Destinations"
          value={destinationsText}
          badge
          badgeVariant="accent"
        />

        <DetailField
          label="Timing Flexibility"
          value={travelTiming || "Exact dates"}
          badge
          badgeVariant="default"
        />

        <DetailField
          label="Travel Dates / Schedule"
          value={datesText}
          icon={<Calendar size={13} aria-hidden="true" />}
        />

        <DetailField
          label="Gateway Cities (In / Out)"
          value={
            arrivalCity || departureCity
              ? `In: ${arrivalCity || "TBD"} • Out: ${departureCity || "TBD"}`
              : "Not specified"
          }
          icon={<Plane size={13} aria-hidden="true" />}
        />
      </div>

      {/* Guest Party Composition Box */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3.5">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)] flex items-center gap-1.5")}>
            <Users size={14} className="text-[var(--color-accent)]" aria-hidden="true" />
            <span>Party Headcount</span>
          </span>

          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Total: {(adults || 2) + (childrenCount || 0) + (infants || 0)} Guests
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
            {adults || 2} Adults
          </span>

          {childrenCount && childrenCount > 0 ? (
            <div className="flex items-center gap-1.5">
              <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
                • {childrenCount} Children
              </span>
              {kidAges.length > 0 ? (
                <div className="flex items-center gap-1">
                  {kidAges.map((age, i) => (
                    <span
                      key={i}
                      className={cn(
                        getTypographyClassName("caption"),
                        "rounded bg-[var(--color-surface)] border border-[var(--color-border)] px-1.5 py-0.5 text-[var(--color-muted)]"
                      )}
                    >
                      {age}y
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {infants && infants > 0 ? (
            <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
              • {infants} Infants (&lt;2y)
            </span>
          ) : null}
        </div>
      </div>

      {/* Room Configuration */}
      <div className="grid gap-3 sm:grid-cols-1">
        <DetailField
          label="Room Configuration"
          value={roomConfiguration || "1 King / Double Room (Standard)"}
          icon={<BedDouble size={14} aria-hidden="true" />}
          badge={Boolean(roomConfiguration)}
          badgeVariant="default"
        />
      </div>

      {/* Routing Constraints / Fixed Flights & Dates */}
      {routingConstraints ? (
        <div className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50/60 p-3.5">
          <span className={cn(getTypographyClassName("label"), "text-amber-900 flex items-center gap-1.5 mb-1")}>
            <AlertCircle size={14} className="text-amber-700" aria-hidden="true" />
            <span>Routing Constraints & Fixed Flights/Dates</span>
          </span>
          <p className={cn(getTypographyClassName("bodySm"), "text-amber-950 whitespace-pre-wrap")}>
            {routingConstraints}
          </p>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}
