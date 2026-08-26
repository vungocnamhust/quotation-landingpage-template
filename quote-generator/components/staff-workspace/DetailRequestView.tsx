"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  Sparkles,
  ExternalLink,
  Edit3,
  History,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { useToast } from "./ToastProvider.tsx";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";

import LeadManagementCard from "./detail/LeadManagementCard.tsx";
import ClientIdentityCard from "./detail/ClientIdentityCard.tsx";
import JourneyRoutingCard from "./detail/JourneyRoutingCard.tsx";
import TravelStyleCard from "./detail/TravelStyleCard.tsx";
import AccommodationScopeCard from "./detail/AccommodationScopeCard.tsx";
import ServiceScopeCard from "./detail/ServiceScopeCard.tsx";
import SpecialRequirementsCard from "./detail/SpecialRequirementsCard.tsx";
import CommercialPricingCard from "./detail/CommercialPricingCard.tsx";
import ReadinessStrategyCard from "./detail/ReadinessStrategyCard.tsx";
import DailyItineraryTimeline from "./detail/DailyItineraryTimeline.tsx";
import { useWorkspaceNavigation, WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";

// Dynamic import modals to optimize initial bundle size (Vercel Best Practice: bundle-dynamic-imports)
const EditRequestDrawer = dynamic(() => import("./EditRequestDrawer"), { ssr: false });
const RequestRevisionHistoryModal = dynamic(() => import("./RequestRevisionHistoryModal"), { ssr: false });

type Props = {
  request: QuoteRequestItem;
};

export default function DetailRequestView({ request: initialRequest }: Props) {
  const { push } = useWorkspaceNavigation();
  const { toast } = useToast();
  const [currentLatestRequest, setCurrentLatestRequest] = useState<QuoteRequestItem>(initialRequest);
  const [activeRequest, setActiveRequest] = useState<QuoteRequestItem>(initialRequest);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const isInspectingPastRevision =
    activeRequest.current_revision !== undefined &&
    currentLatestRequest.current_revision !== undefined &&
    activeRequest.current_revision < currentLatestRequest.current_revision;

  const payload = (
    typeof activeRequest.payload_json === "string"
      ? (() => {
          try {
            return JSON.parse(activeRequest.payload_json) as Record<string, unknown>;
          } catch {
            return {};
          }
        })()
      : (activeRequest.payload_json || {})
  ) as Record<string, unknown>;
  const isTraveller = activeRequest.role === "traveller";
  const clientName = payload.client_name as string | undefined;
  const rawTitle = activeRequest.customer_name || (isTraveller ? "Valued Client" : "Travel Advisor");
  const displayHeading = !isTraveller && clientName ? `Journey for ${clientName}` : rawTitle;

  const rawItinerary = payload.itinerary_days;
  const itineraryDays: Array<Record<string, unknown>> = Array.isArray(rawItinerary)
    ? (rawItinerary as Array<Record<string, unknown>>)
    : [];

  const handleGenerateQuotation = () => {
    toast(`Initializing quotation draft from request #${activeRequest.id}...`, "info");
    push(`/workspace/quotations/new?requestId=${activeRequest.id}`);
  };

  const handleEditSuccess = (updated: QuoteRequestItem) => {
    setCurrentLatestRequest(updated);
    setActiveRequest(updated);
    toast(`Revision #${updated.current_revision || 1} saved successfully.`, "success");
  };

  const handleSelectRevisionSnapshot = (snapshot: QuoteRequestItem) => {
    setActiveRequest(snapshot);
    toast(`Viewing historical snapshot Revision #${snapshot.current_revision || 1} (Read-Only mode).`, "info");
  };

  const handleReturnToLatest = () => {
    setActiveRequest(currentLatestRequest);
    toast(`Returned to active latest revision (v${currentLatestRequest.current_revision || 1}).`, "success");
  };

  return (
    <div className="flex flex-col gap-6 pb-16">

      {/* Past Revision Alert Banner */}
      {isInspectingPastRevision ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-amber-300 bg-amber-50 p-4 text-amber-900 shadow-xs">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} className="text-amber-600 shrink-0" aria-hidden="true" />
            <div>
              <p className={cn(getTypographyClassName("label"), "text-amber-900")}>
                Viewing Past Revision #{activeRequest.current_revision} (Read-Only)
              </p>
              <p className={cn(getTypographyClassName("caption"), "text-amber-700")}>
                You are previewing a historical snapshot. Current latest revision is v{currentLatestRequest.current_revision}.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleReturnToLatest}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 rounded-[var(--radius-button)] bg-amber-600 px-4 py-1.5 text-white shadow-xs hover:bg-amber-700 transition-colors cursor-pointer"
            )}
          >
            <RotateCcw size={14} aria-hidden="true" />
            <span>Return to Latest (v{currentLatestRequest.current_revision})</span>
          </button>
        </div>
      ) : null}

      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)]">
        <div className="flex flex-col gap-2 min-w-0 flex-1">
          <WorkspaceNavigationLink
            href="/workspace/requests"
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1.5 text-[var(--color-muted)] hover:text-[var(--color-on-surface)] transition-colors"
            )}
          >
            <ArrowLeft size={14} aria-hidden="true" />
            <span>Back to Requests</span>
          </WorkspaceNavigationLink>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className={cn(getTypographyClassName("pageTitle"), "text-[var(--color-on-surface)] truncate")}>
              {displayHeading}
            </h1>

            <span
              className={cn(
                getTypographyClassName("caption"),
                "rounded-full px-3 py-1 border",
                isTraveller
                  ? "bg-sky-50 text-sky-700 border-sky-200"
                  : "bg-purple-50 text-purple-700 border-purple-200"
              )}
            >
              {isTraveller ? "B2C TRAVELLER" : "B2B ADVISOR"}
            </span>

            <span
              className={cn(
                getTypographyClassName("caption"),
                "rounded-full px-3 py-1 border",
                activeRequest.status === "quotation_created"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-blue-50 text-blue-700 border-blue-200"
              )}
            >
              {activeRequest.status === "quotation_created" ? "Quotation Created" : "New Request"}
            </span>

            {/* Revision Badge Button */}
            <button
              type="button"
              onClick={() => setIsHistoryOpen(true)}
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1.5 rounded-full px-3 py-1 border cursor-pointer transition-all hover:shadow-xs",
                isInspectingPastRevision
                  ? "bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200"
                  : "bg-neutral-100 text-neutral-800 border-neutral-300 hover:bg-neutral-200"
              )}
              title="Click to view full revision history"
            >
              <History size={12} aria-hidden="true" />
              <span>Revision: v{activeRequest.current_revision || 1}</span>
            </button>
          </div>

          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            Request ID: {activeRequest.id} • Brand:{" "}
            <span className="capitalize text-[var(--color-on-surface)]">
              {(payload.brand_id as string) || "selvara"}
            </span>{" "}
            • Submitted: {new Date(activeRequest.created_at).toLocaleString()}
          </p>
        </div>

        {/* Action Buttons Group */}
        <div className="flex flex-wrap items-center gap-3">
          {/* History Button */}
          <button
            type="button"
            onClick={() => setIsHistoryOpen(true)}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] transition-colors cursor-pointer"
            )}
          >
            <History size={15} aria-hidden="true" />
            <span>History</span>
          </button>

          {/* Edit Request Button */}
          <button
            type="button"
            onClick={() => {
              if (isInspectingPastRevision) {
                handleReturnToLatest();
              }
              setIsEditOpen(true);
            }}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)] transition-colors cursor-pointer"
            )}
          >
            <Edit3 size={15} aria-hidden="true" />
            <span>Edit Request</span>
          </button>

          {/* Primary Action Button */}
          <button
            type="button"
            onClick={handleGenerateQuotation}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-all hover:opacity-90 cursor-pointer"
            )}
          >
            <Sparkles size={16} aria-hidden="true" />
            <span>+ Generate Quotation</span>
          </button>
        </div>
      </div>

      {/* Edit Request Drawer Modal */}
      <EditRequestDrawer
        request={currentLatestRequest}
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        onSuccess={handleEditSuccess}
      />

      {/* Revision History Modal */}
      <RequestRevisionHistoryModal
        requestId={initialRequest.id}
        currentRevision={currentLatestRequest.current_revision || 1}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectRevision={handleSelectRevisionSnapshot}
      />


      {/* Linked Quotation Status Banner */}
      {activeRequest.linked_quotation_id ? (
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-card)] border border-emerald-300 bg-emerald-50/90 p-5 text-emerald-950 shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={24} className="text-emerald-600 shrink-0" aria-hidden="true" />
            <div>
              <h3 className={cn(getTypographyClassName("cardTitle"), "text-emerald-950")}>
                Quotation Proposal Generated
              </h3>
              <p className={cn(getTypographyClassName("caption"), "text-emerald-800")}>
                👉 Báo giá đã được tạo [{activeRequest.linked_quotation_id}]
              </p>
            </div>
          </div>

            <WorkspaceNavigationLink
            href={`/workspace/quotations/${activeRequest.linked_quotation_id}/edit?stage=facts`}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "flex items-center gap-2 rounded-[var(--radius-button)] bg-emerald-700 hover:bg-emerald-800 px-5 py-2.5 !text-white shadow-md transition-all"
            )}
          >
            <span>Mở Quotation Studio</span>
            <ExternalLink size={15} aria-hidden="true" />
            </WorkspaceNavigationLink>
        </section>
      ) : null}

      {/* Main 2-Column Responsive Grid */}
      <div className="grid gap-6 lg:grid-cols-2 items-start">
        {/* Column 1: Client, Route, Lead & Style */}
        <div className="flex flex-col gap-6">
          <LeadManagementCard
            brandId={payload.brand_id as string | undefined}
            travelDesignerId={
              (activeRequest.created_by_profile_id || payload.travel_designer_id) as string | undefined
            }
            priority={(payload.priority as string) || "normal"}
            leadSource={payload.lead_source as string | undefined}
            quoteDeadline={payload.quote_deadline as string | undefined}
            decisionDate={payload.decision_date as string | undefined}
            status={activeRequest.status}
            createdAt={activeRequest.created_at}
          />

          <ClientIdentityCard
            role={activeRequest.role}
            customerName={activeRequest.customer_name}
            clientName={payload.client_name as string | undefined}
            email={activeRequest.email}
            phone={activeRequest.phone}
            companyName={activeRequest.company_name}
            market={activeRequest.market}
            preferredContact={activeRequest.preferred_contact}
            clientContext={payload.client_context as string | undefined}
            partnerId={(activeRequest.partner_id || payload.partner_id) as string | undefined}
          />

          <JourneyRoutingCard
            destinations={activeRequest.destinations}
            startDate={activeRequest.start_date}
            endDate={activeRequest.end_date}
            rawDatesText={activeRequest.raw_dates_text}
            travelTiming={(payload.travel_timing || payload.date_flexibility) as string | undefined}
            arrivalCity={payload.arrival_city as string | undefined}
            departureCity={payload.departure_city as string | undefined}
            adults={activeRequest.adults}
            childrenCount={activeRequest.children}
            kidAges={activeRequest.kid_ages || []}
            infants={payload.infants as number | undefined}
            roomConfiguration={payload.room_configuration as string | undefined}
            routingConstraints={payload.routing_constraints as string | undefined}
          />

          <TravelStyleCard
            primaryTheme={activeRequest.travel_style || (payload.primary_theme as string | undefined)}
            travelPace={payload.travel_pace as string | undefined}
            occasion={payload.occasion as string | undefined}
            priority1={payload.priority_1 as string | undefined}
            priority2={payload.priority_2 as string | undefined}
            priority3={payload.priority_3 as string | undefined}
            mustHave={payload.must_have as string | undefined}
            avoid={payload.avoid as string | undefined}
            message={payload.message as string | undefined}
          />

          <SpecialRequirementsCard
            dietary={payload.dietary as string | undefined}
            halal={payload.halal as string | undefined}
            mobility={payload.mobility as string | undefined}
            healthConsiderations={payload.health_considerations as string | undefined}
            specialRequirements={activeRequest.special_requirements}
          />
        </div>

        {/* Column 2: Accommodation, Services, Commercial & Strategy */}
        <div className="flex flex-col gap-6">
          <AccommodationScopeCard
            hotelLevel={payload.hotel_level as string | undefined}
            preferredHotel={payload.preferred_hotel as string | undefined}
            roomType={payload.room_type as string | undefined}
            bedding={payload.bedding as string | undefined}
            connecting={payload.connecting as string | undefined}
            suiteInterest={payload.suite_interest as string | undefined}
            hotelStyle={payload.hotel_style as string | undefined}
          />

          <ServiceScopeCard
            privateVehicle={payload.private_vehicle as string | undefined}
            vehiclePreference={payload.vehicle_preference as string | undefined}
            guideLanguage={payload.guide_language as string | undefined}
            guideScope={payload.guide_scope as string | undefined}
            domesticFlights={payload.domestic_flights as string | undefined}
            intlFlights={payload.intl_flights as string | undefined}
            railCruise={payload.rail_cruise as string | undefined}
            transportClass={payload.transport_class as string | undefined}
            mealPlan={payload.meal_plan as string | undefined}
            diningLevel={payload.dining_level as string | undefined}
            experiencesIncluded={payload.experiences_included as string | undefined}
            optionalActivities={payload.optional_activities as string | undefined}
            visaFasttrack={payload.visa_fasttrack as string | undefined}
            meetAssist={payload.meet_assist as string | undefined}
            insurance={payload.insurance as string | undefined}
            otherServices={payload.other_services as string | undefined}
          />

          <CommercialPricingCard
            isB2B={!isTraveller}
            budget={payload.budget as number | undefined}
            budgetBasis={payload.budget_basis as string | undefined}
            currency={(payload.currency as string) || "USD"}
            pricingType={payload.pricing_type as string | undefined}
            commission={payload.commission as number | undefined}
            showCommission={payload.show_commission as string | undefined}
            priceDisplay={payload.price_display as string | undefined}
            targetGp={payload.target_gp as number | undefined}
            minimumGp={payload.minimum_gp as number | undefined}
            contingency={payload.contingency as number | undefined}
            paymentFee={payload.payment_fee as number | undefined}
            taxTreatment={payload.tax_treatment as string | undefined}
            discountCap={payload.discount_cap as string | undefined}
            quoteValidity={payload.quote_validity as string | undefined}
            paymentTerms={payload.payment_terms as string | undefined}
          />

          <ReadinessStrategyCard
            existingTemplate={payload.existing_template as string | undefined}
            ratesAvailable={payload.rates_available as string | undefined}
            rfqRequired={payload.rfq_required as string | undefined}
            rateRisk={payload.rate_risk as string | undefined}
            preferredSuppliers={payload.preferred_suppliers as string | undefined}
            missingInfo={payload.missing_info as string | undefined}
            journeyDirection={payload.journey_direction as string | undefined}
            sellingAngle={payload.selling_angle as string | undefined}
            competitor={payload.competitor as string | undefined}
            internalNotes={payload.internal_notes as string | undefined}
          />
        </div>
      </div>

      {/* Full-width Daily Itinerary Schedule */}
      <DailyItineraryTimeline days={itineraryDays} />
    </div>
  );
}
