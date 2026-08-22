import type { PricingViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';
import { BodyCopy, DisplayTitle, Kicker, MetaText } from '../atoms.tsx';
import { InvestmentHero, InvestmentComparisonCard, InvestmentRow } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function PricingSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<PricingViewModel>) {
  const optionCount = viewModel.options.length;
  const effectiveLayoutVariant =
    displayConfig.layoutVariant === 'pricing-investment-ledger' || !displayConfig.layoutVariant
      ? optionCount === 1
        ? 'pricing-hero-investment'
        : optionCount === 2
          ? 'pricing-editorial-comparison'
          : 'pricing-editorial-rows'
      : displayConfig.layoutVariant;

  const slots = getLayoutSlots(effectiveLayoutVariant, viewMode);

  return (
    <section id="pricing" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={cn(slots.header || 'flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8')}>
          <div>
            {viewModel.kicker ? (
              <Kicker variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')} tone="accent" className="mb-2">
                {viewModel.kicker}
              </Kicker>
            ) : null}
            <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')} tone="default">
              {viewModel.title}
            </DisplayTitle>
          </div>
          {viewModel.description ? (
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="muted" className={optionCount === 1 ? 'text-center' : 'sm:text-right'}>
              {viewModel.description}
            </BodyCopy>
          ) : null}
        </div>

        {optionCount === 1 ? (
          <div className={slots.content}>
            <InvestmentHero option={viewModel.options[0]} typography={displayConfig.typographySlots} />
          </div>
        ) : optionCount === 2 ? (
          <div className={slots.content}>
            {viewModel.options.map((option, idx) => (
              <InvestmentComparisonCard
                key={option.index}
                option={option}
                typography={displayConfig.typographySlots}
                isLast={idx === viewModel.options.length - 1}
              />
            ))}
          </div>
        ) : (
          <div className={cn(slots.content, 'divide-y divide-[var(--color-border)]')}>
            {viewModel.options.map((option) => (
              <InvestmentRow key={option.index} option={option} typography={displayConfig.typographySlots} />
            ))}
          </div>
        )}

        {viewModel.importantNote ? (
          <div className={cn(slots.footer || 'mt-10 pt-6 border-t border-[var(--color-border)]')}>
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

