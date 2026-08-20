import type { InclusionsExclusionsViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { InclusionsPanel, SectionHeader } from '../molecules.tsx';
import { BaseSectionProps, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function InclusionsExclusionsSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<InclusionsExclusionsViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="inclusions" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader title={viewModel.title} typography={displayConfig.typographySlots} />
        </div>
        <div className={slots.content}>
          <InclusionsPanel
            title={viewModel.inclusionsTitle ?? viewModel.title}
            lead={viewModel.inclusionsLead}
            items={viewModel.inclusions}
            typography={displayConfig.typographySlots}
          />
          <InclusionsPanel
            title={viewModel.exclusionsTitle ?? viewModel.title}
            lead={viewModel.exclusionsLead}
            items={viewModel.exclusions}
            typography={displayConfig.typographySlots}
          />
        </div>
      </div>
    </section>
  );
}
