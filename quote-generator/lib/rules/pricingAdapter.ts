/**
 * Adapter module bridging application schemas (QuotationFacts, QuoteRequestFormState, TriPricing)
 * with the unified CanonicalCommercialPricing model used by pricingReconciler.
 */

import type {
  PricingOptionFact,
  QuotationFacts,
} from "../../components/quotation-workspace/factsTypes.ts";
import { ensureFactsDefaults } from "../../components/quotation-workspace/factsTypes.ts";
import type { QuoteRequestFormState } from "../quoteRequestPayload.ts";
import {
  currencyDivisor,
  pricingReconciler,
  type CanonicalCommercialPricing,
  type CanonicalPricingOption,
  type ExchangeRateTable,
} from "./pricingReconciler.ts";

export type TriPricingFields = {
  label: string;
  currency: string;
  perAdultMinor: number | null;
  perChildMinor: number | null;
  groupTotalMinor: number | null;
};

export const pricingAdapter = {
  /**
   * Convert QuotationFacts to CanonicalCommercialPricing.
   */
  fromQuotationFacts(factsInput: QuotationFacts): CanonicalCommercialPricing {
    const facts = ensureFactsDefaults(factsInput);
    const pricing = facts.pricing_facts;
    const cust = facts.customer_facts;

    const adults = cust.adults ?? 2;
    const children = cust.children ?? 0;
    const primaryCurrency = pricing.options[0]?.currency || "USD";

    const options: CanonicalPricingOption[] = pricing.options.map((opt, idx) => {
      const adult = opt.per_adult_amount_minor ?? opt.per_traveler_amount_minor ?? null;
      const child = opt.per_child_amount_minor ?? null;
      const total = opt.group_total_amount_minor ?? null;
      const childRatio =
        adult && adult > 0 && child !== null && child !== undefined
          ? child / adult
          : 0.75;

      return {
        id: opt.id || `opt_${idx + 1}`,
        label: opt.label || `Option ${idx + 1}`,
        currency: opt.currency || primaryCurrency,
        perAdultMinor: adult,
        perChildMinor: child,
        groupTotalMinor: total,
        perTravelerMinor: adult,
        childRatio,
      };
    });

    return {
      currency: primaryCurrency,
      adults,
      children,
      options: options.length > 0 ? options : [pricingReconciler.createDefaultPricingOption(1, primaryCurrency)],
      conditions: pricing.conditions ? [...pricing.conditions] : [],
    };
  },

  /**
   * Synchronize CanonicalCommercialPricing back to QuotationFacts.
   */
  syncToQuotationFacts(
    canonical: CanonicalCommercialPricing,
    prevInput: QuotationFacts
  ): QuotationFacts {
    const safe = ensureFactsDefaults(prevInput);

    const options: PricingOptionFact[] = canonical.options.map((opt, idx) => {
      const existing = safe.pricing_facts.options[idx];
      const adult = opt.perAdultMinor ?? opt.perTravelerMinor ?? null;
      const child = opt.perChildMinor ?? null;
      const total = opt.groupTotalMinor ?? null;

      return {
        id: opt.id || existing?.id || `opt-${idx + 1}`,
        label: opt.label || existing?.label || `Option ${idx + 1}`,
        currency: opt.currency || canonical.currency || "USD",
        per_traveler_amount_minor: adult,
        per_adult_amount_minor: adult,
        per_child_amount_minor: child,
        group_total_amount_minor: total,
      };
    });

    return {
      ...safe,
      customer_facts: {
        ...safe.customer_facts,
        adults: canonical.adults,
        children: canonical.children,
      },
      pricing_facts: {
        ...safe.pricing_facts,
        options,
        conditions: canonical.conditions ? [...canonical.conditions] : safe.pricing_facts.conditions,
      },
    };
  },

  /**
   * Convert QuoteRequestFormState to CanonicalCommercialPricing.
   */
  fromQuoteRequest(
    formState: QuoteRequestFormState,
    exchangeRates?: ExchangeRateTable
  ): CanonicalCommercialPricing {
    const adults = formState.adults || 2;
    const children = formState.children || 0;
    const currency = formState.currency || "USD";
    const divisor = currencyDivisor(currency);

    const budgetRaw = typeof formState.budget === "number" ? formState.budget : null;
    const basis = (formState.budget_basis || "Total trip").toLowerCase();
    const isPerPerson = basis.includes("per person") || basis.includes("per_person");

    let perAdultMinor: number | null = null;
    let perChildMinor: number | null = null;
    let groupTotalMinor: number | null = null;

    if (budgetRaw !== null && budgetRaw > 0) {
      const budgetMinor = Math.round(budgetRaw * divisor);
      if (isPerPerson) {
        perAdultMinor = budgetMinor;
        perChildMinor = children > 0 ? Math.round(perAdultMinor * 0.75) : null;
        groupTotalMinor = pricingReconciler.calculateOptionTotal(
          perAdultMinor,
          perChildMinor,
          adults,
          children
        );
      } else {
        groupTotalMinor = budgetMinor;
        const inferred = pricingReconciler.inferOptionRatesFromTotal(
          groupTotalMinor,
          adults,
          children,
          0.75
        );
        perAdultMinor = inferred.perAdultMinor;
        perChildMinor = inferred.perChildMinor;
      }
    }

    const defaultOption: CanonicalPricingOption = {
      id: "opt_request_1",
      label: "Standard Luxury Option",
      currency,
      perAdultMinor,
      perChildMinor,
      groupTotalMinor,
      perTravelerMinor: perAdultMinor,
      childRatio: 0.75,
    };

    return {
      currency,
      adults,
      children,
      options: [defaultOption],
      exchangeRates,
      budget: budgetRaw,
      budgetBasis: formState.budget_basis || "Total trip",
      pricingType: formState.pricing_type || "Gross",
      commission: typeof formState.commission === "number" ? formState.commission : null,
      showCommission: formState.show_commission || "No",
      priceDisplay: formState.price_display || "Total journey price",
      targetGp: typeof formState.target_gp === "number" ? formState.target_gp : null,
      minimumGp: typeof formState.minimum_gp === "number" ? formState.minimum_gp : null,
      contingency: typeof formState.contingency === "number" ? formState.contingency : null,
      paymentFee: typeof formState.payment_fee === "number" ? formState.payment_fee : null,
      taxTreatment: formState.tax_treatment || "",
      discountCap: formState.discount_cap || "",
      quoteValidity: formState.quote_validity || "",
      paymentTerms: formState.payment_terms || "",
    };
  },

  /**
   * Synchronize CanonicalCommercialPricing back to QuoteRequestFormState.
   */
  syncToQuoteRequest(
    canonical: CanonicalCommercialPricing,
    prev: QuoteRequestFormState
  ): QuoteRequestFormState {
    const primaryOption = canonical.options[0];
    const currency = primaryOption?.currency || canonical.currency || prev.currency || "USD";
    const divisor = currencyDivisor(currency);

    let budget: number | "" = prev.budget;
    let budgetBasis = prev.budget_basis;

    if (primaryOption) {
      if (primaryOption.groupTotalMinor !== null && primaryOption.groupTotalMinor > 0) {
        budget = primaryOption.groupTotalMinor / divisor;
        budgetBasis = "Total trip";
      } else if (primaryOption.perAdultMinor !== null && primaryOption.perAdultMinor > 0) {
        budget = primaryOption.perAdultMinor / divisor;
        budgetBasis = "Per person";
      }
    }

    return {
      ...prev,
      adults: canonical.adults,
      children: canonical.children,
      currency,
      budget,
      budget_basis: budgetBasis,
      pricing_type: canonical.pricingType || prev.pricing_type,
      commission: canonical.commission !== undefined && canonical.commission !== null ? canonical.commission : prev.commission,
      show_commission: canonical.showCommission || prev.show_commission,
      target_gp: canonical.targetGp !== undefined && canonical.targetGp !== null ? canonical.targetGp : prev.target_gp,
      minimum_gp: canonical.minimumGp !== undefined && canonical.minimumGp !== null ? canonical.minimumGp : prev.minimum_gp,
      contingency: canonical.contingency !== undefined && canonical.contingency !== null ? canonical.contingency : prev.contingency,
      payment_fee: canonical.paymentFee !== undefined && canonical.paymentFee !== null ? canonical.paymentFee : prev.payment_fee,
      tax_treatment: canonical.taxTreatment || prev.tax_treatment,
      discount_cap: canonical.discountCap || prev.discount_cap,
      quote_validity: canonical.quoteValidity || prev.quote_validity,
      payment_terms: canonical.paymentTerms || prev.payment_terms,
    };
  },

  /**
   * Convert TriPricing UI props to CanonicalPricingOption.
   */
  fromTriPricing(
    fields: TriPricingFields,
    _adults: number = 2,
    children: number = 0
  ): CanonicalPricingOption {
    const childRatio =
      fields.perAdultMinor && fields.perAdultMinor > 0 && fields.perChildMinor !== null
        ? fields.perChildMinor / fields.perAdultMinor
        : 0.75;

    return {
      id: `opt_tri_${Date.now()}`,
      label: fields.label || "Standard Luxury Option",
      currency: fields.currency || "USD",
      perAdultMinor: fields.perAdultMinor,
      perChildMinor: children > 0 ? fields.perChildMinor : null,
      groupTotalMinor: fields.groupTotalMinor,
      perTravelerMinor: fields.perAdultMinor,
      childRatio,
    };
  },

  /**
   * Convert CanonicalPricingOption to TriPricing UI props.
   */
  toTriPricing(option: CanonicalPricingOption): TriPricingFields {
    return {
      label: option.label,
      currency: option.currency,
      perAdultMinor: option.perAdultMinor,
      perChildMinor: option.perChildMinor,
      groupTotalMinor: option.groupTotalMinor,
    };
  },
};
