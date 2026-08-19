import type { ItinerarySectionViewModel } from '../../../display/types';
import { textValue } from '../../../display/types';
import { getLayoutSlots } from '../../../display/layoutRegistry';
import { ItineraryDayMultiLayout, ItineraryDaySingleLayout, SectionHeader } from '../molecules';
import { BaseSectionProps, getItineraryDayColor, sectionOrnaments, shellProps } from './sectionHelpers';

export function ItinerarySection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<ItinerarySectionViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const totalDays = viewModel.days.length;

  return (
    <section id="itinerary" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader
            kicker={viewModel.kicker}
            title={viewModel.title}
            body={viewModel.description}
            typography={displayConfig.typographySlots}
          />
        </div>
        <div className={slots.items}>
          {viewModel.days.map((day, index) => {
            const dayColor = getItineraryDayColor(index, totalDays);
            const wrapperClass = dayColor === 'canvas'
              ? 'display-itinerary-day-wrapper is-bg-canvas'
              : 'display-itinerary-day-wrapper is-bg-borderless';
            return (
              <div key={textValue(day.dayLabel)} className={wrapperClass}>
                {day.layoutType === 'multi' ? (
                  <ItineraryDayMultiLayout
                    day={day}
                    typography={displayConfig.typographySlots}
                  />
                ) : (
                  <ItineraryDaySingleLayout
                    day={day}
                    typography={displayConfig.typographySlots}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
