"use client";

import dynamic from "next/dynamic";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useTransition,
  type CSSProperties,
  type SetStateAction,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ClipboardList,
  PenLine,
  Palette,
  Rocket,
  Lock,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import FactsForm from "./FactsForm";
import {
  hydrateDestinationRefs,
  type QuotationFacts,
} from "./factsTypes";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import { buildDisplayDocumentFromQuoteDocument } from "../../display/runtimePageBuilder";
import type { ViewMode } from "../../display/contracts";
import { useQuotationWorkspace } from "./useQuotationWorkspace";
import { useToast } from "../staff-workspace/ToastProvider";
import {
  parseFactsDeepLink,
  serializeFactsFocus,
  type ResolvedHandoff,
} from "./editableHandoff";

const ContentStudioClient = dynamic(
  () => import("../content-studio/ContentStudioClient"),
  {
    loading: () => (
      <div className="workspace-skeleton">
        <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
        <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
      </div>
    ),
  }
);
const DesignCanvas = dynamic(() => import("./DesignCanvas"), {
  loading: () => (
    <div className="workspace-skeleton">
      <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
    </div>
  ),
});
const PublicationTargetManager = dynamic(
  () => import("./PublicationTargetManager")
);
const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
const stages = ["facts", "content", "design", "review"] as const;
type Stage = (typeof stages)[number];

const stageIcons: Record<Stage, React.ComponentType<{ size?: number; className?: string }>> = {
  facts: ClipboardList,
  content: PenLine,
  design: Palette,
  review: Rocket,
};

export default function QuotationWorkspaceClient({
  quotationId,
  lang,
}: {
  quotationId: string;
  lang: string;
}) {
  const router = useRouter();
  const search = useSearchParams();
  const initialStage = search.get("stage");
  const [stage, setStage] = useState<Stage>(
    stages.includes(initialStage as Stage) ? (initialStage as Stage) : "facts"
  );
  const { toast } = useToast();
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);
  const [fallbackUrl, setFallbackUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [publicationBrandId, setPublicationBrandId] = useState<string | null>(
    null
  );
  const [previewMode] = useState<ViewMode>("desktop");
  const [editableFacts, setEditableFacts] = useState<QuotationFacts | null>(
    null
  );
  const [pending, startTransition] = useTransition();
  const workspace = useQuotationWorkspace(quotationId, lang);
  const refreshWorkspace = workspace.refresh;
  const { data: factsData } = workspace.facts;
  const { data: documentData } = workspace.document;
  const { data: reviewData } = workspace.review;
  const { data: workflowData } = workspace.workflow;
  const { data: options } = workspace.options;
  const { data: brandsResponse } = workspace.brands;
  const factsDeepLink = useMemo(
    () =>
      parseFactsDeepLink(
        search.get("factsSection"),
        search.get("focus"),
        documentData?.document,
      ),
    [documentData?.document, search],
  );
  const [publicationJob, setPublicationJob] = useState<{
    id: string;
    status: string;
    lastError: string | null;
  } | null>(null);
  const contentReady = workflowData?.content.ready ?? false;
  const reviewReady = workflowData?.review.ready ?? false;
  const loadError =
    workspace.facts.error ??
    workspace.document.error ??
    workspace.workflow.error ??
    workspace.options.error ??
    workspace.brands.error;

  useEffect(() => {
    if (!factsData?.baselineLang || factsData.baselineLang === lang) return;
    const params = new URLSearchParams(search.toString());
    params.set("lang", factsData.baselineLang);
    router.replace(`/quotations/${quotationId}/workspace?${params.toString()}`);
  }, [factsData?.baselineLang, lang, quotationId, router, search]);

  const selectedBrandId =
    publicationBrandId ?? documentData?.brandProfile.id ?? "";
  const previewProfile =
    brandsResponse?.brands.find((brand) => brand.id === selectedBrandId)
      ?.renderProfile ?? documentData?.brandProfile;
  const liveDocumentModel = useMemo(
    () =>
      documentData && previewProfile
        ? buildDisplayDocumentFromQuoteDocument({
            document: documentData.document,
            brandProfile: previewProfile,
            lang: lang as "en" | "vi" | "ar",
            viewMode: previewMode,
          })
        : null,
    [documentData, lang, previewMode, previewProfile]
  );

  const goTo = useCallback(
    (next: Stage) => {
      const allowed = next === "review" ? reviewReady : true;
      if (!allowed) {
        toast(
          next === "review"
            ? "Resolve the server-reported review blockers before publishing."
            : "Resolve the server-reported blockers before continuing.",
          "error"
        );
        return;
      }
      setStage(next);
    },
    [reviewReady, toast]
  );

  function saveFacts(facts: QuotationFacts) {
    startTransition(async () => {
      try {
        await workspace.saveFacts(facts);
        toast("Facts saved. Existing content candidates re-evaluated.", "success");
        setEditableFacts(null);
        setStage("content");
      } catch (error) {
        toast(apiErrorMessage(error), "error");
      }
    });
  }

  function savePresentation() {
    startTransition(async () => {
      try {
        await workspace.savePresentation({
          themeId: "brochure",
          layoutVersion: 1,
        });
        toast("Presentation choices saved.", "success");
        setEditableFacts(null);
      } catch (error) {
        toast(apiErrorMessage(error), "error");
      }
    });
  }

  function publish() {
    if (!documentData || !reviewReady) return;
    startTransition(async () => {
      let payload: {
        published_url?: string;
        fallback_url?: string;
        pdfUrl?: string;
        jobId?: string;
        status?: string;
        version?: number;
      };
      try {
        payload = await quotationFetch(
          `${API_BASE}/api/v2/quotations/${quotationId}/publish?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              baseRevision: documentData.currentRevision,
              brandId: selectedBrandId || undefined,
            }),
          },
          "Publish failed."
        );
      } catch (error) {
        toast(apiErrorMessage(error), "error");
        return;
      }
      setPublishedUrl(payload.published_url ?? null);
      setFallbackUrl(payload.fallback_url ?? null);
      setPdfUrl(payload.pdfUrl ?? null);
      setPublicationJob({
        id: payload.jobId ?? '',
        status: payload.status ?? "queued",
        lastError: null,
      });
      await workspace.refresh();
      toast(
        payload.status === "queued"
          ? "Publication queued while PDF renders."
          : `Published version ${payload.version ?? ""}.`,
        "success"
      );
    });
  }

  useEffect(() => {
    if (!publicationJob?.id || !['queued', 'running'].includes(publicationJob.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const job = await quotationFetch<{ id: string; status: string; lastError: string | null }>(
          `${API_BASE}/api/v2/publication-jobs/${publicationJob.id}`,
          undefined,
          'Unable to refresh publication status.',
        );
        setPublicationJob(job);
        if (job.status === 'succeeded') await refreshWorkspace();
      } catch (error) {
        setPublicationJob((current) => current ? { ...current, status: 'failed', lastError: apiErrorMessage(error) } : current);
      }
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [publicationJob, refreshWorkspace]);

  const labels: Record<Stage, string> = {
    facts: "Facts",
    content: "Content",
    design: "Design",
    review: "Review & Publish",
  };

  const isLocked = (item: Stage) => item === "review" ? !reviewReady : false;

  const isComplete = (item: Stage) => {
    if (item === "facts") return contentReady;
    if (item === "content") return contentReady;
    if (item === "design") return reviewReady;
    if (item === "review") return reviewReady && (publishedUrl !== null || (workspace.publications.data?.publications ?? []).length > 0);
    return false;
  };

  const editable = factsData?.source?.kind === "manual";

  const activeFacts =
    editableFacts ??
    (factsData?.facts
      ? hydrateDestinationRefs(factsData.facts, factsData.resolvedFacts)
      : undefined);

  const updateEditableFacts = useCallback(
    (next: SetStateAction<QuotationFacts>) => {
      setEditableFacts((previous) => {
        const current =
          previous ??
          (factsData?.facts
            ? hydrateDestinationRefs(factsData.facts, factsData.resolvedFacts)
            : undefined);
        if (!current) return previous;
        return typeof next === "function" ? next(current) : next;
      });
    },
    [factsData]
  );

  const navigateHandoff = useCallback(
    (target: ResolvedHandoff) => {
      const params = new URLSearchParams(search.toString());
      params.set("stage", target.stage);
      if (target.stage === "facts") {
        params.delete("section");
        params.set("factsSection", target.section);
        const focus = serializeFactsFocus(target.focus);
        if (focus) params.set("focus", focus);
        else params.delete("focus");
      } else {
        params.delete("factsSection");
        params.delete("focus");
        let section = target.section;
        if (target.focus?.kind === "day") {
          const days = ((documentData?.document.itinerary as { days?: Array<{ dayNumber?: number }> } | undefined)?.days ?? []);
          const dayNumber = days[target.focus.index]?.dayNumber;
          if (typeof dayNumber === "number") section = `itinerary:day:${dayNumber}`;
        }
        params.set("section", section);
      }
      router.replace(`/quotations/${quotationId}/workspace?${params.toString()}`, { scroll: false });
      setStage(target.stage);
    },
    [documentData?.document, quotationId, router, search],
  );

  return (
    <div
      className="flex min-w-0 w-full flex-col gap-6"
      style={liveDocumentModel?.colors.appChrome.style as CSSProperties | undefined}
    >
      <header className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  getTypographyClassName("overline"),
                  "text-[var(--color-accent)]"
                )}
              >
                Quotation Studio
              </span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-[var(--color-muted)]"
                )}
              >
                {editable ? "Manual Snapshot" : "DMC Core Snapshot"}
              </span>
              {factsData?.baselineLang ? (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-full border border-[var(--color-border)] bg-[var(--color-accent-wash)] px-2.5 py-0.5 text-[var(--color-accent)]"
                  )}
                >
                  {lang.toUpperCase()}
                </span>
              ) : null}
            </div>
            <h1
              className={cn(
                getTypographyClassName("pageTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {quotationId}
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                void workspace
                  .refresh()
                  .then(() => toast("Latest quotation revision loaded.", "info"))
                  .catch((error) => toast(apiErrorMessage(error), "error"));
              }}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex items-center gap-2 min-h-11 rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white hover:opacity-90 px-4 shadow-2xs transition-all"
              )}
            >
              <RefreshCw size={14} aria-hidden="true" />
              <span>Refresh latest revision</span>
            </button>
          </div>
        </div>

        {/* Stepper Navigation */}
        <nav
          className="workspace-stepper border-t border-[var(--color-border)] pt-4"
          aria-label="Workspace stages"
        >
          {stages.map((item, index) => {
            const Icon = stageIcons[item];
            const locked = isLocked(item);
            const complete = isComplete(item);
            const current = stage === item;

            return (
              <div
                key={item}
                className="contents"
              >
                {index > 0 ? (
                  <div
                    className={cn(
                      "workspace-stepper__connector",
                      isComplete(stages[index - 1]) && "workspace-stepper__connector--done"
                    )}
                    aria-hidden="true"
                  />
                ) : null}
                <button
                  type="button"
                  onClick={() => goTo(item)}
                  aria-current={current ? "step" : undefined}
                  aria-disabled={locked}
                  className={cn(
                    "workspace-stepper__step",
                    current && "workspace-stepper__step--current",
                    complete && "workspace-stepper__step--complete",
                    locked && "workspace-stepper__step--locked"
                  )}
                  title={locked ? "Resolve previous stages first" : undefined}
                >
                  <span className="workspace-stepper__circle">
                    {complete ? (
                      <CheckCircle2 size={16} aria-hidden="true" />
                    ) : locked ? (
                      <Lock size={14} aria-hidden="true" />
                    ) : (
                      <Icon size={16} aria-hidden="true" />
                    )}
                  </span>
                  <span className="workspace-stepper__label">
                    <span className={cn(getTypographyClassName("buttonSecondary"))}>
                      {labels[item]}
                    </span>
                  </span>
                </button>
              </div>
            );
          })}
        </nav>
      </header>

      <section className="flex flex-col gap-6 min-w-0 w-full">
        {stage === "facts" && factsData?.facts && activeFacts && options ? (
          <>
          <FactsForm
            facts={activeFacts}
            options={options}
            resolvedFacts={factsData.resolvedFacts}
            readOnly={!editable}
            allowSubmitWhenReadOnly={!editable}
            sourceNote={
              editable
                ? "Manual quotation · changes create a new fact revision and stale older candidates."
                : `DMC Core owns this snapshot${
                    factsData?.source?.opportunityId
                      ? ` · ${factsData.source.opportunityId}`
                      : ""
                  }${
                    factsData?.source?.snapshotAt
                      ? ` · ${factsData.source.snapshotAt}`
                      : ""
                  }.`
            }
            onChange={updateEditableFacts}
            onSubmit={() =>
              editable ? saveFacts(activeFacts) : savePresentation()
            }
            pending={pending}
            deepLink={factsDeepLink}
            mediaWorkspace={documentData ? { quotationId, lang, document: documentData.document, currentRevision: documentData.currentRevision, contract: documentData.editableContract, onSaved: workspace.refresh } : undefined}
            onDesignerSelected={documentData ? async (designerProfileId) => {
              await workspace.request(`/api/v2/quotations/${quotationId}/facts/designer?lang=${encodeURIComponent(lang)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ baseRevision: documentData.currentRevision, designerProfileId }) }, "Travel Designer could not be assigned.");
              await workspace.refresh();
            } : undefined}
            submitLabel={
              editable
                ? "Save facts & prepare content"
                : "Save presentation choices"
            }
          />
          </>
        ) : stage === "facts" ? (
          <div className="workspace-skeleton">
            <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
            <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
          </div>
        ) : null}

        {loadError ? (
          <div
            role="alert"
            className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4"
          >
            <p
              className={cn(
                getTypographyClassName("bodyMd"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {apiErrorMessage(loadError)}
            </p>
            <button
              type="button"
              onClick={() => {
                void workspace.refresh();
              }}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 text-[var(--color-muted)] transition-all hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-on-surface)]"
              )}
            >
              Retry loading
            </button>
          </div>
        ) : null}

        {stage === "content" ? (
          <ContentStudioClient
            quotationId={quotationId}
            lang={lang}
            onEditFacts={(section) => {
              const params = new URLSearchParams(search.toString());
              params.set("stage", "facts");
              params.delete("section");
              params.delete("focus");
              params.set("factsSection", section === "booking_terms" ? "seller" : section === "inclusions_exclusions" ? "services" : "trip");
              router.replace(`/quotations/${quotationId}/workspace?${params.toString()}`, { scroll: false });
              setStage("facts");
            }}
            resources={{
              documentData,
              draftsData: workspace.drafts.data,
              factsData,
              reviewData,
              refresh: workspace.refresh,
              request: workspace.request,
            }}
          />
        ) : null}

        {stage === "design" && documentData ? (
          <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <p
              className={cn(
                getTypographyClassName("bodyMd"),
                "text-[var(--color-muted)]"
              )}
            >
              This preview reads the canonical brochure document. Only applied
              content is visible.
            </p>
            {liveDocumentModel ? <DesignCanvas quotationId={quotationId} lang={lang} model={liveDocumentModel} document={documentData.document} currentRevision={documentData.currentRevision} contract={documentData.editableContract} onSaved={() => workspace.refresh()} onHandoff={navigateHandoff} /> : null}
          </div>
        ) : null}

        {stage === "review" && !reviewReady ? (
          <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
            <div className="flex items-start gap-3">
              <AlertCircle size={24} className="mt-0.5 text-[var(--color-accent-alt)] shrink-0" aria-hidden="true" />
              <div className="flex flex-col gap-1">
                <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
                  Quotation is not ready for review
                </h2>
                <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
                  Resolve the remaining factual or content-review checks before reviewing and publishing.
                </p>
              </div>
            </div>
            {reviewData?.missingInputs.length || reviewData?.blockingDrafts.length ? (
              <div className="rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 flex flex-col gap-2">
                <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                  Blockers to resolve:
                </span>
                <ul className={cn(getTypographyClassName("bodySm"), "list-disc list-inside text-[var(--color-muted)] flex flex-col gap-1")}>
                  {reviewData.missingInputs.length ? (
                    <li>Missing facts: {reviewData.missingInputs.join(", ")}</li>
                  ) : null}
                  {reviewData.blockingDrafts.length ? (
                    <li>Content requiring review: {reviewData.blockingDrafts.join(", ")}</li>
                  ) : null}
                </ul>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => goTo("facts")}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white hover:opacity-90 px-4 py-2.5 shadow-2xs transition-all"
                )}
              >
                Edit Facts
              </button>
              <button
                type="button"
                onClick={() => goTo("content")}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 py-2.5 shadow-xs transition-all"
                )}
              >
                Review Content Candidates
              </button>
            </div>
          </div>
        ) : null}

        {stage === "review" && reviewReady ? (
          <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <p
              className={cn(
                getTypographyClassName("bodyMd"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {reviewData?.ready
                ? "The canonical document is ready for review and publish."
                : "Resolve the remaining factual or content-review checks before publishing."}
            </p>
            {reviewData?.missingInputs.length ||
            reviewData?.blockingDrafts.length ? (
              <ul
                className={cn(
                  getTypographyClassName("bodySm"),
                  "text-[var(--color-muted)]"
                )}
              >
                <li>
                  Missing facts: {reviewData.missingInputs.join(", ") || "none"}
                </li>
                <li>
                  Content to review:{" "}
                  {reviewData.blockingDrafts.join(", ") || "none"}
                </li>
              </ul>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={publish}
                disabled={pending || !reviewReady || !selectedBrandId}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-6 shadow-md border border-transparent transition-all disabled:opacity-50"
                )}
              >
                {pending ? "Publishing…" : "Publish quotation"}
              </button>
            </div>
            <PublicationTargetManager
              quotationId={quotationId}
              brandId={selectedBrandId}
              onBrandChange={setPublicationBrandId}
              brandsData={brandsResponse}
              publications={workspace.publications.data}
              refresh={workspace.refresh}
            />
            {publishedUrl ? publicationJob?.status === 'succeeded' ? <a href={publishedUrl} target="_blank" rel="noreferrer" className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>Canonical URL</a> : <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Canonical URL · Preparing</span> : null}
            {fallbackUrl ? publicationJob?.status === 'succeeded' ? <a href={fallbackUrl} target="_blank" rel="noreferrer" className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>Customer fallback URL</a> : <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Customer fallback URL · Preparing</span> : null}
            {publicationJob ? (
              <p
                className={cn(
                  getTypographyClassName("bodySm"),
                  "text-[var(--color-muted)]"
                )}
              >
                Publication job: {publicationJob.status}
                {publicationJob.lastError
                  ? ` · ${publicationJob.lastError}`
                  : ""}
              </p>
            ) : null}
            {pdfUrl ? (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "text-[var(--color-accent)]"
                )}
              >
                Download PDF
              </a>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
