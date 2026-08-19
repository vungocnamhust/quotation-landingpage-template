import Image from 'next/image';
import type { StaysDividerViewModel } from '../../../display/types';
import { textValue } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { BodyCopy, DisplayTitle, Kicker, QuoteText } from '../atoms';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers';

export function StaysDividerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<StaysDividerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const hasValidImage = typeof viewModel.image === 'string' && viewModel.image.trim() !== '';

  return (
    <section id="divider-hotels" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className="display-stays-divider__journey-line" aria-hidden="true" />
      <div className={slots.container}>
        {hasValidImage ? (
          <div className={slots.media}>
            <div className="display-stays-divider__image">
              <Image src={viewModel.image} alt={textValue(viewModel.imageAlt)} data-editable={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.path} data-edit-owner={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.owner} data-edit-mode={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.mode} fill sizes="(min-width: 1024px) 50vw, 100vw" className="object-cover" />
            </div>
          </div>
        ) : null}
        <div className={slots.content}>
          <Kicker variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')}>
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')}>
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
            {viewModel.tagline}
          </BodyCopy>
          <QuoteText variant={requireTypographySlot(displayConfig.typographySlots, 'footer')}>
            {viewModel.closing}
          </QuoteText>
        </div>
      </div>
    </section>
  );
}
