import Image from 'next/image';
import type { LetterViewModel } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { BodyCopy, DisplayTitle, MetaText, QuoteText } from '../atoms.tsx';
import { SectionHeader } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function OpenLetterSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<LetterViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const glyphVariant = displayConfig.typographySlots?.signatureGlyph ?? 'signatureGlyph';

  return (
    <section id="letter" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader
            kicker={viewModel.chapterKicker}
            title={viewModel.title}
            typography={displayConfig.typographySlots}
          />
        </div>

        <div className={slots.content}>
          <aside className={slots.aside}>
            <QuoteText
              variant={requireTypographySlot(displayConfig.typographySlots, 'quote')}
              tone="accent"
              className="display-letter__highlight"
            >
              {viewModel.highlight}
            </QuoteText>
            {typeof viewModel.decorAsset === 'string' && viewModel.decorAsset.trim() !== '' ? (
              <div className="display-letter__decor">
                <Image src={viewModel.decorAsset} alt="" width={220} height={240} className="display-letter__decor-image" />
              </div>
            ) : null}
          </aside>

          <div className={slots.media}>
            <div className="display-letter__copy">
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="default">
                {viewModel.greeting}
              </BodyCopy>
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>{viewModel.intro}</BodyCopy>
              {viewModel.body.map((paragraph) => (
                <BodyCopy key={textValue(paragraph)} variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
                  {paragraph}
                </BodyCopy>
              ))}
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>{viewModel.outro}</BodyCopy>
              {textValue(viewModel.signOff) ? (
                <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>{viewModel.signOff}</BodyCopy>
              ) : null}
              {textValue(viewModel.sender) ? (
                <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')} tone="muted">
                  {viewModel.sender}
                </MetaText>
              ) : null}

              <div className="display-letter__signature">
                {viewModel.signatureGlyph && textValue(viewModel.signatureGlyph)?.trim() ? (
                  <p
                    aria-hidden="true"
                    className={getTypographyClassName(glyphVariant)}
                    style={{ marginBottom: '0.6rem', color: 'var(--color-on-surface)', opacity: 0.88 }}
                  >
                    {textValue(viewModel.signatureGlyph)}
                  </p>
                ) : null}
                <DisplayTitle
                  as="h3"
                  variant={requireTypographySlot(displayConfig.typographySlots, 'signature')}
                >
                  {viewModel.signatureName}
                </DisplayTitle>
                <div className="display-letter__signature-meta">
                  <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')} tone="muted">
                    {viewModel.signatureRole}
                  </MetaText>
                  {viewModel.signatureContactLine ? (
                    <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')} tone="muted">
                      {viewModel.signatureContactLine}
                    </MetaText>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
