/**
 * Pure domain rules for presentation resolution and override reconciliation (Layer 1).
 *
 * Implements strict 3-tier precedence hierarchy:
 * Design Override > Applied Content > Fact Baseline > Default Strategy.
 */

export type PresentationValueSource = 'override' | 'content' | 'fact' | 'default';

export type EffectivePresentationValue = {
  value: string;
  isOverridden: boolean;
  source: PresentationValueSource;
};

export type PresentationFieldInput = {
  fieldId: string;
  factValue?: string | null;
  contentValue?: string | null;
  designOverride?: string | null;
  defaultValue?: string;
};

/**
 * Pure function: Resolve the final displayed value for a field according to priority rules:
 * 1. Design Override (Highest priority, user explicitly customized layout/copy in Design stage)
 * 2. Applied Content (AI/Editor copy from Content Studio)
 * 3. Fact Baseline (Operational ground-truth from Intake / Facts)
 * 4. Default Strategy (Theme / Locale default)
 */
export function resolveEffectivePresentationValue(
  fieldId: string,
  factValue?: string | null,
  contentValue?: string | null,
  designOverride?: string | null,
  defaultValue: string = ''
): EffectivePresentationValue {
  if (typeof designOverride === 'string' && designOverride.trim().length > 0) {
    return {
      value: designOverride,
      isOverridden: true,
      source: 'override',
    };
  }

  if (typeof contentValue === 'string' && contentValue.trim().length > 0) {
    return {
      value: contentValue,
      isOverridden: false,
      source: 'content',
    };
  }

  if (typeof factValue === 'string' && factValue.trim().length > 0) {
    return {
      value: factValue,
      isOverridden: false,
      source: 'fact',
    };
  }

  return {
    value: defaultValue,
    isOverridden: false,
    source: 'default',
  };
}

/**
 * Pure function: Set or update an override in an immutable dictionary.
 */
export function setOverride(
  overrides: Record<string, string> = {},
  fieldId: string,
  value: string | null | undefined
): Record<string, string> {
  if (!fieldId) return { ...overrides };

  if (value === null || value === undefined || value.trim().length === 0) {
    return removeOverride(overrides, fieldId);
  }

  return {
    ...overrides,
    [fieldId]: value,
  };
}

/**
 * Pure function: Remove an override for a specific fieldId in an immutable dictionary.
 */
export function removeOverride(
  overrides: Record<string, string> = {},
  fieldId: string
): Record<string, string> {
  if (!fieldId || !(fieldId in overrides)) {
    return { ...overrides };
  }

  const next = { ...overrides };
  delete next[fieldId];
  return next;
}

/**
 * Pure function: Resolve an entire batch of fields in a single deterministic pass.
 */
export function resolveAllPresentationValues(
  fields: PresentationFieldInput[]
): Record<string, EffectivePresentationValue> {
  const result: Record<string, EffectivePresentationValue> = {};

  for (const field of fields) {
    result[field.fieldId] = resolveEffectivePresentationValue(
      field.fieldId,
      field.factValue,
      field.contentValue,
      field.designOverride,
      field.defaultValue ?? ''
    );
  }

  return result;
}

export const presentationReconciler = {
  resolveEffectivePresentationValue,
  setOverride,
  removeOverride,
  resolveAllPresentationValues,
};
