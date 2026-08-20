import type { NavViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import AppTopBar from '../../AppTopBar.tsx';
import { BaseSectionProps, shellProps } from './sectionHelpers.tsx';

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
