'use client';

import { useCallback, useMemo } from 'react';
import useSWR from 'swr';
import type { BrandRenderProfile } from '../../display/types';
import { quotationFetch } from '../../lib/apiError';
import { serializeFactsForApi, type QuotationFacts, type QuotationOptions, type ResolvedFacts } from './factsTypes';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';
export type ContentCandidate = Record<string, unknown>;
export type ContentEditorField = { id: string; label: string; path: Array<string | number>; control: 'input' | 'textarea' | 'string-list'; required: boolean; minLength: number; maxLength: number };
export type ContentFactInput = { id: string; label: string; path: Array<string | number>; required: boolean };
export type ContentEditor = { owner: 'fact' | 'fact-derived' | 'content' | 'design'; generation: boolean; editor: 'narrative' | 'fact-preview' | 'checklist'; recipeVersion: string; schemaVersion: string; fields: ContentEditorField[]; factInputs: ContentFactInput[]; defaultInstructions: { storytelling: string; detailed: string } | null };
export type ContentDraft = { id: string; scope: string; generationMode: 'storytelling' | 'detailed' | 'manual'; status: 'draft' | 'applied' | 'discarded' | 'stale'; candidate: ContentCandidate; missingInputs: Array<{ path: string; reason: string }>; generation: { cached?: boolean; latencyMs?: number; warnings?: string[]; llmCalled?: boolean; generationStatus?: string; instructionSource?: 'default' | 'custom' | 'manual' }; sourceDocumentRevision: number; factsSnapshot: { trip?: { title?: string; destinations?: string[] }; itineraryDay?: { destination?: string; summary?: string } }; editor?: ContentEditor };
export type FactsResponse = { facts: QuotationFacts; resolvedFacts: ResolvedFacts; source: { kind?: string; opportunityId?: string | null; snapshotAt?: string | null }; baselineLang: 'en' | 'vi' | 'ar' };
export type EditableHandoff = {
  stage: 'facts' | 'content';
  section: string;
  anchor?: string;
  item?: 'day' | 'hotel' | 'pricingOption' | 'bookingTerm' | 'routeSegment';
  indexFromSource?: number;
};

export type EditableBrochureContract = {
  version: number;
  id: string;
  fields: Array<{
    fieldId: string;
    section: string;
    owner: 'design' | 'content' | 'fact' | 'fact-derived' | 'system';
    kind: 'text' | 'richText' | 'aria' | 'altText' | 'image' | 'gallery';
    requiredForPublish: boolean;
    defaultStrategy: string;
    source: string;
    editMode: 'inspector' | 'handoff' | 'readonly';
    inspectorControl: 'text' | 'textarea' | 'none';
    editorSurface?: 'design-inspector';
    handoff?: EditableHandoff;
    handoffStage?: EditableHandoff['stage'];
    handoffSection?: string;
  }>;
  mediaSlotRegistry?: Array<{ fieldTemplate: string; source: string; editorRoute: string; pickerContext: 'library' | 'destination' | 'accommodation' | 'team'; minItems: number; maxItems: number; requiredForPublish: boolean; layoutVariants?: string[]; keys?: string[] }>;
};
export type DocumentResponse = { currentRevision: number; document: Record<string, unknown>; brandProfile: BrandRenderProfile; editableContract?: EditableBrochureContract; contentRegistry?: Record<string, ContentEditor>; contentEditorState?: Record<string, ContentCandidate> };
export type DraftsResponse = { drafts: ContentDraft[] };
export type ContentBlocker = { sectionId: string; sectionType: string; path: string; message: string };
export type ContentReadiness = { sectionId: string; sectionType: string; label: string; status: 'chua_du_noi_dung' | 'can_thong_tin' | null; missing: Array<{ path: string; message: string }>; targetStage: 'facts' | 'content' | null; generator: boolean };
export type WorkflowResponse = { locale: string; currentRevision: number; facts: { ready: boolean; missingInputs: string[] }; content: { ready: boolean; blockingDrafts: string[]; contentBlockers: ContentBlocker[]; generationOptional: boolean }; design: { ready: boolean; presentationErrors: string[] }; review: { ready: boolean; blockers: string[] } };
export type BrandResponse = { brands: Array<{ id: string; displayName: string; hostname: string; status: 'active' | 'disabled'; renderProfile: BrandRenderProfile }> };
export type ReviewResponse = { ready: boolean; missingInputs: string[]; blockingDrafts: string[]; contentBlockers?: ContentBlocker[]; contentReadiness?: ContentReadiness[]; presentationErrors?: string[]; assetReadiness?: { ready: boolean; missing: string[]; invalid: string[] } };
export type PublicationResponse = { publications: Array<{ targetId: string; brandId: string; hostname: string; locale: string; slug: string; fallbackUrl: string; status: string; release?: { number: number } | null; releases: Array<{ number: number; status: string; isCurrent: boolean; job?: { type: string; status: string; attempts: number; maxAttempts: number; lastError: string | null } | null }> }> };

const getJson = <T,>(url: string) => quotationFetch<T>(url, undefined, 'The quotation could not be loaded.');

export function useQuotationWorkspace(quotationId: string, lang: string) {
  const urls = useMemo(() => ({
    facts: `${API_BASE}/api/v2/quotations/${quotationId}/facts`,
    document: `${API_BASE}/api/v2/quotations/${quotationId}/document?lang=${encodeURIComponent(lang)}`,
    drafts: `${API_BASE}/api/v2/quotations/${quotationId}/content-drafts?lang=${encodeURIComponent(lang)}`,
    review: `${API_BASE}/api/v2/quotations/${quotationId}/review-status?lang=${encodeURIComponent(lang)}`,
    workflow: `${API_BASE}/api/v2/quotations/${quotationId}/workflow?lang=${encodeURIComponent(lang)}`,
    options: `${API_BASE}/api/v2/quotation-options`,
    brands: `${API_BASE}/api/v2/brands`,
    publications: `${API_BASE}/api/v2/quotations/${quotationId}/publications?lang=${encodeURIComponent(lang)}`,
  }), [lang, quotationId]);
  const facts = useSWR<FactsResponse>(urls.facts, getJson);
  const document = useSWR<DocumentResponse>(urls.document, getJson);
  const drafts = useSWR<DraftsResponse>(urls.drafts, getJson);
  const review = useSWR<ReviewResponse>(urls.review, getJson);
  const workflow = useSWR<WorkflowResponse>(urls.workflow, getJson);
  const options = useSWR<QuotationOptions>(urls.options, getJson);
  const brands = useSWR<BrandResponse>(urls.brands, getJson);
  const publications = useSWR<PublicationResponse>(urls.publications, getJson);
  const refresh = useCallback(async () => {
    await Promise.all([facts.mutate(), document.mutate(), drafts.mutate(), review.mutate(), workflow.mutate(), brands.mutate(), publications.mutate()]);
  }, [brands, document, drafts, facts, publications, review, workflow]);
  const saveFacts = useCallback(async (value: QuotationFacts) => {
    if (!document.data) throw new Error('The current document revision is not loaded.');
    await quotationFetch(`${urls.facts}?baseRevision=${document.data.currentRevision}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(serializeFactsForApi(value)) }, 'Facts could not be saved.');
    await refresh();
  }, [document.data, refresh, urls.facts]);
  const savePresentation = useCallback(async (input: { themeId: 'brochure'; layoutVersion: 1 }) => {
    if (!document.data) throw new Error('The current document revision is not loaded.');
    await quotationFetch(`${API_BASE}/api/v2/quotations/${quotationId}/presentation?lang=${encodeURIComponent(lang)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...input, baseRevision: document.data.currentRevision }) }, 'Presentation choices could not be saved.');
    await refresh();
  }, [document.data, lang, quotationId, refresh]);
  const request = useCallback(<T,>(path: string, init?: RequestInit, fallback?: string) => quotationFetch<T>(`${API_BASE}${path}`, init, fallback), []);
  return { urls, facts, document, drafts, review, workflow, options, brands, publications, refresh, saveFacts, savePresentation, request };
}
