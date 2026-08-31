"use client";

import { type ReactNode, useState } from "react";
import { Loader2, X } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { useAiDrafter } from "./useAiDrafter.ts";
import { RoomConfigEditor, withRoomIds, stripRoomIds, type EditableRoomAllocation } from "./RoomConfigEditor.tsx";
import { TagListEditor } from "./TagListEditor.tsx";
import { DraftProgress } from "./DraftProgress.tsx";
import type {
  DraftDaySpec,
  DraftServicesResponse,
  TripArchetype,
  TripMobility,
  TripPace,
  TripProfile,
  TripQualityTier,
} from "../types.ts";

const ARCHETYPE_OPTIONS: TripArchetype[] = [
  "solo",
  "couple",
  "honeymoon",
  "family_with_young_kids",
  "family_with_teens",
  "multi_generation",
  "friends_group",
  "corporate_incentive",
];
const PACE_OPTIONS: TripPace[] = ["relaxed", "moderate", "packed"];
const MOBILITY_OPTIONS: TripMobility[] = ["full", "limited", "wheelchair"];
const QUALITY_TIER_OPTIONS: TripQualityTier[] = ["ultra_luxury", "luxury", "premium", "standard", "value"];

export interface TripProfileReviewDialogProps {
  sheetId: string;
  baseCostingRevision: number;
  days: DraftDaySpec[];
  onClose: () => void;
  onDraftComplete: (result: DraftServicesResponse) => void;
  onConflict?: () => void;
}

type Step = "input" | "review" | "progress";

const fieldInputClass = cn(
  getTypographyClassName("bodySm"),
  "h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)]",
);

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{label}</span>
      {children}
    </div>
  );
}

/**
 * Human-in-the-loop gate for the AI Service Drafter (15.7 §2). This dialog is the ONLY
 * place `draft()` may be called from — Analyze produces a `TripProfile` the sale must
 * review (and may edit) before "Run Drafter" is enabled, matching chốt #4 (no endpoint
 * that runs both agent tiers back-to-back without a human in between).
 */
export function TripProfileReviewDialog({
  sheetId,
  baseCostingRevision,
  days,
  onClose,
  onDraftComplete,
  onConflict,
}: TripProfileReviewDialogProps) {
  const { isAnalyzing, isDrafting, actionError, analyze, draft } = useAiDrafter(sheetId);
  const [step, setStep] = useState<Step>("input");
  const [rawText, setRawText] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [confidenceNotes, setConfidenceNotes] = useState<string[]>([]);

  const [archetype, setArchetype] = useState<TripArchetype>("couple");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [infants, setInfants] = useState(0);
  const [childAges, setChildAges] = useState<number[]>([]);
  const [rooms, setRooms] = useState<EditableRoomAllocation[]>([]);
  const [mobility, setMobility] = useState<TripMobility>("full");
  const [pace, setPace] = useState<TripPace>("moderate");
  const [dietary, setDietary] = useState<string[]>([]);
  const [qualityTier, setQualityTier] = useState<TripQualityTier>("luxury");
  const [guideNeed, setGuideNeed] = useState(true);
  const [guideLanguages, setGuideLanguages] = useState<string[]>([]);
  const [specialFlags, setSpecialFlags] = useState<string[]>([]);
  const [draftResult, setDraftResult] = useState<DraftServicesResponse | null>(null);

  const isBusy = isAnalyzing || isDrafting;

  const handleAnalyze = async () => {
    const result = await analyze(rawText);
    if (!result) return;
    const profile = result.trip_profile;
    setRunId(result.run_id);
    setFallbackUsed(result.fallback_used);
    setConfidenceNotes(result.confidence_notes);
    setArchetype(profile.archetype);
    setAdults(profile.party.adults);
    setChildren(profile.party.children);
    setInfants(profile.party.infants);
    setChildAges(profile.party.child_ages);
    setRooms(withRoomIds(profile.room_config));
    setMobility(profile.mobility);
    setPace(profile.pace);
    setDietary(profile.dietary);
    setQualityTier(profile.quality_tier);
    setGuideNeed(profile.guide_need);
    setGuideLanguages(profile.guide_languages);
    setSpecialFlags(profile.special_flags);
    setStep("review");
  };

  const handleRunDrafter = async () => {
    if (!runId) return;
    const tripProfile: TripProfile = {
      archetype,
      party: { adults, children, infants, child_ages: childAges },
      room_config: stripRoomIds(rooms),
      mobility,
      pace,
      dietary,
      quality_tier: qualityTier,
      guide_need: guideNeed,
      guide_languages: guideLanguages,
      special_flags: specialFlags,
      confidence_notes: confidenceNotes,
    };
    const result = await draft({ runId, tripProfile, days, baseCostingRevision }, onConflict);
    if (!result) return;
    setDraftResult(result);
    setStep("progress");
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
      onClick={(event) => {
        if (event.target === event.currentTarget && !isBusy) onClose();
      }}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-6 py-4">
          <div>
            <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>AI Service Drafter</h3>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              {step === "input" ? "Step 1 of 3 — Analyze customer prose" : null}
              {step === "review" ? "Step 2 of 3 — Review & confirm trip profile" : null}
              {step === "progress" ? "Step 3 of 3 — Draft outcome" : null}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isBusy}
            className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-on-surface)] cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Close"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {actionError ? (
            <div className={cn(getTypographyClassName("bodySm"), "mb-4 rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-3 py-2 text-rose-700")}>
              {actionError}
            </div>
          ) : null}

          {step === "input" ? (
            <div className="flex flex-col gap-3">
              <label className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                Paste the customer&apos;s raw itinerary request (any language)
              </label>
              <textarea
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                rows={10}
                className={cn(
                  getTypographyClassName("bodySm"),
                  "w-full resize-y rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-3 text-[var(--color-on-surface)]",
                )}
                placeholder="e.g. Family of 3 generations, 5 days Hanoi - Ha Long - Ninh Binh, grandmother has limited mobility..."
              />
            </div>
          ) : null}

          {step === "review" ? (
            <div className="flex flex-col gap-4">
              {fallbackUsed ? (
                <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-amber-300 bg-amber-50 px-3 py-2 text-amber-700")}>
                  Analysis fell back to a deterministic rooming heuristic — review every field carefully.
                </div>
              ) : null}

              {confidenceNotes.length > 0 ? (
                <div className={cn(getTypographyClassName("bodySm"), "flex flex-col gap-1 rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-3 py-2 text-rose-700")}>
                  <span className={getTypographyClassName("label")}>Confidence notes — confirm before drafting</span>
                  <ul className="list-disc pl-4">
                    {confidenceNotes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Field label="Archetype">
                  <select value={archetype} onChange={(event) => setArchetype(event.target.value as TripArchetype)} className={fieldInputClass}>
                    {ARCHETYPE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Adults">
                  <input
                    type="number"
                    min={1}
                    value={adults}
                    onChange={(event) => setAdults(Math.max(1, Number(event.target.value) || 1))}
                    className={fieldInputClass}
                  />
                </Field>
                <Field label="Children">
                  <input
                    type="number"
                    min={0}
                    value={children}
                    onChange={(event) => setChildren(Math.max(0, Number(event.target.value) || 0))}
                    className={fieldInputClass}
                  />
                </Field>
                <Field label="Infants">
                  <input
                    type="number"
                    min={0}
                    value={infants}
                    onChange={(event) => setInfants(Math.max(0, Number(event.target.value) || 0))}
                    className={fieldInputClass}
                  />
                </Field>
                <Field label="Pace">
                  <select value={pace} onChange={(event) => setPace(event.target.value as TripPace)} className={fieldInputClass}>
                    {PACE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Mobility">
                  <select value={mobility} onChange={(event) => setMobility(event.target.value as TripMobility)} className={fieldInputClass}>
                    {MOBILITY_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Quality tier">
                  <select value={qualityTier} onChange={(event) => setQualityTier(event.target.value as TripQualityTier)} className={fieldInputClass}>
                    {QUALITY_TIER_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Guide needed">
                  <label className="flex h-9 items-center gap-2">
                    <input type="checkbox" checked={guideNeed} onChange={(event) => setGuideNeed(event.target.checked)} />
                    <span className={getTypographyClassName("bodySm")}>{guideNeed ? "Yes" : "No"}</span>
                  </label>
                </Field>
              </div>

              <RoomConfigEditor rooms={rooms} onChange={setRooms} />

              {guideNeed ? (
                <TagListEditor label="Guide languages" values={guideLanguages} placeholder="e.g. English" onChange={setGuideLanguages} />
              ) : null}
              <TagListEditor label="Dietary" values={dietary} placeholder="e.g. vegetarian" onChange={setDietary} />

              {specialFlags.length > 0 ? (
                <div className="flex flex-col gap-1">
                  <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
                    Special flags (verbatim from customer text — not editable)
                  </span>
                  <ul className={cn(getTypographyClassName("bodySm"), "list-disc pl-4 text-[var(--color-on-surface)]")}>
                    {specialFlags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {days.length === 0 ? (
                <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-button)] border border-rose-300 bg-rose-50 px-3 py-2 text-rose-700")}>
                  No day/destination anchors available — cannot run the drafter until at least one day has a destination.
                </div>
              ) : (
                <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  Will draft {days.length} day(s): {days.map((day) => `Day ${day.dayNumber}`).join(", ")}.
                </p>
              )}
            </div>
          ) : null}

          {step === "progress" && draftResult ? <DraftProgress result={draftResult} /> : null}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-[var(--color-border)] bg-[var(--color-surface-muted)] px-6 py-4">
          {step === "input" ? (
            <button
              type="button"
              disabled={isAnalyzing || !rawText.trim()}
              onClick={handleAnalyze}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
              )}
            >
              {isAnalyzing ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : null}
              <span>Analyze</span>
            </button>
          ) : null}

          {step === "review" ? (
            <button
              type="button"
              disabled={isDrafting || days.length === 0}
              onClick={handleRunDrafter}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
              )}
            >
              {isDrafting ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : null}
              <span>Run Drafter</span>
            </button>
          ) : null}

          {step === "progress" && draftResult ? (
            <button
              type="button"
              onClick={() => onDraftComplete(draftResult)}
              className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2 text-white cursor-pointer")}
            >
              Done
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default TripProfileReviewDialog;
