import type { PricingViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';
import { BodyCopy, DisplayTitle, MetaText } from '../atoms.tsx';
import { InvestmentRow } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function PricingSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<PricingViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="pricing" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            {viewModel.kicker ? (
              <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'label')} tone="accent" className="mb-2 block">
                {viewModel.kicker}
              </MetaText>
            ) : null}
            <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')} tone="default">
              {viewModel.title}
            </DisplayTitle>
          </div>
          {viewModel.description ? (
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="muted" className="sm:text-right">
              {viewModel.description}
            </BodyCopy>
          ) : null}
        </div>
        <div className={cn(slots.content, 'space-y-4')}>
          {viewModel.options.map((option) => (
            <InvestmentRow key={option.index} option={option} typography={displayConfig.typographySlots} />
          ))}
        </div>
        {viewModel.importantNote ? (
          <div className="mt-10 pt-6 border-t border-[var(--color-border)]">
            <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'label')} tone="accent" className="mb-1 block">
              {viewModel.importantNoteLabel}
            </MetaText>
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="muted">
              {viewModel.importantNote}
            </BodyCopy>
          </div>
        ) : null}
      </div>
    </section>
  );
}
