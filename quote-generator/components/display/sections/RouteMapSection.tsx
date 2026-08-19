import type { RouteMapViewModel } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { requireTypographySlot } from '../../../display/typographySlots';
import { BodyCopy, DisplayTitle } from '../atoms';
import RouteMapClientIsland from '../RouteMapClientIsland';
import { BaseSectionProps, StaticRouteMapPanel, sectionOrnaments, shellProps } from './sectionHelpers';

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
