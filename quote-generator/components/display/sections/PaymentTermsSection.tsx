import type { PaymentTermsViewModel } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { TextLink } from '../atoms.tsx';
import { SectionHeader, TermRow } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function PaymentTermsSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<PaymentTermsViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  const ctaElement = (
    <span className="display-payment-terms__cta">
      <TextLink href={viewModel.cta.href} colorRole="secondary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')}>{viewModel.cta.label}</TextLink>
      <span aria-hidden="true">→</span>
    </span>
  );

  return (
    <section id="payment-terms" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <aside className={slots.aside}>
          <div className="whitespace-pre-line">
            <SectionHeader
              kicker={viewModel.kicker}
              title={viewModel.title}
              body={viewModel.description}
              typography={displayConfig.typographySlots}
            />
          </div>
          {viewMode !== 'mobile' ? (
            <div className="hidden lg:block">
              {ctaElement}
            </div>
          ) : null}
        </aside>

        <div className={slots.content}>
          {viewModel.terms.map((term) => (
            <TermRow key={textValue(term.label)} term={term} typography={displayConfig.typographySlots} />
          ))}
        </div>

        {viewMode === 'mobile' ? (
          <div className="pt-2">
            {ctaElement}
          </div>
        ) : (
          <div className="block lg:hidden pt-2">
            {ctaElement}
          </div>
        )}
      </div>
    </section>
  );
}
