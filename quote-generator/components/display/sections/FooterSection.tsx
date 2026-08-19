import type { FooterViewModel } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { BodyCopy, MetaText } from '../atoms';
import { FooterMetaRow } from '../molecules';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers';

export function FooterSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<FooterViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <footer id="footer" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <FooterMetaRow
          primary={
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="default">
              {viewModel.text}
            </BodyCopy>
          }
          secondary={
            viewModel.secondaryMeta ? (
              <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')}>
                {viewModel.secondaryMeta}
              </MetaText>
            ) : undefined
          }
        />
      </div>
    </footer>
  );
}
