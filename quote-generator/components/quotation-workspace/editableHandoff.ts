import type { EditableBrochureContract, EditableHandoff } from './useQuotationWorkspace';

export type InspectorDescriptor = EditableBrochureContract['fields'][number];

export type ResolvedFocus = {
  kind: NonNullable<EditableHandoff['item']>;
  index: number;
  id?: string;
  blockIndex?: number;
  itemIndex?: number;
};

export type ResolvedHandoff = EditableHandoff & {
  source: string;
  wildcardIndices: number[];
  focus?: ResolvedFocus;
};

export type FactsDeepLink = {
  section: 'trip' | 'travellers' | 'programme' | 'services' | 'commercial' | 'seller';
  focus?: ResolvedFocus;
};

type JsonRecord = Record<string, unknown>;

function sourceSegments(value: string) {
  return value.startsWith('/') ? value.slice(1).split('/') : [];
}

function numericSegment(value: string | undefined) {
  if (!value || !/^\d+$/.test(value)) return null;
  return Number(value);
}

function readPath(document: Record<string, unknown>, segments: string[]) {
  return segments.reduce<unknown>((current, segment) => {
    if (Array.isArray(current)) return current[numericSegment(segment) ?? -1];
    if (!current || typeof current !== 'object') return undefined;
    return (current as JsonRecord)[segment];
  }, document);
}

export function matchEditableSource(template: string | undefined, source: string) {
  if (!template) return null;
  const templateParts = sourceSegments(template);
  const sourceParts = sourceSegments(source);
  if (!templateParts.length || templateParts.length !== sourceParts.length) return null;
  const wildcardIndices: number[] = [];
  for (let index = 0; index < templateParts.length; index += 1) {
    if (templateParts[index] === '*') {
      wildcardIndices.push(index);
      continue;
    }
    if (templateParts[index] !== sourceParts[index]) return null;
  }
  return wildcardIndices;
}

export function resolveInspectorDescriptor(fields: InspectorDescriptor[], source: string) {
  for (const descriptor of fields) {
    const wildcardIndices = matchEditableSource(descriptor.source, source);
    if (wildcardIndices) return { descriptor, wildcardIndices };
  }
  return null;
}

/**
 * Resolve an emitted marker to the canonical list record it came from. The
 * resolved ID is used only for navigation; the editor continues to own all
 * writes through its existing Facts/Content workflow.
 */
export function resolveEditableHandoff(
  descriptor: InspectorDescriptor,
  source: string,
  document: Record<string, unknown>,
): ResolvedHandoff | undefined {
  const handoff = descriptor.handoff;
  if (!handoff) return undefined;
  const sourceParts = sourceSegments(source);
  const wildcardIndices = matchEditableSource(descriptor.source, source);
  if (!wildcardIndices) return undefined;
  if (!handoff.item || handoff.indexFromSource === undefined) {
    return { ...handoff, source, wildcardIndices };
  }

  const index = numericSegment(sourceParts[handoff.indexFromSource]);
  if (index === null) return undefined;
  const record = readPath(document, sourceParts.slice(0, handoff.indexFromSource + 1));
  const id = record && typeof record === 'object' && typeof (record as JsonRecord).id === 'string'
    ? (record as JsonRecord).id as string
    : undefined;

  if (handoff.item === 'bookingTerm') {
    const itemsIndex = sourceParts.indexOf('items');
    const blockIndex = numericSegment(sourceParts[itemsIndex - 1]);
    const itemIndex = numericSegment(sourceParts[itemsIndex + 1]);
    if (blockIndex === null || itemIndex === null) return undefined;
    return {
      ...handoff,
      source,
      wildcardIndices,
      focus: { kind: 'bookingTerm', index: itemIndex, blockIndex, itemIndex },
    };
  }

  return { ...handoff, source, wildcardIndices, focus: { kind: handoff.item, index, id } };
}

export function serializeFactsFocus(focus: ResolvedFocus | undefined) {
  if (!focus) return undefined;
  if (focus.kind === 'bookingTerm') return `bookingTerm:${focus.blockIndex}:${focus.itemIndex}`;
  if (focus.id) return `${focus.kind}:${focus.id}`;
  return `${focus.kind}:index:${focus.index}`;
}

function recordsAt(document: Record<string, unknown>, path: string[]) {
  const value = readPath(document, path);
  return Array.isArray(value) ? value : [];
}

function findRecordIndex(records: unknown[], token: string) {
  return records.findIndex((record) => record && typeof record === 'object' && (record as JsonRecord).id === token);
}

/** Parse only the typed, allowlisted focus grammar. Unknown/stale targets deliberately fall back to the parent Facts card. */
export function parseFactsDeepLink(
  section: string | null,
  focusValue: string | null,
  document: Record<string, unknown> | undefined,
): FactsDeepLink | undefined {
  if (!section || !['trip', 'travellers', 'programme', 'services', 'commercial', 'seller'].includes(section)) return undefined;
  const result: FactsDeepLink = { section: section as FactsDeepLink['section'] };
  if (!focusValue || !document) return result;
  const [kind, token, fallbackIndex] = focusValue.split(':');
  if (kind === 'bookingTerm' && /^\d+$/.test(token ?? '') && /^\d+$/.test(fallbackIndex ?? '')) {
    const blockIndex = Number(token);
    const itemIndex = Number(fallbackIndex);
    const blocks = recordsAt(document, ['content', 'sections', 'booking_terms', 'blocks']);
    const flatIndex = blocks.slice(0, blockIndex).reduce((total, block) => {
      const items = block && typeof block === 'object' && Array.isArray((block as JsonRecord).items)
        ? (block as JsonRecord).items as unknown[]
        : [];
      return total + items.length;
    }, 0) + itemIndex;
    const block = blocks[blockIndex];
    const items = block && typeof block === 'object' && Array.isArray((block as JsonRecord).items)
      ? (block as JsonRecord).items as unknown[]
      : [];
    if (!items[itemIndex]) return result;
    result.focus = { kind: 'bookingTerm', index: flatIndex, blockIndex, itemIndex };
    return result;
  }
  if (!['day', 'hotel', 'pricingOption', 'routeSegment'].includes(kind)) return result;
  const collectionPath: Record<string, string[]> = {
    day: ['itinerary', 'days'],
    hotel: ['stays', 'hotels'],
    pricingOption: ['pricing', 'options'],
    routeSegment: ['route', 'staySegments'],
  };
  const records = recordsAt(document, collectionPath[kind]);
  const index = token === 'index' && /^\d+$/.test(fallbackIndex ?? '')
    ? Number(fallbackIndex)
    : findRecordIndex(records, token ?? '');
  if (index < 0 || index >= records.length) return result;
  const record = records[index];
  const id = record && typeof record === 'object' && typeof (record as JsonRecord).id === 'string'
    ? (record as JsonRecord).id as string
    : undefined;
  result.focus = { kind: kind as ResolvedFocus['kind'], index, id };
  return result;
}
