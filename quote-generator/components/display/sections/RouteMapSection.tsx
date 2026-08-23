import type { RouteMapViewModel } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { BodyCopy, DisplayTitle } from '../atoms.tsx';
import RouteMapClientIsland from '../RouteMapClientIsland.tsx';
import { BaseSectionProps, StaticRouteMapPanel, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function RouteMapSection({
  sectionId,
  viewModel,
  displayConfig,
  colorScope,
  theme,
  viewMode,
}: BaseSectionProps<RouteMapViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="route-map" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')}>
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} className="display-route-map__lede">
            {viewModel.description}
          </BodyCopy>
        </div>

        <div className={slots.content}>
          {viewMode === 'pdf' ? (
            <StaticRouteMapPanel viewModel={viewModel} typography={displayConfig.typographySlots} />
          ) : (
            <RouteMapClientIsland
              viewModel={viewModel}
              typography={displayConfig.typographySlots}
              mapColors={{
                route: colorScope.style['--color-map-route'],
                leader: colorScope.style['--color-map-leader'],
                marker: colorScope.style['--color-map-marker'],
                activeMarker: colorScope.style['--color-map-marker-active'],
              }}
              viewMode={viewMode}
            />
          )}
        </div>
      </div>
    </section>
  );
}
