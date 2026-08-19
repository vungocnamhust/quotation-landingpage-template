import type { HeroViewModel } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { ActionButton, BodyCopy, DisplayTitle, Kicker, MetaText } from '../atoms';
import { HeroRuleMeta } from '../molecules';
import { BaseSectionProps, SectionOverlay, sectionOrnaments, shellProps } from './sectionHelpers';

export function HeroSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<HeroViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="hero" className={shellProps(sectionId, displayConfig, viewMode, 'display-hero')}>
      <SectionOverlay
        src={viewModel.backgroundImage}
        alt={viewModel.backgroundImageAlt}
      />
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.content}>
          <Kicker variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')} tone="inverse">
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle
            as="h1"
            variant={requireTypographySlot(displayConfig.typographySlots, 'title')}
            className="display-hero__title"
            tone="inverse"
          >
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy
            variant={requireTypographySlot(displayConfig.typographySlots, 'body')}
            className="display-hero__lede"
            tone="inverse"
          >
            {viewModel.lede}
          </BodyCopy>
          <HeroRuleMeta
            primary={viewModel.metaPrimary}
            secondary={viewModel.metaSecondary}
            typography={displayConfig.typographySlots}
          />
          <div className="display-hero__actions">
            <ActionButton href={viewModel.primaryCta.href} colorRole="primary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')} className="display-hero__primary-action">
              {viewModel.primaryCta.label}
            </ActionButton>
          </div>
        </div>
        <div className={slots.footer}>
          <MetaText
            variant={requireTypographySlot(displayConfig.typographySlots, 'footer')}
            className="display-hero__footer"
            tone="inverse"
          >
            {viewModel.footerMeta}
          </MetaText>
        </div>
      </div>
    </section>
  );
}
