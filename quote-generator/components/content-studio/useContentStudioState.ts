'use client';

import { useCallback, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getDefaultMealsForLang } from '../../lib/prefillRules.ts';
import { contentReconciler } from '../../lib/rules/contentReconciler.ts';
import type {
  ContentCandidate,
  ContentDraft,
  DocumentResponse,
  DraftsResponse,
  FactsResponse,
  ReviewResponse,
} from '../quotation-workspace/useQuotationWorkspace.ts';

export type Mode = 'storytelling' | 'detailed';

export const labels: Record<string, string> = {
  hero: 'Hero',
  overview_letter: 'Overview letter',
  route_map: 'Route map',
  itinerary: 'Itinerary',
  hotel_plan: 'Hotel plan',
  pricing: 'Pricing',
  inclusions_exclusions: 'Inclusions & exclusions',
  booking_terms: 'Booking & payment terms',
  designer: 'Designer',
};

export const SCOPE_BY_SECTION_TYPE: Record<string, string> = {
  route_map: 'route',
};

export type UseContentStudioStateOptions = {
  quotationId: string;
  lang: string;
  resources: {
    documentData?: DocumentResponse;
    draftsData?: DraftsResponse;
    factsData?: FactsResponse;
    reviewData?: ReviewResponse;
  };
};

export function useContentStudioState({
  lang,
  resources,
}: UseContentStudioStateOptions) {
  const router = useRouter();
  const search = useSearchParams();

  const [mode, setMode] = useState<Mode>('storytelling');
  const [customInstruction, setCustomInstructionState] = useState<{
    scope: string;
    mode: Mode;
    value: string;
  } | null>(null);
  const [localCandidate, setLocalCandidate] = useState<{
    scope: string;
    candidate: ContentCandidate;
  } | null>(null);
  const [generatedDraft, setGeneratedDraft] = useState<ContentDraft | null>(
    null
  );

  const readiness = useMemo(
    () =>
      (resources.reviewData?.contentReadiness ?? []).flatMap((item) => {
        if (item.sectionType !== 'itinerary') return [item];
        const days = resources.factsData?.facts?.trip_facts?.itinerary ?? [];
        return [
          item,
          ...days.map((day, index) => {
            const dayNumber = day.day_number ?? index + 1;
            const sourceFactId = day.id ?? String(dayNumber);
            return {
              ...item,
              sectionId: `itinerary:day:${sourceFactId}`,
              label: `Day ${dayNumber}${
                day.destination ? ` · ${day.destination}` : ''
              }`,
              missing: [],
              generator: item.targetStage !== 'facts',
            };
          }),
        ];
      }),
    [resources.factsData, resources.reviewData?.contentReadiness]
  );

  const selectedId = search.get('section') ?? readiness[0]?.sectionId ?? '';
  const selected =
    readiness.find((item) => item.sectionId === selectedId) ?? readiness[0];
  const scope = selected?.sectionId.startsWith('itinerary:day:')
    ? selected.sectionId
    : selected
    ? SCOPE_BY_SECTION_TYPE[selected.sectionType] ?? selected.sectionType
    : null;

  const editor = scope
    ? resources.documentData?.contentRegistry?.[scope]
    : undefined;
  // `fact-derived` sections are deterministic projections of Facts as well.
  // They must not expose a Content Studio save/apply path.
  const factOwned = Boolean(editor && editor.owner !== 'content');

  const persistedDraft = useMemo(
    () =>
      scope
        ? (resources.draftsData?.drafts ?? []).find(
            (item) => item.scope === scope && item.status === 'draft'
          )
        : undefined,
    [resources.draftsData, scope]
  );

  const draft =
    generatedDraft?.scope === scope && generatedDraft.status === 'draft'
      ? generatedDraft
      : persistedDraft;

  const canonicalCandidate = useMemo(() => {
    if (!scope) return undefined;
    const raw = resources.documentData?.contentEditorState?.[scope];
    const facts = resources.factsData?.facts;
    const fallback = contentReconciler.deriveDefaultCandidate(scope, facts, lang);
    const base = raw ?? fallback;
    return contentReconciler.reconcileCandidateWithFacts(scope, base, facts, lang);
  }, [lang, resources.documentData?.contentEditorState, resources.factsData?.facts, scope]);

  const workingCandidate = useMemo(() => {
    if (!scope) return undefined;
    const candidateSource =
      localCandidate?.scope === scope
        ? localCandidate.candidate
        : draft?.candidate ?? canonicalCandidate;
    if (!candidateSource) return undefined;
    const facts = resources.factsData?.facts;
    return contentReconciler.reconcileCandidateWithFacts(
      scope,
      candidateSource,
      facts,
      lang
    );
  }, [canonicalCandidate, draft?.candidate, lang, localCandidate, resources.factsData?.facts, scope]);

  const defaultInstruction = editor?.defaultInstructions?.[mode] ?? '';
  const activeCustomInstruction =
    customInstruction?.scope === scope && customInstruction.mode === mode
      ? customInstruction.value
      : null;
  const instruction = activeCustomInstruction ?? defaultInstruction;

  const setCustomInstruction = useCallback(
    (value: string | null) =>
      setCustomInstructionState(
        value === null || !scope ? null : { scope, mode, value }
      ),
    [mode, scope]
  );

  const setWorkingCandidate = useCallback(
    (candidate: ContentCandidate) => {
      if (scope) setLocalCandidate({ scope, candidate });
    },
    [scope]
  );

  const select = useCallback(
    (sectionId: string) => {
      const params = new URLSearchParams(search.toString());
      params.set('section', sectionId);
      router.replace(`?${params.toString()}`);
      setCustomInstructionState(null);
      setLocalCandidate(null);
      setGeneratedDraft(null);
    },
    [router, search]
  );

  const complete = readiness.filter((item) => item.status === null).length;
  const facts = resources.factsData?.facts as unknown as
    | Record<string, unknown>
    | undefined;

  const factsForPanel = useMemo(() => {
    if (!facts) return facts;
    const tripFacts =
      (facts.trip_facts as Record<string, unknown> | undefined) ?? {};
    const resolvedFacts = resources.factsData?.resolvedFacts;
    const requestBrief = resources.factsData?.requestBrief;
    const normalizedFacts = {
      ...facts,
      ...(requestBrief && typeof requestBrief === 'object' && Object.keys(requestBrief).length > 0
        ? { request_brief: requestBrief }
        : {}),
      trip_facts: {
        ...tripFacts,
        duration_days:
          tripFacts.duration_days ?? resolvedFacts?.durationDays ?? null,
        duration_nights:
          tripFacts.duration_nights ?? resolvedFacts?.durationNights ?? null,
      },
    };
    if (!scope?.startsWith('itinerary:day:')) return normalizedFacts;
    const sourceFactId = scope.split(':').at(-1) ?? '';
    const days =
      (
        tripFacts as {
          itinerary?: Array<{
            id?: string;
            day_number?: number;
            destination?: string;
            summary?: string;
            highlights?: string[];
            meals?: string[];
            overnight?: string;
          }>;
        }
      ).itinerary ?? [];
    const day = days.find((item) => item.id === sourceFactId || String(item.day_number) === sourceFactId);
    return {
      ...normalizedFacts,
      itineraryDay: day
        ? {
            dayNumber: day.day_number ?? 0,
            sourceFactId,
            destination: day.destination ?? '',
            summary: day.summary ?? '',
            highlights: day.highlights ?? [],
            meals: day.meals?.length
              ? day.meals
              : getDefaultMealsForLang(lang as 'en' | 'vi' | 'ar'),
            overnight: day.overnight ?? '',
          }
        : {},
    };
  }, [facts, lang, resources.factsData?.requestBrief, resources.factsData?.resolvedFacts, scope]);

  return {
    mode,
    setMode,
    readiness,
    selectedId,
    selected,
    scope,
    editor,
    factOwned,
    draft,
    generatedDraft,
    setGeneratedDraft,
    canonicalCandidate,
    workingCandidate,
    setWorkingCandidate,
    localCandidate,
    setLocalCandidate,
    instruction,
    activeCustomInstruction,
    setCustomInstruction,
    select,
    complete,
    facts,
    factsForPanel,
  };
}
