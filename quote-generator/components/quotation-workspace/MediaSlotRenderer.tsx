"use client";

import dynamic from "next/dynamic";
import { useMemo, useState, useTransition } from "react";
import { Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import type { EditableBrochureContract } from "./useQuotationWorkspace";
import type { DraftMediaRef, DraftMediaSelections, DraftMediaSlotValue } from "./factsTypes";

const MediaPicker = dynamic(() => import("./MediaPicker"));
const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

export type MediaRef = DraftMediaRef;
export type MediaSlotValue = DraftMediaSlotValue;
type Slot = NonNullable<EditableBrochureContract["mediaSlotRegistry"]>[number];
export type MediaWorkspace = {
    contract?: EditableBrochureContract;
    document?: Record<string, unknown>;
    quotationId?: string;
    lang?: string;
    currentRevision?: number;
    onSaved?: () => Promise<unknown> | void;
    draftSelections?: DraftMediaSelections;
    onDraftSelectionChange?: (fieldId: string, value: MediaSlotValue) => void;
};
export type MediaSlotContext = { index?: number; destinationId?: string; accommodationName?: string; travelDesignerId?: string; profileAssetKeys?: Record<string, string | null | undefined> };

function fieldIdFor(slot: Slot, context: MediaSlotContext): string[] {
    const template = slot.fieldTemplate;
    if (!template.includes("*")) return [template];
    if (context.index !== undefined) return [template.replace("*", String(context.index))];
    return (slot.keys ?? []).map((key) => template.replace("*", key));
}

function sourceFor(slot: Slot, fieldId: string): string[] {
    const source = slot.source ?? `/${fieldId.replaceAll(".", "/")}`;
    const templateParts = slot.fieldTemplate.split(".");
    const fieldParts = fieldId.split(".");
    const wildcard = fieldParts[templateParts.indexOf("*")] ?? "";
    return source.split("/").filter(Boolean).map((part) => part === "*" ? wildcard : part);
}

function readValue(workspace: MediaWorkspace, slot: Slot, fieldId: string): MediaSlotValue {
    if (workspace.draftSelections && Object.prototype.hasOwnProperty.call(workspace.draftSelections, fieldId)) return workspace.draftSelections[fieldId];
    const document = workspace.document;
    if (!document) return null;
    let current: unknown = document;
    for (const key of sourceFor(slot, fieldId)) {
        if (!current || typeof current !== "object") return null;
        current = (current as Record<string, unknown>)[key];
    }
    return current && typeof current === "object" ? current as MediaRef | MediaRef[] : null;
}

function resolverRationale(workspace: MediaWorkspace, fieldId: string): string | null {
    const presentation = workspace.document?.presentation;
    if (!presentation || typeof presentation !== "object") return null;
    const defaults = (presentation as { mediaDefaults?: unknown }).mediaDefaults;
    if (!defaults || typeof defaults !== "object") return null;
    const rationale = (defaults as { rationale?: unknown }).rationale;
    if (!Array.isArray(rationale)) return null;
    const entry = rationale.find((item) => item && typeof item === "object" && (item as { fieldId?: unknown }).fieldId === fieldId) as { reason?: unknown } | undefined;
    return typeof entry?.reason === "string" && entry.reason ? entry.reason : null;
}

function sourceLabel(values: MediaRef[], rationale: string | null, profileAssetKey?: string | null): string {
    if (!values.length) return "Empty — choose an image or generate a matching default.";
    if (values.some((value) => value.source === "auto")) return rationale ? `R2 default · ${rationale}` : "R2 default";
    if (profileAssetKey && values.length === 1 && values[0].r2Key === profileAssetKey) return "Profile default";
    return "Manual or profile selection";
}

export function MediaSlotRenderer({ workspace, editorRoute, context = {}, readOnly = false }: { workspace: MediaWorkspace; editorRoute: string; context?: MediaSlotContext; readOnly?: boolean }) {
    const [selected, setSelected] = useState<{ slot: Slot; fieldId: string } | null>(null);
    const [message, setMessage] = useState("");
    const [pending, startTransition] = useTransition();
    const slots = useMemo(() => (workspace.contract?.mediaSlotRegistry ?? []).filter((slot) => slot.editorRoute === editorRoute).flatMap((slot) => fieldIdFor(slot, context).map((fieldId) => ({ slot, fieldId }))), [context, editorRoute, workspace.contract?.mediaSlotRegistry]);
    const save = (fieldId: string, value: MediaRef | MediaRef[] | null) => startTransition(async () => {
        try {
            if (workspace.onDraftSelectionChange) {
                workspace.onDraftSelectionChange(fieldId, value);
                setMessage("Selected media will be saved when the quotation is created.");
                return;
            }
            if (!workspace.quotationId || !workspace.lang || workspace.currentRevision === undefined || !workspace.onSaved) {
                throw new Error("The quotation media workspace is not ready.");
            }
            await quotationFetch(`${API_BASE}/api/v2/quotations/${workspace.quotationId}/facts/media?lang=${encodeURIComponent(workspace.lang)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ baseRevision: workspace.currentRevision, slots: [{ fieldId, value }] }) }, "Media could not be saved.");
            setMessage("Saved media fact."); await workspace.onSaved();
        } catch (error) { setMessage(apiErrorMessage(error)); }
    });
    if (!slots.length) return null;
    return <div className="sm:col-span-2 grid gap-3 border-t border-[var(--color-border)] pt-4">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Brochure media</p>
        {slots.map(({ slot, fieldId }) => {
            const raw = readValue(workspace, slot, fieldId);
            const values = Array.isArray(raw) ? raw : raw?.r2Key ? [raw] : [];
            const gallery = slot.maxItems > 1;
            const rationale = resolverRationale(workspace, fieldId);
            return <div key={fieldId} className="rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-4 shadow-2xs">
                <div className="flex flex-wrap items-center justify-between gap-3"><span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{fieldId} · {values.length}/{slot.maxItems}</span>{!readOnly ? <div className="flex gap-2"><button type="button" disabled={pending} onClick={() => setSelected({ slot, fieldId })} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-3.5 shadow-2xs border border-transparent transition-all disabled:opacity-50")}>{values.length ? "Replace" : gallery ? "Add images" : "Choose image"}</button>{values.length ? <button type="button" disabled={pending} onClick={() => save(fieldId, gallery ? [] : null)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3.5 shadow-2xs border border-transparent transition-all disabled:opacity-50")}>Remove</button> : null}</div> : null}</div>
                <p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>{sourceLabel(values, rationale, context.profileAssetKeys?.[fieldId])}</p>
                {values.map((value, index) => <div key={`${value.r2Key}-${index}`} className="mt-2 flex flex-wrap items-center gap-2"><span className={cn(getTypographyClassName("caption"), "break-all text-[var(--color-muted)]")}>{value.r2Key}</span>{!readOnly ? <input aria-label={`${fieldId} image ${index + 1} alt text`} defaultValue={value.altText ?? ""} onBlur={(event) => { const next = [...values]; next[index] = { ...value, altText: event.target.value }; save(fieldId, gallery ? next : next[0]); }} className={cn(getTypographyClassName("bodySm"), "min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 text-[var(--color-on-surface)]")} placeholder="Alt text" /> : null}{gallery && !readOnly ? <><button type="button" disabled={index === 0 || pending} onClick={() => { const next = [...values]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; save(fieldId, next); }} className={cn(getTypographyClassName("buttonSecondary"), "min-h-9 rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white px-2.5")}>←</button><button type="button" disabled={index === values.length - 1 || pending} onClick={() => { const next = [...values]; [next[index + 1], next[index]] = [next[index], next[index + 1]]; save(fieldId, next); }} className={cn(getTypographyClassName("buttonSecondary"), "min-h-9 rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white px-2.5")}>→</button><button type="button" disabled={pending} onClick={() => save(fieldId, values.filter((_, itemIndex) => itemIndex !== index))} className={cn(getTypographyClassName("buttonSecondary"), "min-h-9 rounded-[var(--radius-button)] bg-rose-700 !text-white hover:bg-rose-800 px-3 shadow-2xs")}>Remove image</button></> : null}</div>)}
            </div>;
        })}
        {message ? <p aria-live="polite" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{message}</p> : null}
        {selected ? <div role="presentation" className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_38%,transparent)] p-4"><section role="dialog" aria-modal="true" aria-label="Media library" className="h-full w-full max-w-3xl overflow-y-auto bg-[var(--color-surface)] p-5"><div className="mb-4 flex justify-end"><button type="button" onClick={() => setSelected(null)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 rounded-[var(--radius-button)] bg-[var(--color-contrast)] !text-white hover:opacity-90 px-4 shadow-2xs")}>Close</button></div><MediaPicker selectionMode={selected.slot.maxItems > 1 ? "multiple" : "single"} maxSelection={selected.slot.maxItems} initialSelection={(Array.isArray(readValue(workspace, selected.slot, selected.fieldId)) ? readValue(workspace, selected.slot, selected.fieldId) as MediaRef[] : [readValue(workspace, selected.slot, selected.fieldId)].filter((value): value is MediaRef => Boolean(value && !Array.isArray(value))).map((value) => value)).map((value) => value.r2Key)} context={selected.slot.pickerContext === "destination" ? { kind: "destination", destinationId: context.destinationId } : selected.slot.pickerContext === "accommodation" ? { kind: "accommodation", destinationId: context.destinationId, accommodationName: context.accommodationName, accommodationKind: "hotel" } : selected.slot.pickerContext === "team" ? { kind: "team", travelDesignerId: context.travelDesignerId } : undefined} onConfirm={(keys) => { save(selected.fieldId, selected.slot.maxItems > 1 ? keys.map((r2Key) => ({ r2Key, status: "ready", source: "manual" as const })) : { r2Key: keys[0], status: "ready", source: "manual" }); setSelected(null); }} /></section></div> : null}
    </div>;
}

export function BrochureAssetsEditor({ workspace, readOnly, context }: { workspace: MediaWorkspace; readOnly?: boolean; context?: MediaSlotContext }) {
    return <div className="grid gap-3"><MediaSlotRenderer workspace={workspace} editorRoute="facts.brochureAssets" readOnly={readOnly} context={context} /><MediaDefaultsAction workspace={workspace} readOnly={readOnly} /></div>;
}

export function MediaDefaultsAction({ workspace, readOnly = false }: { workspace: MediaWorkspace; readOnly?: boolean }) {
    const [message, setMessage] = useState("");
    const [pending, startTransition] = useTransition();
    const { quotationId, lang, currentRevision, onSaved } = workspace;
    if (readOnly || !quotationId || !lang || currentRevision === undefined || !onSaved) return null;
    const generate = () => startTransition(async () => {
        try {
            await quotationFetch(`${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ baseRevision: currentRevision, dryRun: false }),
            }, "Missing media could not be generated.");
            setMessage("Generated missing media defaults."); await onSaved();
        } catch (error) { setMessage(apiErrorMessage(error)); }
    });
    return (
      <div className="rounded-[var(--radius-card)] border-2 border-dashed border-[color-mix(in_srgb,var(--color-accent)_45%,var(--color-border-strong))] bg-[color-mix(in_srgb,var(--color-accent-wash)_40%,var(--color-surface-white))] p-4 flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex flex-wrap items-center gap-2.5 min-w-0">
          <span className={cn(getTypographyClassName("caption"), "inline-flex items-center gap-1 rounded-full bg-[var(--color-accent)] px-2.5 py-0.5 !text-white shadow-2xs shrink-0")}>
            <Sparkles className="size-3.5 shrink-0 text-amber-300" aria-hidden="true" />
            <span>AI Media Auto-Fill</span>
          </span>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-on-surface)]")}>
            Let AI find and assign matching destination & stay photos from R2
          </p>
        </div>
        <button type="button" disabled={pending} onClick={generate} className={cn(getTypographyClassName("buttonSecondary"), "min-h-10 w-fit rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-2xs transition-all disabled:opacity-50")}>
          {pending ? "Generating media…" : "✨ Generate missing media"}
        </button>
        {message ? <p aria-live="polite" className={cn(getTypographyClassName("caption"), "w-full text-[var(--color-accent)]")}>{message}</p> : null}
      </div>
    );
}
