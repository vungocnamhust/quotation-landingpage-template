import type { NavViewModel } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import AppTopBar from '../../AppTopBar';
import { BaseSectionProps, shellProps } from './sectionHelpers';

export function NavSection({
  sectionId,
  viewModel,
  displayConfig,
  viewMode,
}: BaseSectionProps<NavViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="top" className={shellProps(sectionId, displayConfig, viewMode, 'display-nav')}>
      <div className={slots.container}>
        <AppTopBar viewModel={viewModel} typography={displayConfig.typographySlots} />
      </div>
    </section>
  );
}
