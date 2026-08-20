"use client";

import { useMemo } from "react";
import {
  User,
  Calendar,
  Compass,
  DollarSign,
  AlertCircle,
  FileText,
  Globe,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuoteRequestItem } from "./factsTypes.ts";

type Props = {
  request: QuoteRequestItem;
  className?: string;
};

export default function RequestRecapPanel({ request, className }: Props) {
  const payload = useMemo(
    () => ((request.payload_json || {}) as Record<string, unknown>),
    [request.payload_json]
  );
  const isTraveller = request.role === "traveller";
  const clientName = payload.client_name as string | undefined;

  const priorities = useMemo(() => {
    const list: string[] = [];
    if (payload.priority_1) list.push(String(payload.priority_1));
    if (payload.priority_2) list.push(String(payload.priority_2));
    if (payload.priority_3) list.push(String(payload.priority_3));
    return list;
  }, [payload]);

  const constraints = useMemo(() => {
    const list: Array<{ label: string; value: string }> = [];
    if (payload.must_have) list.push({ label: "Must-Have", value: String(payload.must_have) });
    if (payload.avoid) list.push({ label: "Avoid", value: String(payload.avoid) });
    if (payload.dietary) list.push({ label: "Dietary", value: String(payload.dietary) });
    if (payload.halal) list.push({ label: "Halal/Prayer", value: String(payload.halal) });
    if (payload.mobility) list.push({ label: "Mobility", value: String(payload.mobility) });
    if (payload.health_considerations) list.push({ label: "Health", value: String(payload.health_considerations) });
    if (payload.private_vehicle) list.push({ label: "Private Vehicle", value: String(payload.private_vehicle) });
    if (payload.vehicle_preference) list.push({ label: "Vehicle Type", value: String(payload.vehicle_preference) });
    if (payload.guide_scope) list.push({ label: "Guide Scope", value: String(payload.guide_scope) });
    if (payload.hotel_style) list.push({ label: "Hotel Style", value: String(payload.hotel_style) });
    return list;
  }, [payload]);

  return (
    <aside
      className={cn(
        "flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)]",
        className
      )}
    >
      {/* Panel Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-3">
        <div className="flex items-center gap-2">
          <FileText size={18} className="text-[var(--color-accent)]" aria-hidden="true" />
          <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
            Request Context
          </h2>
        </div>
        <div className="flex items-center gap-1.5">
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
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            #{request.id.slice(-6)}
          </span>
        </div>
      </div>

      {/* 1. Client / Advisor Profile */}
      <div className="flex flex-col gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <User size={15} aria-hidden="true" />
          <span className={cn(getTypographyClassName("label"))}>
            {isTraveller ? "Client Details" : "Advisor & End-Client"}
          </span>
        </div>
        <div className="grid gap-1">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
            {!isTraveller && clientName ? (
              <>
                <span>{clientName}</span>
                <span className={cn(getTypographyClassName("caption"), "block text-[var(--color-muted)]")}>
                  via {request.customer_name} ({request.company_name || "Travel Advisor"})
                </span>
              </>
            ) : (
              request.customer_name || "Valued Client"
            )}
          </p>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[var(--color-muted)]">
            {request.market ? (
              <span className={cn(getTypographyClassName("caption"), "flex items-center gap-1")}>
                <Globe size={12} aria-hidden="true" />
                {request.market}
              </span>
            ) : null}
            {request.email ? (
              <span className={cn(getTypographyClassName("caption"))}>{request.email}</span>
            ) : null}
            {request.phone ? (
              <span className={cn(getTypographyClassName("caption"))}>{request.phone}</span>
            ) : null}
          </div>
        </div>
      </div>

      {/* 2. Journey Specs & Composition */}
      <div className="flex flex-col gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <Calendar size={15} aria-hidden="true" />
          <span className={cn(getTypographyClassName("label"))}>Target Dates & Party</span>
        </div>
        <div className="grid gap-1 text-[var(--color-on-surface)]">
          <p className={cn(getTypographyClassName("bodySm"))}>
            {request.start_date && request.end_date
              ? `${request.start_date} ➔ ${request.end_date}`
              : request.raw_dates_text || "Flexible Dates"}
          </p>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Party:{" "}
            <strong className="text-[var(--color-on-surface)]">
              {request.adults || 2} Adults
              {request.children ? `, ${request.children_details || `${request.children} Children`}` : ""}
            </strong>
          </p>
          {request.destinations && request.destinations.length ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {request.destinations.map((dest, i) => (
                <span
                  key={i}
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-md bg-[var(--color-surface)] px-2 py-0.5 border border-[var(--color-border)] text-[var(--color-on-surface)]"
                  )}
                >
                  📍 {dest}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {/* 3. Style, Pacing & Vision */}
      {(request.travel_style || payload.travel_pace || priorities.length > 0) ? (
        <div className="flex flex-col gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
          <div className="flex items-center gap-2 text-[var(--color-muted)]">
            <Compass size={15} aria-hidden="true" />
            <span className={cn(getTypographyClassName("label"))}>Travel Style & Vision</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {request.travel_style ? (
              <span className={cn(getTypographyClassName("caption"), "rounded-md bg-[var(--color-accent-wash)] text-[var(--color-accent)] px-2 py-0.5 border border-transparent")}>
                ✨ {request.travel_style}
              </span>
            ) : null}
            {payload.travel_pace ? (
              <span className={cn(getTypographyClassName("caption"), "rounded-md bg-[var(--color-surface)] text-[var(--color-muted)] px-2 py-0.5 border border-[var(--color-border)]")}>
                Pacing: {String(payload.travel_pace)}
              </span>
            ) : null}
            {priorities.map((p, idx) => (
              <span
                key={idx}
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-md bg-[var(--color-surface)] px-2 py-0.5 border border-[var(--color-border)] text-[var(--color-on-surface)]"
                )}
              >
                🎯 {p}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {/* 4. Commercial & Budget Expectations */}
      {(payload.budget || payload.currency) ? (
        <div className="flex flex-col gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
          <div className="flex items-center gap-2 text-[var(--color-muted)]">
            <DollarSign size={15} aria-hidden="true" />
            <span className={cn(getTypographyClassName("label"))}>Budget Signal</span>
          </div>
          <p className={cn(getTypographyClassName("bodySm"), "text-emerald-700")}>
            {payload.budget ? `${Number(payload.budget).toLocaleString()} ${payload.currency || "USD"}` : "Not specified"}{" "}
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              ({String(payload.budget_basis || "Total trip")})
            </span>
          </p>
        </div>
      ) : null}

      {/* 5. Key Constraints & Requirements */}
      {constraints.length > 0 ? (
        <div className="flex flex-col gap-2 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
          <div className="flex items-center gap-2 text-[var(--color-muted)]">
            <AlertCircle size={15} aria-hidden="true" />
            <span className={cn(getTypographyClassName("label"))}>Notes & Constraints</span>
          </div>
          <ul className="flex flex-col gap-1 text-[var(--color-on-surface)]">
            {constraints.map((c, i) => (
              <li key={i} className={cn(getTypographyClassName("caption"), "flex items-start gap-1.5")}>
                <strong className="text-[var(--color-muted)] shrink-0">{c.label}:</strong>
                <span className="text-[var(--color-on-surface)]">{c.value}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* 6. Raw Message / Internal Notes */}
      {(payload.message || payload.internal_notes || request.special_requirements) ? (
        <div className="flex flex-col gap-1.5 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-3 border border-[var(--color-border)]">
          <span className={cn(getTypographyClassName("overline"), "text-[var(--color-muted)]")}>
            Raw Notes / Message
          </span>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-on-surface)] whitespace-pre-line")}>
            {String(payload.message || payload.internal_notes || request.special_requirements)}
          </p>
        </div>
      ) : null}
    </aside>
  );
}
