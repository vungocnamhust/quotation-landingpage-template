'use client';

import { useEffect, useState } from 'react';
import SectionOutlineNav, { type SectionOutlineItem } from '../ui/SectionOutlineNav.tsx';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';

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
  isDirty,
}: {
  sections: FactSectionStatus[];
  submitLabel?: string;
  onSubmit?: () => void;
  pending?: boolean;
  activeSection?: FactSectionId;
  isDirty?: boolean;
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

  const goTo = (id: string) =>
    document.getElementById(`facts-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const completedCount = sections.filter((s) => s.complete).length;

  const items: SectionOutlineItem[] = sections.map((section) => ({
    id: section.id,
    label: section.label,
    isSelected: (activeSection ?? active) === section.id,
    isComplete: section.complete,
  }));

  const footer = onSubmit ? (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between px-1">
        <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
          Sync status:
        </span>
        {isDirty ? (
          <span className={cn(getTypographyClassName('caption'), 'inline-flex items-center gap-1.5 text-[var(--color-accent-alt)]')}>
            <span className="h-2 w-2 rounded-full bg-[var(--color-accent-alt)] animate-pulse" />
            Unsaved changes
          </span>
        ) : (
          <span className={cn(getTypographyClassName('caption'), 'inline-flex items-center gap-1 text-[var(--color-accent)]')}>
            <span className="h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            Synced
          </span>
        )}
      </div>
      <button
        type="button"
        onClick={onSubmit}
        disabled={pending}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'min-h-11 w-full rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-md transition-all disabled:opacity-50 cursor-pointer'
        )}
      >
        {pending ? 'Saving facts…' : submitLabel}
      </button>
    </div>
  ) : undefined;

  return (
    <SectionOutlineNav
      title="FACT SECTIONS"
      completedCount={completedCount}
      totalCount={sections.length}
      counterLabel="ready"
      items={items}
      onSelect={goTo}
      ariaLabel="Fact sections"
      footer={footer}
    />
  );
}
