"use client";

/* R2 previews are thumbnail-sized runtime assets, so Next image optimization is intentionally bypassed. */
/* eslint-disable @next/next/no-img-element */

import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import useSWR from "swr";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { formatApiError } from "./factsTypes.ts";
import { quotationFetch } from "../../lib/apiError.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
const PAGE_SIZE = 60;

export type MediaPickerContext = {
  kind: "destination" | "accommodation" | "team";
  destinationId?: string;
  accommodationName?: string;
  accommodationKind?: "hotel" | "cruise";
  travelDesignerId?: string;
};
type Item = { r2Key: string; fileName: string; previewUrl: string | null; previewStatus?: string; width?: number | null; height?: number | null; classification?: string; mediaKind?: string | null };
type Children = { prefix: string; folders: Array<{ prefix: string; name: string }>; items: Item[]; nextCursor: number | null };
type SyncRun = { id: string; status: "queued" | "indexing" | "previewing" | "completed" | "failed"; scannedCount: number; indexedCount: number; previewCount: number; errorCount: number; errorMessage: string | null; reused?: boolean };

const isFolder = (value: unknown): value is Children["folders"][number] => {
  if (!value || typeof value !== "object") return false;
  const folder = value as { prefix?: unknown; name?: unknown };
  return typeof folder.prefix === "string" && typeof folder.name === "string";
};
const isItem = (value: unknown): value is Item => {
  if (!value || typeof value !== "object") return false;
  const item = value as { r2Key?: unknown; fileName?: unknown; previewUrl?: unknown; previewStatus?: unknown; width?: unknown; height?: unknown; classification?: unknown; mediaKind?: unknown };
  return typeof item.r2Key === "string" && typeof item.fileName === "string" && (typeof item.previewUrl === "string" || item.previewUrl === null) && (item.previewStatus === undefined || typeof item.previewStatus === "string") && (item.width === undefined || typeof item.width === 'number' || item.width === null) && (item.height === undefined || typeof item.height === 'number' || item.height === null) && (item.classification === undefined || typeof item.classification === 'string');
};
function uniqueBy<T>(items: T[], key: (item: T) => string): T[] {
  const unique = new Map<string, T>();
  for (const item of items) if (!unique.has(key(item))) unique.set(key(item), item);
  return [...unique.values()];
}
function normalizeLibraryPage(payload: unknown, fallbackPrefix: string): Children {
  if (!payload || typeof payload !== "object") throw new Error("Media library returned an invalid response.");
  const response = payload as { detail?: unknown; prefix?: unknown; folders?: unknown; items?: unknown; nextCursor?: unknown };
  if (response.detail !== undefined) throw new Error(formatApiError(response.detail, "Media library could not be loaded."));
  if (!Array.isArray(response.items)) throw new Error("Media library returned an invalid response.");
  return {
    prefix: typeof response.prefix === "string" ? response.prefix : fallbackPrefix,
    folders: Array.isArray(response.folders) ? uniqueBy(response.folders.filter(isFolder), (folder) => folder.prefix) : [],
    items: uniqueBy(response.items.filter(isItem), (item) => item.r2Key),
    nextCursor: typeof response.nextCursor === "number" ? response.nextCursor : null,
  };
}
async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  return quotationFetch<unknown>(url, init, "Media library request failed.");
}
async function fetchLibraryPage(url: string): Promise<Children> {
  const payload = await requestJson(url);
  const search = url.includes("?") ? url.slice(url.indexOf("?") + 1) : "";
  const prefix = new URLSearchParams(search).get("prefix") ?? "";
  return normalizeLibraryPage(payload, prefix);
}
const isActiveSync = (status?: SyncRun["status"]) => status === "queued" || status === "indexing" || status === "previewing";

export type MediaPickerProps = {
  onSelect?: (r2Key: string) => void;
  onConfirm?: (r2Keys: string[]) => void;
  onSelectFolder?: (folderPrefix: string) => void;
  mode?: "asset" | "folder";
  context?: MediaPickerContext;
  selectionMode?: "single" | "multiple";
  maxSelection?: number;
  initialSelection?: string[];
  initialPrefix?: string;
};

export default function MediaPicker({
  onSelect,
  onConfirm,
  onSelectFolder,
  mode = "asset",
  context,
  selectionMode = "single",
  maxSelection = 1,
  initialSelection = [],
  initialPrefix,
}: MediaPickerProps) {
  const { toast } = useToast();
  const [selected, setSelected] = useState<string[]>(initialSelection);
  const [prefix, setPrefix] = useState(initialPrefix ?? "");
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [cursor, setCursor] = useState(0);
  const [items, setItems] = useState<Item[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [syncRunId, setSyncRunId] = useState<string | null>(null);
  const [message, setMessage] = useState("Browse the indexed R2 library.");
  const [pending, startTransition] = useTransition();

  const isFolderMode = mode === "folder";

  const active = useMemo(() => {
    const search = new URLSearchParams();
    search.set("prefix", prefix);
    search.set("cursor", String(cursor));
    search.set("limit", String(PAGE_SIZE));
    if (deferredQuery.trim()) search.set("query", deferredQuery.trim());
    return deferredQuery.trim() ? `${API_BASE}/api/v2/media-library/search?${search}` : `${API_BASE}/api/v2/media-library/children?${search}`;
  }, [cursor, deferredQuery, prefix]);

  const { data, error, mutate } = useSWR<Children>(active, fetchLibraryPage, { revalidateOnFocus: false });
  const { data: syncRun } = useSWR<SyncRun>(
    syncRunId ? `${API_BASE}/api/v2/media-library/sync/${syncRunId}` : null,
    async (url) => requestJson(url) as Promise<SyncRun>,
    { refreshInterval: (latest) => (isActiveSync(latest?.status) ? 1000 : 0), revalidateOnFocus: false }
  );

  useEffect(() => {
    if (!data?.items) return;
    const timer = window.setTimeout(() => {
      setItems((current) => (cursor === 0 ? data.items : uniqueBy([...current, ...data.items], (item) => item.r2Key)));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [cursor, data]);

  useEffect(() => {
    if (!syncRun) return;
    const timer = window.setTimeout(() => {
      if (syncRun.status === "completed") {
        const msg = `R2 refresh complete · ${syncRun.indexedCount} images indexed.`;
        setMessage(msg);
        toast(msg, "success");
        void mutate();
      }
      if (syncRun.status === "failed") {
        const errMsg = syncRun.errorMessage || "R2 refresh failed. Retry when the media service is available.";
        setMessage(errMsg);
        toast(errMsg, "error");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [mutate, syncRun, toast]);

  const canUpload = !isFolderMode && Boolean(context && (context.kind === "team" ? context.travelDesignerId : context.destinationId) && (context.kind !== "accommodation" || context.accommodationName));
  const crumbs = useMemo(() => (prefix ? prefix.split("/") : []), [prefix]);

  const navigate = (nextPrefix: string) => { setPrefix(nextPrefix); setQuery(""); setCursor(0); setItems([]); };
  const refreshFromR2 = () => startTransition(async () => {
    try {
      const payload = await requestJson(`${API_BASE}/api/v2/media-library/sync`, { method: "POST" }) as SyncRun;
      setSyncRunId(payload.id);
      const msg = payload.reused ? "A media refresh is already running." : "Refreshing the R2 media index…";
      setMessage(msg);
      toast(msg, "info");
    } catch (requestError) {
      const errMsg = requestError instanceof Error ? requestError.message : "R2 refresh could not be started.";
      setMessage(errMsg);
      toast(errMsg, "error");
    }
  });
  const upload = () => startTransition(async () => {
    if (!file || !context) return;
    const form = new FormData();
    form.append("file", file); form.append("kind", context.kind);
    if (context.destinationId) form.append("destinationId", context.destinationId);
    if (context.accommodationName) form.append("accommodationName", context.accommodationName);
    if (context.accommodationKind) form.append("accommodationKind", context.accommodationKind);
    if (context.travelDesignerId) form.append("travelDesignerId", context.travelDesignerId);
    try {
      const payload = await requestJson(`${API_BASE}/api/v2/media-library/uploads`, { method: "POST", body: form }) as { r2Key?: unknown };
      if (typeof payload.r2Key !== "string") throw new Error("Upload returned an invalid response.");
      const uploadedKey: string = payload.r2Key;
      const msg = "Image uploaded and added to the selection.";
      setMessage(msg);
      toast(msg, "success");
      setCursor(0); setItems([]); await mutate();
      setSelected((current) => selectionMode === 'single' ? [uploadedKey] : current.includes(uploadedKey) ? current : [...current, uploadedKey].slice(0, maxSelection));
    } catch (requestError) {
      const errMsg = requestError instanceof Error ? requestError.message : "Upload failed.";
      setMessage(errMsg);
      toast(errMsg, "error");
    }
  });
  const activeSync = isActiveSync(syncRun?.status);
  const statusText = syncRun ? `${syncRun.status} · ${syncRun.indexedCount} indexed · ${syncRun.previewCount} previews` : "Browse the indexed R2 library.";
  const nextCursor = data?.nextCursor ?? null;
  const toggle = (r2Key: string) => setSelected((current) => {
    if (selectionMode === 'single') return [r2Key];
    if (current.includes(r2Key)) return current.filter((key) => key !== r2Key);
    return current.length >= maxSelection ? current : [...current, r2Key];
  });
  const confirm = () => {
    if (isFolderMode) {
      if (onSelectFolder) onSelectFolder(prefix);
      return;
    }
    if (!selected.length) return;
    if (onConfirm) onConfirm(selected);
    else if (onSelect) selected.forEach(onSelect);
  };

  return <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-2xs">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          {isFolderMode ? "R2 Folder Navigator" : "Media library"}
        </p>
        <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          {isFolderMode
            ? "Browse Cloudflare R2 folder tree to choose the asset directory for this item."
            : "Only the selected R2 key is saved to the quotation document."}
        </p>
      </div>
      <button type="button" disabled={pending || activeSync} onClick={refreshFromR2} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all disabled:opacity-50")}>{activeSync ? "Refreshing R2…" : "Refresh from R2"}</button>
    </div>
    <p aria-live="polite" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{statusText}</p>
    {canUpload ? <div className="flex flex-wrap items-center gap-3"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className={cn(getTypographyClassName("bodySm"), "min-h-11 text-[var(--color-on-surface)]")} /><button type="button" disabled={!file || pending} onClick={upload} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-md border border-transparent transition-all disabled:opacity-50")}>Upload to this location</button></div> : context && !isFolderMode ? <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Complete the linked destination, accommodation or designer before uploading.</p> : null}
    {message ? <p aria-live="polite" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{message}</p> : null}
    {error ? <div className="flex flex-wrap items-center gap-3"><p role="alert" className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{error instanceof Error ? error.message : "Media library could not be loaded."}</p><button type="button" onClick={() => void mutate()} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>Retry</button></div> : null}
    <label className="flex flex-col gap-2"><span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Search this folder</span><input value={query} onChange={(event) => { setQuery(event.target.value); setCursor(0); setItems([]); }} className={cn(getTypographyClassName("bodyMd"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]")} /></label>
    <nav className="flex min-h-11 flex-wrap gap-2" aria-label="Media folders">{prefix ? <button type="button" onClick={() => navigate("")} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>Library</button> : null}{crumbs.map((crumb, index) => <button type="button" key={`${crumb}-${index}`} onClick={() => navigate(crumbs.slice(0, index + 1).join("/"))} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-3 transition-all")}>{crumb}</button>)}</nav>
    {!deferredQuery ? (
      <div className="flex flex-col gap-2">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Subfolders</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {data?.folders.map((folder) => (
            <div
              key={folder.prefix}
              className="flex items-center justify-between gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-2.5 shadow-2xs hover:border-[var(--color-accent)] transition-all"
            >
              <button
                type="button"
                onClick={() => navigate(folder.prefix)}
                className={cn(getTypographyClassName("bodyMd"), "flex-1 text-left text-[var(--color-on-surface)] hover:text-[var(--color-accent)] cursor-pointer truncate")}
              >
                📁 {folder.name}
              </button>
              {isFolderMode ? (
                <button
                  type="button"
                  onClick={() => onSelectFolder?.(folder.prefix)}
                  className={cn(getTypographyClassName("caption"), "rounded-[var(--radius-button)] bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)] hover:bg-[var(--color-accent)] hover:!text-white transition-colors cursor-pointer shrink-0")}
                >
                  Select folder
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate(folder.prefix)}
                  className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] hover:text-[var(--color-on-surface)] cursor-pointer")}
                >
                  Open →
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    ) : null}

    {/* Items / Thumbnail preview grid */}
    {items.length > 0 ? (
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-3">
        <p className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
          {isFolderMode ? `Photos inside this folder (${items.length} indexed files)` : "Images in this folder"}
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const checked = selected.includes(item.r2Key);
            return (
              <div
                key={item.r2Key}
                onClick={() => { if (!isFolderMode) toggle(item.r2Key); }}
                className={cn(
                  "content-visibility-auto rounded-[var(--radius-button)] border p-3 text-left transition-all",
                  !isFolderMode ? "cursor-pointer" : "",
                  checked
                    ? "border-[var(--color-focus)] ring-2 ring-[var(--color-focus)] bg-[var(--color-surface-white)]"
                    : "border-[var(--color-border-strong)] bg-[var(--color-surface)]"
                )}
              >
                {item.previewUrl ? (
                  <img
                    src={item.previewUrl}
                    alt=""
                    loading="lazy"
                    className="h-28 w-full object-cover rounded-[var(--radius-button)]"
                  />
                ) : (
                  <span className={cn(getTypographyClassName("caption"), "flex h-28 items-center justify-center text-[var(--color-muted)]")}>
                    {item.previewStatus === "pending" || item.previewStatus === "processing" ? "Preparing preview…" : "Preview unavailable"}
                  </span>
                )}
                <span className={cn(getTypographyClassName("bodySm"), "mt-2 block break-all text-[var(--color-on-surface)] truncate")}>
                  {item.fileName}
                </span>
                <span className={cn(getTypographyClassName("caption"), "mt-1 block text-[var(--color-muted)]")}>
                  {item.classification ?? "generic"} · {item.width && item.height ? `${item.width}×${item.height}` : item.previewStatus === "ready" ? "Preview ready" : "Preview pending"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    ) : null}

    {!error && data && !data.folders.length && !items.length ? <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{deferredQuery ? "No indexed media matches this search." : "No indexed media is available in this folder. Refresh from R2 to load recent files."}</p> : null}
    {nextCursor !== null ? <button type="button" onClick={() => setCursor(nextCursor)} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all")}>Load more</button> : null}
    
    <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border-strong)] bg-[var(--color-surface)] pt-3">
      {isFolderMode ? (
        <>
          <div className="flex flex-col min-w-0">
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Active R2 Folder:</span>
            <span className={cn(getTypographyClassName("bodySm"), "font-mono text-[var(--color-on-surface)] truncate")}>
              {prefix ? `/${prefix}` : "/ (Root Directory)"}
            </span>
          </div>
          <button
            type="button"
            onClick={confirm}
            className={cn(
              getTypographyClassName("buttonPrimary"),
              "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all cursor-pointer"
            )}
          >
            {prefix ? `Use current folder: /${prefix}` : "Use Root Folder"}
          </button>
        </>
      ) : (
        <>
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{selected.length}/{maxSelection} selected</span>
          <button type="button" disabled={!selected.length} onClick={confirm} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-5 shadow-md border border-transparent transition-all disabled:opacity-50")}>{selectionMode === "multiple" ? "Add selected images" : "Use image"}</button>
        </>
      )}
    </div>
  </section>;
}
