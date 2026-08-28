/**
 * Pure adapter bridging the media slot registry contract with the rendered
 * QuoteDocument (Layer 2, Plan 16.1 §3.2/M3.2).
 *
 * Single source for two things that had drifted into 3 independent copies:
 * "which registry slot does this live selection belong to" and "what
 * destination/accommodation context should seed the media picker". Reads
 * exclusively from the rendered `QuoteDocument` — never from raw intake
 * facts, which lag behind the document mid-edit (Plan 16.1 §1.5).
 */
import { matchEditableSource } from '../../components/quotation-workspace/editableHandoff.ts';
import { resolveEntityIndex } from './mediaSlotReconciler.ts';

export type MediaSlotPickerContext = 'library' | 'destination' | 'accommodation' | 'team';

export type MediaSlotDescriptor = {
  fieldTemplate: string;
  source: string;
  editorRoute: string;
  pickerContext: MediaSlotPickerContext;
  minItems: number;
  maxItems: number;
  requiredForPublish: boolean;
  layoutVariants?: string[];
  keys?: string[];
};

export type MatchedMediaSlot = { slot: MediaSlotDescriptor; fieldId: string };

export type MediaPickerTarget = {
  initialPrefix?: string;
  context?: { kind: 'destination' | 'accommodation'; destinationId?: string; accommodationName?: string };
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

/**
 * Resolve a live element's editable descriptor (`fieldId`/`source`) to its
 * media slot registry entry, concretizing any `*` wildcard from the
 * resolved source. Returns null when the selection is not a registered media
 * field — there is deliberately no hardcoded fallback slot (the old
 * `hero.bannerImage` special case named a field the contract never defined).
 *
 * `selectedFieldId` is the *static* contract fieldId (it still carries a
 * literal `*` for a repeated field — `InspectorDescriptor` is shared across
 * every instance of that field, never resolved per-instance). Only a
 * non-wildcard template may match it directly; a wildcard template must
 * always resolve its concrete index from `selectedSource` instead, or every
 * day/hotel would collapse onto the same un-concretized `fieldId` (a bug in
 * the pre-M3.2 duplicate copies of this logic).
 */
export function matchSlotDescriptor(
  mediaSlots: readonly MediaSlotDescriptor[],
  selectedFieldId: string,
  selectedSource: string
): MatchedMediaSlot | null {
  for (const slot of mediaSlots) {
    const hasWildcard = slot.fieldTemplate.includes('*');
    if (!hasWildcard && slot.fieldTemplate === selectedFieldId) {
      return { slot, fieldId: slot.fieldTemplate };
    }
    const wildcardIndices = matchEditableSource(slot.source, selectedSource);
    if (hasWildcard && wildcardIndices && wildcardIndices.length > 0) {
      const sourceParts = selectedSource.startsWith('/') ? selectedSource.slice(1).split('/') : selectedSource.split('/');
      const indexVal = sourceParts[wildcardIndices[0]];
      return { slot, fieldId: slot.fieldTemplate.replace('*', indexVal) };
    }
  }
  return null;
}

function mediaPrefix(destRef: Record<string, unknown>): string | undefined {
  if (typeof destRef.mediaPrefix === 'string' && destRef.mediaPrefix) return destRef.mediaPrefix;
  if (typeof destRef.defaultMediaPrefix === 'string' && destRef.defaultMediaPrefix) return destRef.defaultMediaPrefix;
  return undefined;
}

function destinationTarget(destRef: Record<string, unknown>): MediaPickerTarget {
  const prefix = mediaPrefix(destRef) ?? (typeof destRef.slug === 'string' && destRef.slug ? `destination/${destRef.slug}` : undefined);
  const destinationId = typeof destRef.id === 'string' ? destRef.id : undefined;
  return { initialPrefix: prefix, context: destinationId ? { kind: 'destination', destinationId } : undefined };
}

/**
 * Derive the picker's starting R2 prefix and destination/accommodation
 * context for a media fieldId.
 */
export function derivePickerTarget(document: Record<string, unknown>, fieldId: string): MediaPickerTarget {
  const days = Array.isArray(record(document.itinerary).days) ? (record(document.itinerary).days as unknown[]) : [];
  const hotels = Array.isArray(record(document.stays).hotels) ? (record(document.stays).hotels as unknown[]) : [];

  if (fieldId.startsWith('itinerary.days.')) {
    // The day segment is a stable id (v4 contract) or a numeric index
    // (legacy v3) — id resolved first (Plan 16.1 M3.3).
    const dayIndex = resolveEntityIndex(days.map(record), fieldId.split('.')[2]);
    return dayIndex === null ? {} : destinationTarget(record(record(days[dayIndex]).destinationRef));
  }

  if (fieldId.startsWith('stays.hotels.')) {
    const hotelIndex = resolveEntityIndex(hotels.map(record), fieldId.split('.')[2]);
    if (hotelIndex === null) return {};
    const hotel = record(hotels[hotelIndex]);
    const destRef = record(hotel.destinationRef);
    const hotelName = typeof hotel.name === 'string' ? hotel.name : undefined;
    const destinationId = typeof destRef.id === 'string' ? destRef.id : undefined;
    const prefix = mediaPrefix(destRef) ?? (destinationId ? 'accommodations' : undefined);
    return {
      initialPrefix: prefix,
      context: destinationId && hotelName ? { kind: 'accommodation', destinationId, accommodationName: hotelName } : undefined,
    };
  }

  if (fieldId === 'assets.hero' || fieldId === 'assets.itineraryDivider' || fieldId === 'assets.staysDivider' || fieldId === 'assets.hotelDivider') {
    return { initialPrefix: mediaPrefix(record(record(days[0]).destinationRef)) };
  }

  return {};
}
