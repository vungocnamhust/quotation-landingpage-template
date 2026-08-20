"use client";

import { type QuoteRequestFormState } from "../../lib/quoteRequestPayload";
import { RequestIdentitySection } from "./request-sections/RequestIdentitySection";
import { RequestRoutingSection } from "./request-sections/RequestRoutingSection";
import { RequestTravelStyleSection } from "./request-sections/RequestTravelStyleSection";
import AccommodationScopeSection from "./AccommodationScopeSection";
import ServiceScopeSection from "./ServiceScopeSection";
import SpecialRequirementsSection from "./SpecialRequirementsSection";
import CommercialPricingSection from "./CommercialPricingSection";
import ReadinessAndStrategySection from "./ReadinessAndStrategySection";

import type { DestinationRef } from "../destination/types.ts";

export type { QuoteRequestFormState };

type Props = {
  state: QuoteRequestFormState;
  onChange: (updater: (prev: QuoteRequestFormState) => QuoteRequestFormState) => void;
  onApplyRouteToItinerary?: (destinations: DestinationRef[]) => void;
  disabled?: boolean;
};

export default function QuoteRequestForm({
  state,
  onChange,
  onApplyRouteToItinerary,
  disabled = false,
}: Props) {
  return (
    <div className="flex flex-col gap-6">
      {/* 1. Internal Lead Management & Identity Section */}
      <RequestIdentitySection state={state} onChange={onChange} disabled={disabled} />

      {/* 2. Routing, Travel Dates & Party Composition Section */}
      <RequestRoutingSection
        state={state}
        onChange={onChange}
        onApplyRouteToItinerary={onApplyRouteToItinerary}
        disabled={disabled}
      />

      {/* 3. Travel Themes, Priorities & Experience Pace Section */}
      <RequestTravelStyleSection state={state} onChange={onChange} disabled={disabled} />

      {/* 4. Functional Scope Sections */}
      <AccommodationScopeSection
        state={{
          hotel_level: state.hotel_level,
          preferred_hotel: state.preferred_hotel,
          room_type: state.room_type,
          bedding: state.bedding,
          connecting: state.connecting,
          suite_interest: state.suite_interest,
          hotel_style: state.hotel_style,
        }}
        disabled={disabled}
        onChange={(updater) =>
          onChange((prev) => {
            const next = updater({
              hotel_level: prev.hotel_level,
              preferred_hotel: prev.preferred_hotel,
              room_type: prev.room_type,
              bedding: prev.bedding,
              connecting: prev.connecting,
              suite_interest: prev.suite_interest,
              hotel_style: prev.hotel_style,
            });
            return { ...prev, ...next };
          })
        }
      />

      <ServiceScopeSection
        state={{
          private_vehicle: state.private_vehicle,
          vehicle_preference: state.vehicle_preference,
          guide_language: state.guide_language,
          guide_scope: state.guide_scope,
          domestic_flights: state.domestic_flights,
          intl_flights: state.intl_flights,
          rail_cruise: state.rail_cruise,
          transport_class: state.transport_class,
          meal_plan: state.meal_plan,
          dining_level: state.dining_level,
          experiences_included: state.experiences_included,
          optional_activities: state.optional_activities,
          visa_fasttrack: state.visa_fasttrack,
          meet_assist: state.meet_assist,
          insurance: state.insurance,
          other_services: state.other_services,
        }}
        disabled={disabled}
        onChange={(updater) =>
          onChange((prev) => {
            const next = updater({
              private_vehicle: prev.private_vehicle,
              vehicle_preference: prev.vehicle_preference,
              guide_language: prev.guide_language,
              guide_scope: prev.guide_scope,
              domestic_flights: prev.domestic_flights,
              intl_flights: prev.intl_flights,
              rail_cruise: prev.rail_cruise,
              transport_class: prev.transport_class,
              meal_plan: prev.meal_plan,
              dining_level: prev.dining_level,
              experiences_included: prev.experiences_included,
              optional_activities: prev.optional_activities,
              visa_fasttrack: prev.visa_fasttrack,
              meet_assist: prev.meet_assist,
              insurance: prev.insurance,
              other_services: prev.other_services,
            });
            return { ...prev, ...next };
          })
        }
      />

      <SpecialRequirementsSection
        state={{
          dietary: state.dietary,
          halal: state.halal,
          mobility: state.mobility,
          health_considerations: state.health_considerations,
        }}
        disabled={disabled}
        onChange={(updater) =>
          onChange((prev) => {
            const next = updater({
              dietary: prev.dietary,
              halal: prev.halal,
              mobility: prev.mobility,
              health_considerations: prev.health_considerations,
            });
            return { ...prev, ...next };
          })
        }
      />

      <CommercialPricingSection
        state={{
          budget: state.budget,
          budget_basis: state.budget_basis,
          currency: state.currency,
          pricing_type: state.pricing_type,
          commission: state.commission,
          show_commission: state.show_commission,
          price_display: state.price_display,
          target_gp: state.target_gp,
          minimum_gp: state.minimum_gp,
          contingency: state.contingency,
          payment_fee: state.payment_fee,
          tax_treatment: state.tax_treatment,
          discount_cap: state.discount_cap,
          quote_validity: state.quote_validity,
          payment_terms: state.payment_terms,
        }}
        isB2B={state.role === "advisor"}
        disabled={disabled}
        onChange={(updater) =>
          onChange((prev) => {
            const next = updater({
              budget: prev.budget,
              budget_basis: prev.budget_basis,
              currency: prev.currency,
              pricing_type: prev.pricing_type,
              commission: prev.commission,
              show_commission: prev.show_commission,
              price_display: prev.price_display,
              target_gp: prev.target_gp,
              minimum_gp: prev.minimum_gp,
              contingency: prev.contingency,
              payment_fee: prev.payment_fee,
              tax_treatment: prev.tax_treatment,
              discount_cap: prev.discount_cap,
              quote_validity: prev.quote_validity,
              payment_terms: prev.payment_terms,
            });
            return { ...prev, ...next };
          })
        }
      />

      <ReadinessAndStrategySection
        state={{
          existing_template: state.existing_template,
          rates_available: state.rates_available,
          rfq_required: state.rfq_required,
          rate_risk: state.rate_risk,
          preferred_suppliers: state.preferred_suppliers,
          missing_info: state.missing_info,
          journey_direction: state.journey_direction,
          selling_angle: state.selling_angle,
          competitor: state.competitor,
          internal_notes: state.internal_notes,
        }}
        disabled={disabled}
        onChange={(updater) =>
          onChange((prev) => {
            const next = updater({
              existing_template: prev.existing_template,
              rates_available: prev.rates_available,
              rfq_required: prev.rfq_required,
              rate_risk: prev.rate_risk,
              preferred_suppliers: prev.preferred_suppliers,
              missing_info: prev.missing_info,
              journey_direction: prev.journey_direction,
              selling_angle: prev.selling_angle,
              competitor: prev.competitor,
              internal_notes: prev.internal_notes,
            });
            return { ...prev, ...next };
          })
        }
      />
    </div>
  );
}
