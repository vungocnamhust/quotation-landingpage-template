import { useEffect, useState } from 'react';
import { apiErrorMessage } from '../../lib/apiError.ts';
import { getPublicationJob, type PublicationJob } from '../../lib/publicationApi.ts';

const POLL_INTERVAL_MS = 1500;

/**
 * Polls a publication job by id, keyed strictly to that id (Plan 16.2
 * F-13/F-14/PB3.3): switching quotationId/brand mid-flight and publishing
 * again produces a new jobId, which re-keys this effect and aborts the
 * previous poll outright — a late response for a superseded job can never
 * overwrite state for the job actually being tracked now. The caller decides
 * when to disable the Publish button (job.status ∈ {queued, running}).
 */
export function usePublicationJob(jobId: string | null): PublicationJob | null {
  const [job, setJob] = useState<PublicationJob | null>(null);

  useEffect(() => {
    setJob(null);
    if (!jobId) return;
    let cancelled = false;
    const controller = new AbortController();
    let timer: number | undefined;

    async function poll() {
      try {
        const result = await getPublicationJob(jobId as string, controller.signal);
        if (cancelled) return;
        setJob(result);
        if (result.status === 'queued' || result.status === 'running') {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (error) {
        if (cancelled || (error instanceof DOMException && error.name === 'AbortError')) return;
        setJob((current) => (current ? { ...current, status: 'failed', lastError: apiErrorMessage(error) } : current));
      }
    }

    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [jobId]);

  return job;
}
