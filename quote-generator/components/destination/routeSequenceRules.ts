import type { DestinationRef } from "./types.ts";
import type { ToastType } from "../staff-workspace/ToastProvider.tsx";
import { parseRouteTokens } from "../../lib/rules/routeRules.ts";

/**
 * Pure domain rules for RouteSequenceInput:
 * - Consecutive adjacent duplicate detection and collapsing
 * - Round-trip preservation (non-consecutive duplicates)
 * - Deterministic, collision-free React chip key generation
 * Zero React dependencies, 100% deterministic.
 */

export type ToastHandler = (message: string, type?: ToastType) => void;

/**
 * Normalize destination name for whitespace and case-insensitive comparison.
 */
export function normalizeDestinationName(name?: string | null): string {
  return (name || "").trim().toLowerCase();
}

/**
 * Strip diacritics and non-alphanumeric chars to produce a comparable alpha slug.
 */
export function toComparableAlpha(str?: string | null): string {
  return (str || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

/**
 * Determine if a candidate destination matches the immediately preceding destination.
 * Matches on normalized name, normalized alpha slug, or exact id match.
 */
export function isConsecutiveDuplicateDestination(
  candidate: DestinationRef | string | null | undefined,
  previous: DestinationRef | string | null | undefined
): boolean {
  if (!candidate || !previous) return false;

  const candidateName = typeof candidate === "string" ? candidate : candidate.name;
  const candidateSlug = typeof candidate === "string" ? "" : candidate.slug;
  const candidateId = typeof candidate === "string" ? "" : candidate.id;

  const prevName = typeof previous === "string" ? previous : previous.name;
  const prevSlug = typeof previous === "string" ? "" : previous.slug;
  const prevId = typeof previous === "string" ? "" : previous.id;

  const cNorm = normalizeDestinationName(candidateName);
  const pNorm = normalizeDestinationName(prevName);

  if (cNorm && pNorm && cNorm === pNorm) return true;

  const cAlpha = toComparableAlpha(candidateSlug || candidateName);
  const pAlpha = toComparableAlpha(prevSlug || prevName);

  if (cAlpha && pAlpha && cAlpha === pAlpha) return true;

  if (candidateId && prevId && candidateId === prevId) return true;

  return false;
}

/**
 * Collapse consecutive adjacent duplicate tokens from a parsed route token list.
 * Non-consecutive duplicates (e.g. Hanoi -> Da Nang -> Hanoi) are strictly preserved.
 */
export function collapseConsecutiveTokens(
  tokens: string[],
  initialLastItem?: DestinationRef | string | null
): {
  retainedTokens: string[];
  omittedCount: number;
} {
  const retainedTokens: string[] = [];
  let omittedCount = 0;
  let currentLast: DestinationRef | string | null | undefined = initialLastItem;

  for (const token of tokens) {
    if (isConsecutiveDuplicateDestination(token, currentLast)) {
      omittedCount++;
    } else {
      retainedTokens.push(token);
      currentLast = token;
    }
  }

  return { retainedTokens, omittedCount };
}

/**
 * Generate collision-free React keys for destination chips.
 * Uses base destination identifier combined with index to guarantee uniqueness across round trips.
 */
export function getDestinationChipKey(
  ref: DestinationRef | null | undefined,
  index: number
): string {
  const base =
    ref?.id ||
    ref?.slug ||
    (ref?.name ? ref.name.toLowerCase().replace(/[^a-z0-9]/g, "_") : "dst");
  return `${base}-${index}`;
}

/**
 * Intercept and reject consecutive duplicate destination additions.
 * If rejected, triggers a warning toast and leaves current list unchanged.
 */
export function addDestinationWithGuard(
  candidate: DestinationRef,
  currentList: DestinationRef[],
  onToast?: ToastHandler
): {
  success: boolean;
  nextList: DestinationRef[];
} {
  const lastItem = currentList[currentList.length - 1];
  if (isConsecutiveDuplicateDestination(candidate, lastItem)) {
    onToast?.(
      `Cannot add consecutive duplicate destination "${candidate.name}".`,
      "warning"
    );
    return {
      success: false,
      nextList: currentList,
    };
  }

  return {
    success: true,
    nextList: [...currentList, candidate],
  };
}

/**
 * Parse and sanitize pasted route text/tokens with consecutive duplicate collapsing.
 */
export function pasteDestinationsWithGuard(
  pastedTextOrTokens: string | string[],
  currentList: DestinationRef[],
  onToast?: ToastHandler
): {
  success: boolean;
  nextList: DestinationRef[];
  omittedCount: number;
  newItems: DestinationRef[];
} {
  const tokens = Array.isArray(pastedTextOrTokens)
    ? pastedTextOrTokens
    : parseRouteTokens(pastedTextOrTokens);

  if (tokens.length <= 1) {
    return {
      success: false,
      nextList: currentList,
      omittedCount: 0,
      newItems: [],
    };
  }

  const lastItem = currentList[currentList.length - 1];
  const { retainedTokens, omittedCount } = collapseConsecutiveTokens(tokens, lastItem);

  if (omittedCount > 0) {
    onToast?.(
      "Consecutive duplicate destinations were omitted from the pasted route.",
      "warning"
    );
  }

  if (retainedTokens.length === 0) {
    return {
      success: false,
      nextList: currentList,
      omittedCount,
      newItems: [],
    };
  }

  const newItems: DestinationRef[] = retainedTokens.map((token, idx) => ({
    id: `dst_${token.toLowerCase().replace(/[^a-z0-9]/g, "_")}_${idx}`,
    name: token,
    slug: token.toLowerCase().replace(/\s+/g, "-"),
  }));

  return {
    success: true,
    nextList: [...currentList, ...newItems],
    omittedCount,
    newItems,
  };
}
