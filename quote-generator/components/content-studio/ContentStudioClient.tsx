'use client';

import { useCallback, useMemo, useState, useTransition } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getTypographyClassName } from '../../config/typography';
import { getLanguageLabels } from '../../display/labels';
import { cn } from '../../utils/cn';
import { apiErrorMessage } from '../../lib/apiError';
import { ContentDraftActions } from './ContentDraftActions';
import { ContentGenerationPanel, FactsUsed } from './ContentGenerationPanel';
import { cloneCandidate, SectionContentFields } from './SectionContentFields';
import type { ContentCandidate, ContentDraft, ContentFactInput, DocumentResponse, DraftsResponse, FactsResponse, ReviewResponse } from '../quotation-workspace/useQuotationWorkspace';

type Props = {
  quotationId: string;
  lang: string;
  onEditFacts?: (section?: string) => void;
  resources: {
    documentData?: DocumentResponse;
    draftsData?: DraftsResponse;
    factsData?: FactsResponse;
    reviewData?: ReviewResponse;
    refresh: () => Promise<unknown>;
    request: <T>(path: string, init?: RequestInit, fallback?: string) => Promise<T>;
  };
};
type Mode = 'storytelling' | 'detailed';

const labels: Record<string, string> = {
  hero: 'Hero', overview_letter: 'Overview letter', route_map: 'Route map', itinerary: 'Itinerary',
  hotel_plan: 'Hotel plan', pricing: 'Pricing', inclusions_exclusions: 'Inclusions & exclusions',
  booking_terms: 'Booking & payment terms', designer: 'Designer', finalization: 'Final details',
};

function defaultRouteCandidate(candidate: ContentCandidate | undefined, lang: string): ContentCandidate | undefined {
  if (!candidate) return candidate;
  const route = candidate.route;
  if (!route || typeof route !== 'object') return candidate;
  const language = lang === 'vi' || lang === 'ar' ? lang : 'en';
  const copy = getLanguageLabels(language);
  const routeValues = route as Record<string, unknown>;
  const title = typeof routeValues.title === 'string' ? routeValues.title.trim() : '';
  const description = typeof routeValues.description === 'string' ? routeValues.description.trim() : '';
  if (title && description) return candidate;
  return { ...candidate, route: { ...routeValues, title: title || copy.routeMapTitle, description: description || copy.routeMapDescription } };
}

function FactOwnedPreview({ sectionType, document }: { sectionType: string; document?: Record<string, unknown> }) {
  const content = document?.content as { sections?: Record<string, { blocks?: Array<Record<string, unknown>> }> } | undefined;
  const key = sectionType === 'inclusions_exclusions' ? 'inclusions_exclusions' : sectionType === 'booking_terms' ? 'booking_terms' : '';
  const blocks = content?.sections?.[key]?.blocks ?? [];
  if (sectionType === 'inclusions_exclusions') {
    const block = blocks.find((item) => item.type === 'twoColumnList');
    return <div className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] p-4 sm:grid-cols-2"><div><p className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Included</p><ul className={cn(getTypographyClassName('bodySm'), 'mt-2 grid gap-1 text-[var(--color-on-surface)]')}>{Array.isArray(block?.leftItems) ? block.leftItems.map((item, index) => <li key={index}>{String(item)}</li>) : null}</ul></div><div><p className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Not included</p><ul className={cn(getTypographyClassName('bodySm'), 'mt-2 grid gap-1 text-[var(--color-on-surface)]')}>{Array.isArray(block?.rightItems) ? block.rightItems.map((item, index) => <li key={index}>{String(item)}</li>) : null}</ul></div></div>;
  }
  if (sectionType === 'booking_terms') return <div className="grid gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] p-4">{blocks.map((block, index) => <p key={index} className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-on-surface)]')}>{String(block.text ?? block.body ?? '')}</p>)}</div>;
  return <p className={cn(getTypographyClassName('bodySm'), 'rounded-[var(--radius-card)] border border-[var(--color-border)] p-4 text-[var(--color-muted)]')}>This fixed brochure layout is sourced from approved Facts.</p>;
}

function ContentContractUnavailable({ onRetry }: { onRetry: () => void }) {
  return <div role="alert" className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4"><div><h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Content workspace is unavailable</h3><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>The document response is missing the Content editor contract. Fields cannot be safely guessed because the registry is their source of truth.</p></div><button type="button" onClick={onRetry} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2')}>Retry loading workspace</button></div>;
}

function DeterministicFactsPanel({ factInputs, facts }: { factInputs: ContentFactInput[]; facts?: Record<string, unknown> }) {
  return <aside className="grid h-fit gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 xl:sticky xl:top-4"><div><h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Approved checklist</h3><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>This section is derived deterministically from approved Facts. It does not use AI generation.</p></div><FactsUsed factInputs={factInputs} facts={facts} /></aside>;
}

export default function ContentStudioClient({ quotationId, lang, onEditFacts, resources }: Props) {
  const router = useRouter();
  const search = useSearchParams();
  const [mode, setMode] = useState<Mode>('storytelling');
  const [customInstruction, setCustomInstructionState] = useState<{ scope: string; mode: Mode; value: string } | null>(null);
  const [localCandidate, setLocalCandidate] = useState<{ scope: string; candidate: ContentCandidate } | null>(null);
  const [generatedDraft, setGeneratedDraft] = useState<ContentDraft | null>(null);
  const [message, setMessage] = useState('Select a section to review its content.');
  const [pending, startTransition] = useTransition();

  const readiness = useMemo(() => (resources.reviewData?.contentReadiness ?? []).flatMap((item) => {
    if (item.sectionType !== 'itinerary') return [item];
    const days = resources.factsData?.facts.trip_facts.itinerary ?? [];
    return [item, ...days.map((day, index) => {
      const dayNumber = day.day_number ?? index + 1;
      return { ...item, sectionId: `itinerary:day:${dayNumber}`, label: `Day ${dayNumber}${day.destination ? ` · ${day.destination}` : ''}`, missing: [], generator: item.targetStage !== 'facts' };
    })];
  }), [resources.factsData, resources.reviewData?.contentReadiness]);
  const selectedId = search.get('section') ?? readiness[0]?.sectionId ?? '';
  const selected = readiness.find((item) => item.sectionId === selectedId) ?? readiness[0];
  const scopeBySectionType: Record<string, string> = { route_map: 'route' };
  const scope = selected?.sectionId.startsWith('itinerary:day:') ? selected.sectionId : selected ? (scopeBySectionType[selected.sectionType] ?? selected.sectionType) : null;
  const editor = scope ? resources.documentData?.contentRegistry?.[scope] : undefined;
  const factOwned = editor?.owner === 'fact';
  const persistedDraft = useMemo(() => scope ? (resources.draftsData?.drafts ?? []).find((item) => item.scope === scope && item.status === 'draft') : undefined, [resources.draftsData, scope]);
  const draft = generatedDraft?.scope === scope && generatedDraft.status === 'draft' ? generatedDraft : persistedDraft;
  const canonicalCandidate = useMemo(() => {
    const candidate = scope ? resources.documentData?.contentEditorState?.[scope] : undefined;
    return scope === 'route' ? defaultRouteCandidate(candidate, lang) : candidate;
  }, [lang, resources.documentData?.contentEditorState, scope]);
  const workingCandidate = localCandidate?.scope === scope ? localCandidate.candidate : draft?.candidate ?? canonicalCandidate;
  const defaultInstruction = editor?.defaultInstructions?.[mode] ?? '';
  const activeCustomInstruction = customInstruction?.scope === scope && customInstruction.mode === mode ? customInstruction.value : null;
  const instruction = activeCustomInstruction ?? defaultInstruction;
  const complete = readiness.filter((item) => item.status === null).length;
  const facts = resources.factsData?.facts as unknown as Record<string, unknown> | undefined;
  const factsForPanel = useMemo(() => {
    if (!facts) return facts;
    const tripFacts = (facts.trip_facts as Record<string, unknown> | undefined) ?? {};
    const resolvedFacts = resources.factsData?.resolvedFacts;
    const normalizedFacts = {
      ...facts,
      trip_facts: {
        ...tripFacts,
        duration_days: tripFacts.duration_days ?? resolvedFacts?.durationDays ?? null,
        duration_nights: tripFacts.duration_nights ?? resolvedFacts?.durationNights ?? null,
      },
    };
    if (!scope?.startsWith('itinerary:day:')) return normalizedFacts;
    const number = Number(scope.split(':').at(-1));
    const days = (tripFacts as { itinerary?: Array<{ day_number?: number; destination?: string; summary?: string; highlights?: string[]; meals?: string[]; overnight?: string }> }).itinerary ?? [];
    const day = days.find((item) => item.day_number === number);
    return {
      ...normalizedFacts,
      itineraryDay: day ? {
        dayNumber: number,
        destination: day.destination ?? '',
        summary: day.summary ?? '',
        highlights: day.highlights ?? [],
        meals: day.meals ?? [],
        overnight: day.overnight ?? '',
      } : {},
    };
  }, [facts, resources.factsData?.resolvedFacts, scope]);
  const hasContentContract = Boolean(resources.documentData?.contentRegistry && resources.documentData?.contentEditorState);

  const setCustomInstruction = useCallback((value: string | null) => setCustomInstructionState(value === null || !scope ? null : { scope, mode, value }), [mode, scope]);
  const setWorkingCandidate = useCallback((candidate: ContentCandidate) => { if (scope) setLocalCandidate({ scope, candidate }); }, [scope]);
  const select = (sectionId: string) => {
    const params = new URLSearchParams(search.toString());
    params.set('section', sectionId);
    router.replace(`?${params.toString()}`);
    setCustomInstructionState(null);
    setLocalCandidate(null);
    setGeneratedDraft(null);
  };
  const generate = useCallback(() => {
    if (!scope || !editor?.generation) return;
    startTransition(async () => {
      try {
        const response = await resources.request<{ draft: ContentDraft }>(`/api/v2/quotations/${quotationId}/content-drafts?lang=${encodeURIComponent(lang)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scope, generationMode: mode, instruction: activeCustomInstruction ?? '' }) });
        setGeneratedDraft(response.draft);
        setWorkingCandidate(cloneCandidate(response.draft.candidate));
        void resources.refresh();
        setMessage(response.draft.missingInputs.length ? 'Complete the required Facts before generating this draft.' : 'AI draft filled into the content fields. Review it before Apply.');
      } catch (error) { setMessage(apiErrorMessage(error)); }
    });
  }, [activeCustomInstruction, editor?.generation, lang, mode, quotationId, resources, scope, setWorkingCandidate]);
  const saveDraft = useCallback(() => {
    if (!scope || !workingCandidate) return;
    startTransition(async () => {
      try {
        const response = draft
          ? await resources.request<{ draft: ContentDraft }>(`/api/v2/quotations/${quotationId}/content-drafts/${draft.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate: workingCandidate }) })
          : await resources.request<{ draft: ContentDraft }>(`/api/v2/quotations/${quotationId}/content-drafts/manual?lang=${encodeURIComponent(lang)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scope, candidate: workingCandidate, baseRevision: resources.documentData?.currentRevision }) });
        setGeneratedDraft(response.draft);
        setWorkingCandidate(cloneCandidate(response.draft.candidate));
        void resources.refresh();
        setMessage('Draft saved. Apply it when the content is ready.');
      } catch (error) { setMessage(apiErrorMessage(error)); }
    });
  }, [draft, lang, quotationId, resources, scope, setWorkingCandidate, workingCandidate]);
  const apply = useCallback(() => {
    if (!draft || !workingCandidate) return;
    startTransition(async () => {
      try {
        const patched = await resources.request<{ draft: ContentDraft }>(`/api/v2/quotations/${quotationId}/content-drafts/${draft.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate: workingCandidate }) });
        await resources.request(`/api/v2/quotations/${quotationId}/content-drafts/${patched.draft.id}/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ baseRevision: resources.documentData?.currentRevision ?? draft.sourceDocumentRevision }) });
        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        setMessage('Content applied to the canonical brochure.');
      } catch (error) { setMessage(apiErrorMessage(error)); }
    });
  }, [draft, quotationId, resources, workingCandidate]);
  const discard = useCallback(() => {
    if (!draft) return;
    startTransition(async () => {
      try {
        await resources.request(`/api/v2/quotations/${quotationId}/content-drafts/${draft.id}/discard`, { method: 'POST' });
        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        setMessage('Draft discarded; canonical content remains unchanged.');
      } catch (error) { setMessage(apiErrorMessage(error)); }
    });
  }, [draft, quotationId, resources]);

  return <section className="grid min-w-0 gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]"><aside className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"><p className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>CONTENT STUDIO · {complete}/{readiness.length}</p><div className="mt-4 grid gap-1">{readiness.map((item) => <button key={item.sectionId} type="button" aria-current={selected?.sectionId === item.sectionId ? 'page' : undefined} onClick={() => select(item.sectionId)} className={cn(getTypographyClassName('bodySm'), 'min-h-11 rounded-[var(--radius-button)] px-3 py-2 text-left', selected?.sectionId === item.sectionId ? 'bg-[var(--color-accent-wash)] text-[var(--color-on-surface)]' : 'text-[var(--color-muted)]')}><span>{item.status === null ? '✓ ' : item.status === 'can_thong_tin' ? '! ' : '○ '}</span>{item.sectionId.startsWith('itinerary:day:') ? item.label : labels[item.sectionType] ?? item.label}</button>)}</div></aside><main className="min-w-0 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"><p aria-live="polite" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{message}</p>{selected ? <div className="mt-4 grid gap-5"><div><h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>{selected.label || labels[selected.sectionType]}</h2><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>Review and write brochure copy here. Facts and AI generation never publish automatically.</p></div>{selected.missing.map((item) => <p key={item.path} className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-accent-alt)]')}>{item.message}</p>)}{!hasContentContract ? <ContentContractUnavailable onRetry={() => { void resources.refresh(); }} /> : factOwned || selected.targetStage === 'facts' ? <><FactOwnedPreview sectionType={selected.sectionType} document={resources.documentData?.document} /><button type="button" onClick={() => onEditFacts?.(selected.sectionId)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2')}>Open approved Facts</button></> : workingCandidate && editor ? <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(20rem,0.85fr)]"><div className="grid gap-4"><SectionContentFields scope={scope ?? ''} fields={editor.fields} candidate={workingCandidate} onChange={setWorkingCandidate} /><ContentDraftActions hasDraft={Boolean(draft)} pending={pending} onSave={saveDraft} onApply={apply} onDiscard={discard} /></div>{editor.generation ? <ContentGenerationPanel mode={mode} onModeChange={setMode} instruction={instruction} defaultInstruction={defaultInstruction} onInstructionChange={setCustomInstruction} onRestoreDefault={() => setCustomInstruction(null)} factInputs={editor.factInputs} facts={factsForPanel} onGenerate={generate} pending={pending} disabled={selected?.status === 'can_thong_tin'} /> : <DeterministicFactsPanel factInputs={editor.factInputs} facts={factsForPanel} />}</div> : <ContentContractUnavailable onRetry={() => { void resources.refresh(); }} />}</div> : null}</main></section>;
}
