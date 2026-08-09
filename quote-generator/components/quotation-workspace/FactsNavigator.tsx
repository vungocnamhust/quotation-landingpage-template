'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';

export type FactSectionId = 'trip' | 'travellers' | 'programme' | 'services' | 'commercial' | 'seller';

export type FactSectionStatus = {
  id: FactSectionId;
  label: string;
  detail: string;
  complete: boolean;
};

export default function FactsNavigator({
  sections,
  submitLabel,
  onSubmit,
  pending,
  activeSection,
}: {
  sections: FactSectionStatus[];
  submitLabel?: string;
  onSubmit?: () => void;
  pending?: boolean;
  activeSection?: FactSectionId;
}) {
  const [active, setActive] = useState<FactSectionId>('trip');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id.replace('facts-', '') as FactSectionId);
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: [0.1, 0.4, 0.75] }
    );
    document
      .querySelectorAll<HTMLElement>('[data-facts-section]')
      .forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  const goTo = (id: FactSectionId) =>
    document.getElementById(`facts-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const completedCount = sections.filter((s) => s.complete).length;

  return (
    <aside
      aria-label="Quotation fact progress"
      className="facts-navigator rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-white)] p-3.5 shadow-md backdrop-blur-md flex flex-col gap-3"
    >
      <div className="flex items-center justify-between px-1 pb-1 border-b border-[var(--color-border-strong)]">
        <span className={cn(getTypographyClassName('overline'), 'text-[var(--color-accent)]')}>
          Fact Progress
        </span>
        <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
          {completedCount}/{sections.length} done
        </span>
      </div>

      <div className="facts-navigator__list" role="navigation" aria-label="Fact sections">
        {sections.map((section) => {
          const isActive = (activeSection ?? active) === section.id;
          return (
            <button
              key={section.id}
              type="button"
              onClick={() => goTo(section.id)}
              aria-current={isActive ? 'location' : undefined}
              className={cn(
                getTypographyClassName('buttonSecondary'),
                'facts-navigator__item flex items-center justify-between min-h-11 rounded-[var(--radius-button)] px-3 text-left transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
                isActive
                  ? 'border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-xs'
                  : 'border border-transparent text-[var(--color-on-surface)] hover:bg-[color-mix(in_srgb,var(--color-accent-wash)_30%,transparent)] hover:border-[var(--color-border-strong)]'
              )}
            >
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate">{section.label}</span>
                <span
                  className={cn(
                    getTypographyClassName('caption'),
                    isActive
                      ? 'text-[var(--color-accent)]'
                      : section.complete
                      ? 'text-[var(--color-accent)]'
                      : 'text-[var(--color-muted)]'
                  )}
                >
                  {section.detail}
                </span>
              </span>
              <span className="shrink-0 ml-2">
                {section.complete ? (
                  <CheckCircle2 size={16} className="text-[var(--color-accent)]" aria-hidden="true" />
                ) : (
                  <AlertCircle size={16} className="text-[var(--color-muted)]" aria-hidden="true" />
                )}
              </span>
            </button>
          );
        })}
      </div>

      {onSubmit ? (
        <button
          type="button"
          onClick={onSubmit}
          disabled={pending}
          className={cn(
            getTypographyClassName('buttonPrimary'),
            'mt-1 min-h-11 w-full rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-md transition-all disabled:opacity-50'
          )}
        >
          {pending ? 'Saving facts…' : submitLabel}
        </button>
      ) : null}
    </aside>
  );
}
