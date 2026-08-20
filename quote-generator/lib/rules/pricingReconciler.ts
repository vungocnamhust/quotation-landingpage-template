/**
 * Pure domain rules for commercial pricing reconciliation, 3-tier FX conversion,
 * child preset ratios, and Pax count synchronization (TypeScript).
 * Guarantees invariant synchronization between:
 * groupTotal <-> perAdult <-> perChild <-> currency <-> Pax counts
 */

export const SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "AUD", "VND"] as const;
export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export const MAX_COMMERCIAL_OPTIONS = 3;

/**
 * Standard Tier 1 Fallback Exchange Rates (relative to 1 USD).
 * 1 USD = 25,400 VND | 0.92 EUR | 0.78 GBP | 1.50 AUD
 */
export const DEFAULT_EXCHANGE_RATES: Record<string, number> = {
  USD: 1.0,
  VND: 25400,
  EUR: 0.92,
  GBP: 0.78,
  AUD: 1.50,
};

export type ExchangeRateTable = Record<string, number>;

export type ExchangeRateMeta = {
  baseCurrency: string;
  targetCurrency: string;
  rate: number;
  source?: "config" | "brand" | "custom" | string;
  appliedAt?: string;
  fxBufferPercent?: number;
};

export type CanonicalPricingOption = {
  id: string;
  label: string;
  currency: string;
  perAdultMinor: number | null;
  perChildMinor: number | null;
  groupTotalMinor: number | null;
  perTravelerMinor?: number | null;
  childRatio?: number | null;
  exchangeRateMeta?: ExchangeRateMeta | null;
  [key: string]: unknown;
};

export type CanonicalCommercialPricing = {
  currency: string;
  adults: number;
  children: number;
  options: CanonicalPricingOption[];
  conditions?: string[];
  exchangeRates?: ExchangeRateTable;
  // Commercial Request & Budget Specs
  budget?: number | null; // Float in major units (e.g. 5000 USD)
  budgetBasis?: "per_person" | "total_group" | "Total trip" | string | null;
  pricingType?: "Gross" | "Net" | "Commissionable" | string | null;
  commission?: number | null;
  showCommission?: string | null;
  priceDisplay?: string | null;
  targetGp?: number | null;
  minimumGp?: number | null;
  contingency?: number | null;
  paymentFee?: number | null;
  taxTreatment?: string | null;
  discountCap?: string | null;
  quoteValidity?: string | null;
  paymentTerms?: string | null;
};

/**
 * Return divisor for currency: 1 for VND (0 decimal places), 100 for USD/EUR/GBP/AUD (2 decimals).
 */
export function currencyDivisor(currency: string | null | undefined): number {
  return (currency || "").toUpperCase() === "VND" ? 1 : 100;
}

/**
 * Convert minor unit integer amount (cents) to major unit float (e.g. 400000 cents -> 4000 USD, 5000000 VND -> 5000000 VND).
 */
export function minorToMajor(
  minor: number | null | undefined,
  currency: string | null | undefined
): number | null {
  if (minor === null || minor === undefined || isNaN(minor)) return null;
  const divisor = currencyDivisor(currency);
  return minor / divisor;
}

/**
 * Convert major unit float to minor unit integer amount (e.g. 4000 USD -> 400000 cents).
 */
export function majorToMinor(
  major: number | null | undefined,
  currency: string | null | undefined
): number | null {
  if (major === null || major === undefined || isNaN(major)) return null;
  const divisor = currencyDivisor(currency);
  return Math.round(major * divisor);
}

/**
 * Compute the exchange rate from fromCurrency to toCurrency.
 */
export function getExchangeRate(
  fromCurrency: string | null | undefined,
  toCurrency: string | null | undefined,
  rateTable: ExchangeRateTable = DEFAULT_EXCHANGE_RATES
): number {
  const from = (fromCurrency || "USD").toUpperCase();
  const to = (toCurrency || "USD").toUpperCase();
  if (from === to) return 1.0;

  const fromRate = rateTable[from] ?? DEFAULT_EXCHANGE_RATES[from] ?? 1.0;
  const toRate = rateTable[to] ?? DEFAULT_EXCHANGE_RATES[to] ?? 1.0;

  if (fromRate <= 0) return 1.0;
  return toRate / fromRate;
}

/**
 * Convert minor amount from one currency to another using the exchange rate table.
 * Accurately handles difference in divisors between currencies.
 */
export function convertCurrencyAmount(
  amountMinor: number | null | undefined,
  fromCurrency: string | null | undefined,
  toCurrency: string | null | undefined,
  options?: {
    customRate?: number | null;
    rateTable?: ExchangeRateTable;
  }
): number | null {
  if (amountMinor === null || amountMinor === undefined || amountMinor <= 0) {
    return null;
  }

  const from = (fromCurrency || "USD").toUpperCase();
  const to = (toCurrency || "USD").toUpperCase();
  if (from === to) return amountMinor;

  const rate =
    options?.customRate !== undefined && options?.customRate !== null && options?.customRate > 0
      ? options.customRate
      : getExchangeRate(from, to, options?.rateTable);

  const fromDivisor = currencyDivisor(from);
  const toDivisor = currencyDivisor(to);

  // Convert minor -> major in fromCurrency, multiply rate -> major in toCurrency, convert to minor in toCurrency
  const majorFrom = amountMinor / fromDivisor;
  const majorTo = majorFrom * rate;
  return Math.round(majorTo * toDivisor);
}

/**
 * Create a default CanonicalPricingOption object.
 */
export function createDefaultPricingOption(
  index: number = 1,
  currency: string = "USD"
): CanonicalPricingOption {
  const defaultLabels = [
    "Standard Luxury Option",
    "Signature Executive Option",
    "Premier Villa Option",
  ];
  const label = defaultLabels[index - 1] || `Pricing Option ${index}`;

  return {
    id: `opt_${Date.now()}_${index}`,
    label,
    currency,
    perAdultMinor: null,
    perChildMinor: null,
    groupTotalMinor: null,
    perTravelerMinor: null,
    childRatio: 0.75,
  };
}

export const pricingReconciler = {
  currencyDivisor,
  minorToMajor,
  majorToMinor,
  getExchangeRate,
  convertCurrencyAmount,
  createDefaultPricingOption,

  /**
   * Pure forward calculation of total price from adult & child rates and Pax counts.
   * Invariant: Total = (Adults * PerAdult) + (Children * PerChild)
   */
  calculateOptionTotal(
    perAdultMinor: number | null | undefined,
    perChildMinor: number | null | undefined,
    adults: number = 2,
    children: number = 0
  ): number | null {
    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    if (perAdultMinor === null || perAdultMinor === undefined || perAdultMinor <= 0) {
      return null;
    }

    const adultSubtotal = safeAdults * perAdultMinor;
    const childSubtotal =
      safeKids * (perChildMinor !== null && perChildMinor !== undefined && perChildMinor >= 0 ? perChildMinor : 0);

    return adultSubtotal + childSubtotal;
  },

  /**
   * Pure reverse inference of adult & child rates from group total price and Pax counts.
   * Invariant: WeightedUnits = Adults + (Children * ChildRatio)
   *            PerAdult = round(GroupTotal / WeightedUnits)
   *            PerChild = round(PerAdult * ChildRatio)
   */
  inferOptionRatesFromTotal(
    groupTotalMinor: number | null | undefined,
    adults: number = 2,
    children: number = 0,
    childRatio: number = 0.75
  ): { perAdultMinor: number | null; perChildMinor: number | null } {
    if (groupTotalMinor === null || groupTotalMinor === undefined || groupTotalMinor <= 0) {
      return { perAdultMinor: null, perChildMinor: null };
    }

    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    const safeRatio = Math.max(0, childRatio);
    const weightedUnits = safeAdults + safeKids * safeRatio;
    if (weightedUnits <= 0) {
      return { perAdultMinor: null, perChildMinor: null };
    }

    const perAdult = Math.round(groupTotalMinor / weightedUnits);
    const perChild = safeKids > 0 ? Math.round(perAdult * safeRatio) : null;

    return { perAdultMinor: perAdult, perChildMinor: perChild };
  },

  /**
   * Apply a child preset ratio (e.g. 0.0, 0.5, 0.75, 1.0) to an option and recalculate group total.
   */
  applyChildPreset(
    option: CanonicalPricingOption,
    ratio: number,
    adults: number = 2,
    children: number = 0
  ): CanonicalPricingOption {
    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    if (option.perAdultMinor === null || option.perAdultMinor <= 0) {
      return {
        ...option,
        childRatio: ratio,
      };
    }

    const childMinor = ratio <= 0 ? 0 : Math.round(option.perAdultMinor * ratio);
    const effectiveChildMinor = safeKids > 0 ? childMinor : null;
    const newTotal = this.calculateOptionTotal(
      option.perAdultMinor,
      effectiveChildMinor,
      safeAdults,
      safeKids
    );

    return {
      ...option,
      childRatio: ratio,
      perChildMinor: effectiveChildMinor,
      groupTotalMinor: newTotal,
      perTravelerMinor: option.perAdultMinor,
    };
  },

  /**
   * Update adult rate and recalculate group total.
   */
  updateOptionPerAdult(
    option: CanonicalPricingOption,
    perAdultMinor: number | null,
    adults: number = 2,
    children: number = 0,
    options?: { maintainChildRatio?: boolean }
  ): CanonicalPricingOption {
    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    let nextChildMinor = option.perChildMinor;
    if (
      options?.maintainChildRatio &&
      option.childRatio !== undefined &&
      option.childRatio !== null &&
      perAdultMinor !== null &&
      perAdultMinor > 0 &&
      safeKids > 0
    ) {
      nextChildMinor = Math.round(perAdultMinor * option.childRatio);
    }

    const newTotal = this.calculateOptionTotal(
      perAdultMinor,
      nextChildMinor,
      safeAdults,
      safeKids
    );

    return {
      ...option,
      perAdultMinor,
      perChildMinor: safeKids > 0 ? nextChildMinor : null,
      groupTotalMinor: newTotal,
      perTravelerMinor: perAdultMinor,
    };
  },

  /**
   * Update child rate and recalculate group total.
   */
  updateOptionPerChild(
    option: CanonicalPricingOption,
    perChildMinor: number | null,
    adults: number = 2,
    children: number = 0
  ): CanonicalPricingOption {
    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    const effectiveChild = safeKids > 0 ? perChildMinor : null;
    const newTotal = this.calculateOptionTotal(
      option.perAdultMinor,
      effectiveChild,
      safeAdults,
      safeKids
    );

    const derivedRatio =
      option.perAdultMinor && option.perAdultMinor > 0 && effectiveChild !== null
        ? effectiveChild / option.perAdultMinor
        : option.childRatio ?? 0.75;

    return {
      ...option,
      perChildMinor: effectiveChild,
      childRatio: derivedRatio,
      groupTotalMinor: newTotal,
    };
  },

  /**
   * Update total group price and reverse-infer adult & child rates.
   */
  updateOptionTotal(
    option: CanonicalPricingOption,
    groupTotalMinor: number | null,
    adults: number = 2,
    children: number = 0,
    fallbackChildRatio: number = 0.75
  ): CanonicalPricingOption {
    const safeAdults = Math.max(1, adults);
    const safeKids = Math.max(0, children);

    if (groupTotalMinor === null || groupTotalMinor <= 0) {
      return {
        ...option,
        groupTotalMinor: null,
      };
    }

    const currentRatio =
      option.perAdultMinor && option.perChildMinor !== null && option.perChildMinor !== undefined
        ? option.perChildMinor / option.perAdultMinor
        : option.childRatio ?? fallbackChildRatio;

    const { perAdultMinor, perChildMinor } = this.inferOptionRatesFromTotal(
      groupTotalMinor,
      safeAdults,
      safeKids,
      currentRatio
    );

    return {
      ...option,
      perAdultMinor,
      perChildMinor: safeKids > 0 ? perChildMinor : null,
      childRatio: currentRatio,
      groupTotalMinor,
      perTravelerMinor: perAdultMinor,
    };
  },

  /**
   * Convert an individual pricing option to a new currency.
   * Supports smart amount conversion (Smart Convert) or unit switch only (Keep Numbers).
   */
  convertOptionCurrency(
    option: CanonicalPricingOption,
    nextCurrency: string,
    config?: {
      convertAmounts?: boolean;
      customRate?: number | null;
      rateTable?: ExchangeRateTable;
      adults?: number;
      children?: number;
    }
  ): CanonicalPricingOption {
    const nextCurr = nextCurrency.toUpperCase();
    const prevCurr = (option.currency || "USD").toUpperCase();
    if (nextCurr === prevCurr) return option;

    const shouldConvert = config?.convertAmounts ?? true;
    const rate =
      config?.customRate !== undefined && config?.customRate !== null && config?.customRate > 0
        ? config.customRate
        : getExchangeRate(prevCurr, nextCurr, config?.rateTable);

    if (!shouldConvert) {
      return {
        ...option,
        currency: nextCurr,
        exchangeRateMeta: {
          baseCurrency: prevCurr,
          targetCurrency: nextCurr,
          rate,
          source: "unit_switch",
          appliedAt: new Date().toISOString(),
        },
      };
    }

    const nextAdult = convertCurrencyAmount(option.perAdultMinor, prevCurr, nextCurr, {
      customRate: rate,
      rateTable: config?.rateTable,
    });
    const nextChild = convertCurrencyAmount(option.perChildMinor, prevCurr, nextCurr, {
      customRate: rate,
      rateTable: config?.rateTable,
    });

    const safeAdults = config?.adults ?? 2;
    const safeKids = config?.children ?? 0;
    const nextTotal = this.calculateOptionTotal(nextAdult, nextChild, safeAdults, safeKids);

    return {
      ...option,
      currency: nextCurr,
      perAdultMinor: nextAdult,
      perChildMinor: nextChild,
      groupTotalMinor: nextTotal,
      perTravelerMinor: nextAdult,
      exchangeRateMeta: {
        baseCurrency: prevCurr,
        targetCurrency: nextCurr,
        rate,
        source: config?.customRate ? "custom" : "config",
        appliedAt: new Date().toISOString(),
      },
    };
  },

  /**
   * Synchronize all options in CanonicalCommercialPricing when traveller counts change.
   * Invariant: perAdultMinor and perChildMinor remain locked, and groupTotalMinor is recalculated for all options.
   * If an option had only groupTotalMinor without rates, rates are first inferred from previous counts, then recalculated.
   */
  syncPaxCounts<T extends CanonicalCommercialPricing>(
    pricing: T,
    nextAdults: number = 2,
    nextChildren: number = 0
  ): T {
    const safeAdults = Math.max(1, nextAdults);
    const safeKids = Math.max(0, nextChildren);

    const prevAdults = Math.max(1, pricing.adults || 2);
    const prevKids = Math.max(0, pricing.children || 0);

    const updatedOptions = pricing.options.map((option) => {
      let adultRate = option.perAdultMinor;
      let childRate = option.perChildMinor;

      // If rates were missing but total existed, infer rates using previous counts
      if ((!adultRate || adultRate <= 0) && option.groupTotalMinor && option.groupTotalMinor > 0) {
        const inferred = this.inferOptionRatesFromTotal(
          option.groupTotalMinor,
          prevAdults,
          prevKids,
          option.childRatio ?? 0.75
        );
        adultRate = inferred.perAdultMinor;
        childRate = inferred.perChildMinor;
      }

      // If there are now children but childRate was null, calculate from childRatio
      if (safeKids > 0 && childRate === null && adultRate && adultRate > 0) {
        const ratio = option.childRatio ?? 0.75;
        childRate = Math.round(adultRate * ratio);
      } else if (safeKids === 0) {
        childRate = null;
      }

      const recalculatedTotal = this.calculateOptionTotal(
        adultRate,
        childRate,
        safeAdults,
        safeKids
      );

      return {
        ...option,
        perAdultMinor: adultRate,
        perChildMinor: safeKids > 0 ? childRate : null,
        groupTotalMinor: recalculatedTotal,
        perTravelerMinor: adultRate,
      };
    });

    return {
      ...pricing,
      adults: safeAdults,
      children: safeKids,
      options: updatedOptions,
    };
  },

  /**
   * Add a new pricing option up to MAX_COMMERCIAL_OPTIONS.
   */
  addOption<T extends CanonicalCommercialPricing>(
    pricing: T,
    defaultLabel?: string
  ): T {
    if (pricing.options.length >= MAX_COMMERCIAL_OPTIONS) {
      return pricing;
    }

    const nextIndex = pricing.options.length + 1;
    const newOption = createDefaultPricingOption(nextIndex, pricing.currency || "USD");
    if (defaultLabel) {
      newOption.label = defaultLabel;
    }

    return {
      ...pricing,
      options: [...pricing.options, newOption],
    };
  },

  /**
   * Remove a pricing option at a given index safely.
   */
  removeOption<T extends CanonicalCommercialPricing>(
    pricing: T,
    removeIndex: number
  ): T {
    if (removeIndex < 0 || removeIndex >= pricing.options.length) {
      return pricing;
    }

    const filtered = pricing.options.filter((_, i) => i !== removeIndex);
    return {
      ...pricing,
      options: filtered,
    };
  },

  /**
   * Update an option at index with arbitrary patch, maintaining domain invariants.
   */
  updateOption<T extends CanonicalCommercialPricing>(
    pricing: T,
    index: number,
    patch: Partial<CanonicalPricingOption>
  ): T {
    if (index < 0 || index >= pricing.options.length) {
      return pricing;
    }

    const currentOption = pricing.options[index];
    const safeAdults = Math.max(1, pricing.adults || 2);
    const safeKids = Math.max(0, pricing.children || 0);

    let updatedOption: CanonicalPricingOption = {
      ...currentOption,
      ...patch,
    };

    // If adult price changed in patch, recalculate total
    if (patch.perAdultMinor !== undefined && patch.groupTotalMinor === undefined) {
      updatedOption = this.updateOptionPerAdult(
        updatedOption,
        patch.perAdultMinor,
        safeAdults,
        safeKids
      );
    } else if (patch.perChildMinor !== undefined && patch.groupTotalMinor === undefined) {
      updatedOption = this.updateOptionPerChild(
        updatedOption,
        patch.perChildMinor,
        safeAdults,
        safeKids
      );
    } else if (patch.groupTotalMinor !== undefined && patch.perAdultMinor === undefined) {
      updatedOption = this.updateOptionTotal(
        updatedOption,
        patch.groupTotalMinor,
        safeAdults,
        safeKids
      );
    }

    const nextOptions = [...pricing.options];
    nextOptions[index] = updatedOption;

    return {
      ...pricing,
      options: nextOptions,
    };
  },
};
