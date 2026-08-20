/**
 * Adapter module bridging application schemas (QuoteRequestFormState, QuotationFacts)
 * with the unified CanonicalParty model used by partyReconciler.
 */

import type { QuotationFacts } from "../../components/quotation-workspace/factsTypes.ts";
import { ensureFactsDefaults } from "../../components/quotation-workspace/factsTypes.ts";
import type { QuoteRequestFormState } from "../quoteRequestPayload.ts";
import {
  partyReconciler,
  type CanonicalParty,
  type RoomingRule,
} from "./partyReconciler.ts";

export const partyAdapter = {
  /**
   * Convert QuoteRequestFormState to CanonicalParty.
   */
  fromQuoteRequest(formState: QuoteRequestFormState, rules?: RoomingRule[]): CanonicalParty {
    const isAdvisor = formState.role === "advisor";
    const derivedName = isAdvisor
      ? formState.client_name?.trim() || ""
      : [formState.first_name, formState.last_name].filter(Boolean).join(" ").trim();

    return partyReconciler.reconcileParty(
      {
        customerName: derivedName || null,
        clientName: formState.client_name || null,
        role: formState.role || "traveller",
        adults: formState.adults ?? 2,
        children: formState.children ?? 0,
        kidAges: formState.kid_ages ?? [],
        infants: formState.infants ?? 0,
        roomConfiguration: formState.room_configuration || null,
        travelStyle: formState.primary_theme || null,
        market: formState.advisor_market || null,
        nationality: formState.country || null,
        lang: "en",
      },
      rules
    );
  },

  /**
   * Synchronize CanonicalParty back to QuoteRequestFormState.
   */
  syncToQuoteRequest(
    canonical: CanonicalParty,
    prev: QuoteRequestFormState
  ): QuoteRequestFormState {
    const isAdvisor = prev.role === "advisor";
    let firstName = prev.first_name;
    let lastName = prev.last_name;
    let clientName = prev.client_name;

    if (canonical.customerName) {
      if (isAdvisor) {
        clientName = canonical.customerName;
      } else if (!firstName && !lastName) {
        const parts = canonical.customerName.trim().split(/\s+/);
        firstName = parts[0] || "";
        lastName = parts.slice(1).join(" ") || "";
      }
    }

    return {
      ...prev,
      adults: canonical.adults,
      children: canonical.children,
      kid_ages: canonical.kidAges,
      infants: canonical.infants,
      room_configuration: canonical.roomConfiguration || "",
      first_name: firstName,
      last_name: lastName,
      client_name: clientName,
      primary_theme: canonical.travelStyle || prev.primary_theme,
    };
  },

  /**
   * Convert QuotationFacts to CanonicalParty.
   */
  fromQuotationFacts(factsInput: QuotationFacts, rules?: RoomingRule[]): CanonicalParty {
    const facts = ensureFactsDefaults(factsInput);
    const cust = facts.customer_facts;
    const services = facts.service_facts;

    return partyReconciler.reconcileParty(
      {
        customerName: cust.customer_name || null,
        adults: cust.adults ?? 2,
        children: cust.children ?? 0,
        kidAges: cust.kid_ages ?? [],
        partyLabel: cust.party_label || null,
        greetingName: cust.greeting_name || null,
        roomNotes: services.room_notes || null,
        travelStyle: cust.travel_style ?? cust.guest_profile ?? null,
        market: cust.market || null,
        nationality: cust.nationality || null,
        lang: facts.lang || "en",
      },
      rules
    );
  },

  /**
   * Synchronize CanonicalParty back to QuotationFacts.
   */
  syncToQuotationFacts(
    canonical: CanonicalParty,
    prevInput: QuotationFacts
  ): QuotationFacts {
    const safe = ensureFactsDefaults(prevInput);

    return {
      ...safe,
      customer_facts: {
        ...safe.customer_facts,
        customer_name: canonical.customerName,
        adults: canonical.adults,
        children: canonical.children,
        kid_ages: canonical.kidAges,
        party_label: canonical.partyLabel,
        greeting_name: canonical.greetingName,
        travel_style: canonical.travelStyle || safe.customer_facts.travel_style,
        guest_profile: canonical.travelStyle || safe.customer_facts.guest_profile,
        market: canonical.market || safe.customer_facts.market,
        nationality: canonical.nationality || safe.customer_facts.nationality,
      },
      service_facts: {
        ...safe.service_facts,
        room_notes: canonical.roomNotes || safe.service_facts.room_notes,
      },
    };
  },
};
