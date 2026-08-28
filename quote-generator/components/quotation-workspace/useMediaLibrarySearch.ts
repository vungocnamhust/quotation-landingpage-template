'use client';

/**
 * Headless data hook for the R2 media library browser (Plan 16.1 M4.2,
 * React Component Reuse Golden Standard #1 — separate the headless search
 * hook from the presentational picker). Owns folder navigation, search,
 * pagination, the R2 refresh sync poll, and uploads. `MediaPicker` owns only
 * selection state and rendering.
 */
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from 'react';
import useSWR from 'swr';
import { formatApiError } from './factsTypes.ts';
import { quotationFetch } from '../../lib/apiError.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';
import type { MediaPickerContext } from './MediaPicker.tsx';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';
const PAGE_SIZE = 60;

export type MediaLibraryItem = { r2Key: string; fileName: string; previewUrl: string | null; previewStatus?: string; width?: number | null; height?: number | null; classification?: string; mediaKind?: string | null };
type MediaLibraryPage = { prefix: string; folders: Array<{ prefix: string; name: string }>; items: MediaLibraryItem[]; nextCursor: number | null };
type SyncRun = { id: string; status: 'queued' | 'indexing' | 'previewing' | 'completed' | 'failed'; scannedCount: number; indexedCount: number; previewCount: number; errorCount: number; errorMessage: string | null; reused?: boolean };

const isFolder = (value: unknown): value is MediaLibraryPage['folders'][number] => {
  if (!value || typeof value !== 'object') return false;
  const folder = value as { prefix?: unknown; name?: unknown };
  return typeof folder.prefix === 'string' && typeof folder.name === 'string';
};
const isItem = (value: unknown): value is MediaLibraryItem => {
  if (!value || typeof value !== 'object') return false;
  const item = value as { r2Key?: unknown; fileName?: unknown; previewUrl?: unknown; previewStatus?: unknown; width?: unknown; height?: unknown; classification?: unknown; mediaKind?: unknown };
  return typeof item.r2Key === 'string' && typeof item.fileName === 'string' && (typeof item.previewUrl === 'string' || item.previewUrl === null) && (item.previewStatus === undefined || typeof item.previewStatus === 'string') && (item.width === undefined || typeof item.width === 'number' || item.width === null) && (item.height === undefined || typeof item.height === 'number' || item.height === null) && (item.classification === undefined || typeof item.classification === 'string');
};
function uniqueBy<T>(items: T[], key: (item: T) => string): T[] {
  const unique = new Map<string, T>();
  for (const item of items) if (!unique.has(key(item))) unique.set(key(item), item);
  return [...unique.values()];
}
function normalizeLibraryPage(payload: unknown, fallbackPrefix: string): MediaLibraryPage {
  if (!payload || typeof payload !== 'object') throw new Error('Media library returned an invalid response.');
  const response = payload as { detail?: unknown; prefix?: unknown; folders?: unknown; items?: unknown; nextCursor?: unknown };
  if (response.detail !== undefined) throw new Error(formatApiError(response.detail, 'Media library could not be loaded.'));
  if (!Array.isArray(response.items)) throw new Error('Media library returned an invalid response.');
  return {
    prefix: typeof response.prefix === 'string' ? response.prefix : fallbackPrefix,
    folders: Array.isArray(response.folders) ? uniqueBy(response.folders.filter(isFolder), (folder) => folder.prefix) : [],
    items: uniqueBy(response.items.filter(isItem), (item) => item.r2Key),
    nextCursor: typeof response.nextCursor === 'number' ? response.nextCursor : null,
  };
}
async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  return quotationFetch<unknown>(url, init, 'Media library request failed.');
}
async function fetchLibraryPage(url: string): Promise<MediaLibraryPage> {
  const payload = await requestJson(url);
  const search = url.includes('?') ? url.slice(url.indexOf('?') + 1) : '';
  const prefix = new URLSearchParams(search).get('prefix') ?? '';
  return normalizeLibraryPage(payload, prefix);
}
const isActiveSync = (status?: SyncRun['status']) => status === 'queued' || status === 'indexing' || status === 'previewing';

export interface UseMediaLibrarySearchArgs {
  initialPrefix?: string;
  context?: MediaPickerContext;
  isFolderMode: boolean;
  onUploaded?: (r2Key: string) => void;
}

export function useMediaLibrarySearch({ initialPrefix, context, isFolderMode, onUploaded }: UseMediaLibrarySearchArgs) {
  const { toast } = useToast();
  const [prefix, setPrefix] = useState(initialPrefix ?? '');
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const [cursor, setCursor] = useState(0);
  const [items, setItems] = useState<MediaLibraryItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [syncRunId, setSyncRunId] = useState<string | null>(null);
  const [message, setMessage] = useState('Browse the indexed R2 library.');
  const [pending, startTransition] = useTransition();

  const active = useMemo(() => {
    const search = new URLSearchParams();
    search.set('prefix', prefix);
    search.set('cursor', String(cursor));
    search.set('limit', String(PAGE_SIZE));
    if (deferredQuery.trim()) search.set('query', deferredQuery.trim());
    return deferredQuery.trim() ? `${API_BASE}/api/v2/media-library/search?${search}` : `${API_BASE}/api/v2/media-library/children?${search}`;
  }, [cursor, deferredQuery, prefix]);

  const { data, error, mutate } = useSWR<MediaLibraryPage>(active, fetchLibraryPage, { revalidateOnFocus: false });
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
      if (syncRun.status === 'completed') {
        const msg = `R2 refresh complete · ${syncRun.indexedCount} images indexed.`;
        setMessage(msg);
        toast(msg, 'success');
        void mutate();
      }
      if (syncRun.status === 'failed') {
        const errMsg = syncRun.errorMessage || 'R2 refresh failed. Retry when the media service is available.';
        setMessage(errMsg);
        toast(errMsg, 'error');
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [mutate, syncRun, toast]);

  const canUpload = !isFolderMode && Boolean(context && (context.kind === 'team' ? context.travelDesignerId : context.destinationId) && (context.kind !== 'accommodation' || context.accommodationName));
  const crumbs = useMemo(() => (prefix ? prefix.split('/') : []), [prefix]);

  const navigate = (nextPrefix: string) => { setPrefix(nextPrefix); setQuery(''); setCursor(0); setItems([]); };
  const setSearchQuery = (nextQuery: string) => { setQuery(nextQuery); setCursor(0); setItems([]); };

  const refreshFromR2 = () => startTransition(async () => {
    try {
      const payload = await requestJson(`${API_BASE}/api/v2/media-library/sync`, { method: 'POST' }) as SyncRun;
      setSyncRunId(payload.id);
      const msg = payload.reused ? 'A media refresh is already running.' : 'Refreshing the R2 media index…';
      setMessage(msg);
      toast(msg, 'info');
    } catch (requestError) {
      const errMsg = requestError instanceof Error ? requestError.message : 'R2 refresh could not be started.';
      setMessage(errMsg);
      toast(errMsg, 'error');
    }
  });

  const upload = () => startTransition(async () => {
    if (!file || !context) return;
    const form = new FormData();
    form.append('file', file); form.append('kind', context.kind);
    if (context.destinationId) form.append('destinationId', context.destinationId);
    if (context.accommodationName) form.append('accommodationName', context.accommodationName);
    if (context.accommodationKind) form.append('accommodationKind', context.accommodationKind);
    if (context.travelDesignerId) form.append('travelDesignerId', context.travelDesignerId);
    try {
      const payload = await requestJson(`${API_BASE}/api/v2/media-library/uploads`, { method: 'POST', body: form }) as { r2Key?: unknown };
      if (typeof payload.r2Key !== 'string') throw new Error('Upload returned an invalid response.');
      const uploadedKey: string = payload.r2Key;
      const msg = 'Image uploaded and added to the selection.';
      setMessage(msg);
      toast(msg, 'success');
      setCursor(0); setItems([]); await mutate();
      onUploaded?.(uploadedKey);
    } catch (requestError) {
      const errMsg = requestError instanceof Error ? requestError.message : 'Upload failed.';
      setMessage(errMsg);
      toast(errMsg, 'error');
    }
  });

  const activeSync = isActiveSync(syncRun?.status);
  const statusText = syncRun ? `${syncRun.status} · ${syncRun.indexedCount} indexed · ${syncRun.previewCount} previews` : 'Browse the indexed R2 library.';

  return {
    prefix,
    query,
    deferredQuery,
    crumbs,
    items,
    folders: data?.folders ?? [],
    nextCursor: data?.nextCursor ?? null,
    error,
    message,
    statusText,
    activeSync,
    pending,
    canUpload,
    file,
    setFile,
    setCursor,
    setQuery: setSearchQuery,
    navigate,
    refreshFromR2,
    upload,
    mutate,
  };
}
