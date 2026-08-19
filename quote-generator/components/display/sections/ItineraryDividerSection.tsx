import type { ChapterDividerViewModel } from '../../../display/types';
import { textValue } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { cn } from '../../../utils/cn';
import { BodyCopy, DisplayTitle, Kicker, MetaText, TextLink } from '../atoms';
import { BaseSectionProps, SectionOverlay, sectionOrnaments, shellProps } from './sectionHelpers';

export function ItineraryDividerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<ChapterDividerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const isImageMode = displayConfig.backgroundVariant === 'image-overlay' && typeof viewModel.image === 'string' && viewModel.image.trim() !== '';

  return (
    <section id="divider-itinerary" className={shellProps(sectionId, displayConfig, viewMode)}>
      {isImageMode && viewModel.image ? (
        <SectionOverlay
          src={viewModel.image}
          alt={viewModel.imageAlt ?? viewModel.title}
          gradientClassName="display-section-overlay__gradient--chapter"
        />
      ) : null}
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.content}>
          <Kicker
            variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')}
            tone={isImageMode ? 'inverse' : 'accent'}
          >
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle
            as="h2"
            variant={requireTypographySlot(displayConfig.typographySlots, 'title')}
            tone={isImageMode ? 'inverse' : 'default'}
          >
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy
            variant={requireTypographySlot(displayConfig.typographySlots, 'body')}
            tone={isImageMode ? 'inverse' : 'muted'}
            className="display-chapter-divider__tagline"
          >
            {viewModel.tagline}
          </BodyCopy>
          {viewModel.journeyMeta?.length ? (
            <dl className={cn('display-chapter-divider__meta', isImageMode && 'is-inverse')}>
              {viewModel.journeyMeta.map((item) => (
                <div key={textValue(item.label)} className="display-chapter-divider__meta-row">
                  <dt>
                    <MetaText
                      variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')}
                      tone={isImageMode ? 'inverse' : 'accent'}
                    >
                      {item.label}
                    </MetaText>
                  </dt>
                  <dd>
                    <MetaText
                      variant={requireTypographySlot(displayConfig.typographySlots, 'metaPrimary')}
                      tone={isImageMode ? 'inverse' : 'default'}
                    >
                      {item.value}
                    </MetaText>
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
          {viewModel.exploreHref && viewModel.exploreLabel ? (
            <span className={cn('display-chapter-divider__explore', isImageMode && 'is-inverse')}>
              <TextLink href={viewModel.exploreHref} colorRole="secondary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')}>{viewModel.exploreLabel}</TextLink>
              <span aria-hidden="true">→</span>
            </span>
          ) : null}
        </div>
      </div>
    </section>
  );
}
