'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import { apiErrorMessage } from '../../lib/apiError.ts';
import { restoreRelease, unpublishTarget } from '../../lib/publicationApi.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';

import CustomSelect from '../ui/CustomSelect.tsx';

type Brand = { id: string; displayName: string; hostname: string; status: 'active' | 'disabled' };
type Publication = { targetId: string; brandId: string; hostname: string; locale: string; slug: string; fallbackUrl: string; status: string; release?: { number: number } | null; releases: Array<{ number: number; status: string; isCurrent: boolean; job?: { type: string; status: string; attempts: number; maxAttempts: number; lastError: string | null } | null }> };

export default function PublicationTargetManager({ quotationId, brandId, onBrandChange, brandsData, publications, refresh }: { quotationId: string; brandId: string | null; onBrandChange: (brandId: string) => void; brandsData?: { brands: Brand[] }; publications?: { publications: Publication[] }; refresh?: () => Promise<unknown> }) {
  const brands = brandsData?.brands ?? [];
  const targets = publications?.publications ?? [];
  const [message, setMessage] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const { toast, notify, clearScope } = useToast();

  async function action(targetId: string, actionName: 'unpublish' | 'restore', release?: number) {
    const actionKey = `${targetId}-${actionName}-${release ?? ''}`;
    setRunningAction(actionKey);
    try {
      // Plan 16.2 F-17: unpublish/restore are revision-agnostic by design —
      // the advisory lock on the target, not a baseRevision token, is what
      // serializes these mutations.
      if (actionName === 'restore') {
        await restoreRelease(quotationId, targetId, release as number);
      } else {
        await unpublishTarget(quotationId, targetId);
      }
      if (refresh) await refresh();
      const success = actionName === 'restore' ? `Release #${release} restored and cache synchronization queued.` : 'Publication target unpublished and cache synchronization queued.';
      clearScope(`publication-target:${targetId}`);
      setMessage(success);
      toast(success, 'success');
    } catch (error) {
      const failure = apiErrorMessage(error);
      setMessage(failure);
      notify({ message: failure, type: 'error', persistent: true, scope: `publication-target:${targetId}`, action: { label: 'Retry', onClick: () => void action(targetId, actionName, release) } });
    } finally {
      setRunningAction(null);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <div className="flex flex-col gap-1.5">
        <span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Publication brand</span>
        <CustomSelect
          value={brandId}
          placeholder="Select a brand"
          onChange={onBrandChange}
          options={brands.map((brand) => ({ id: brand.id, label: `${brand.displayName} · ${brand.hostname}` }))}
        />
      </div>
      {message ? <p role="status" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{message}</p> : null}
      {targets.map((target) => (
        <article key={target.targetId} className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-on-surface)]')}>
            {target.hostname}/{target.locale}/q/{target.slug} · {target.status}{target.release ? ` · release ${target.release.number}` : ''}
          </p>
          {target.status === 'published' ? (
            <a href={target.fallbackUrl} target="_blank" rel="noreferrer" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-accent)] hover:underline')}>
              Customer fallback URL →
            </a>
          ) : (
            <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>
              Customer fallback URL · Preparing in background…
            </span>
          )}
          {target.releases.map((release) =>
            release.job ? (
              <p key={`job-${release.number}`} className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
                Release {release.number} · {release.job.type}: {release.job.status} ({release.job.attempts}/{release.job.maxAttempts})
                {release.job.lastError ? ` · ${release.job.lastError}` : ''}
              </p>
            ) : null
          )}
          <div className="flex flex-wrap gap-2">
            {target.status === 'published' ? (
              <button
                type="button"
                disabled={runningAction !== null}
                onClick={() => action(target.targetId, 'unpublish')}
                className={cn(
                  getTypographyClassName('buttonSecondary'),
                  'min-h-9 flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer disabled:opacity-50'
                )}
              >
                {runningAction === `${target.targetId}-unpublish-` ? <Loader2 size={13} className="animate-spin" /> : null}
                <span>Unpublish</span>
              </button>
            ) : null}
            {target.releases
              .filter((release) => !release.isCurrent && release.status === 'superseded')
              .map((release) => (
                <button
                  key={release.number}
                  type="button"
                  disabled={runningAction !== null}
                  onClick={() => action(target.targetId, 'restore', release.number)}
                  className={cn(
                    getTypographyClassName('buttonSecondary'),
                    'min-h-9 flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer disabled:opacity-50'
                  )}
                >
                  {runningAction === `${target.targetId}-restore-${release.number}` ? <Loader2 size={13} className="animate-spin" /> : null}
                  <span>Restore release {release.number}</span>
                </button>
              ))}
          </div>
        </article>
      ))}
    </section>
  );
}
