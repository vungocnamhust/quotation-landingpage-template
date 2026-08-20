import type { FooterViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { BodyCopy, MetaText } from '../atoms.tsx';
import { FooterMetaRow } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

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
