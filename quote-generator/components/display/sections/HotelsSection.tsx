import type { HotelsViewModel } from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import { getLayoutSlots } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { cn } from '../../../utils/cn.ts';
import { BodyCopy } from '../atoms.tsx';
import { HotelEditorialCard, SectionHeader } from '../molecules.tsx';
import { BaseSectionProps, getItineraryDayColor, sectionOrnaments, shellProps } from './sectionHelpers.tsx';

export function HotelsSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
  pageViewModel,
}: BaseSectionProps<HotelsViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  const itineraryDays = pageViewModel?.itinerary?.days ?? [];
  const lastDayIndex = itineraryDays.length > 0 ? itineraryDays.length - 1 : 0;
  const lastDayColor = itineraryDays.length > 0 ? getItineraryDayColor(lastDayIndex, itineraryDays.length) : 'borderless';

  // Hotel section background gets OPPOSITE color of the last itinerary day
  const hotelBgClass = lastDayColor === 'canvas'
    ? 'display-section--bg-surfaceWhite display-section--surface-borderless'
    : 'display-section--bg-canvas';

  return (
    <section id="hotels" className={cn(shellProps(sectionId, displayConfig, viewMode), hotelBgClass)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader title={viewModel.title} body={viewModel.description} typography={displayConfig.typographySlots} />
        </div>
        <div className={slots.items}>
          {viewModel.cards.map((item) => (
            <HotelEditorialCard
              key={`${textValue(item.city)}-${textValue(item.name)}`}
              item={item}
              typography={displayConfig.typographySlots}
            />
          ))}
        </div>
        {viewModel.roomNotes && textValue(viewModel.roomNotes) ? (
          <div className="mt-8 p-4.5 rounded-none border border-dashed border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_6%,transparent)]">
            <strong className={cn(getTypographyClassName('overline'), 'block mb-1.5 text-[var(--color-accent)]')}>
              Room Notes &amp; Special Requests
            </strong>
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
              {viewModel.roomNotes}
            </BodyCopy>
          </div>
        ) : null}
      </div>
    </section>
  );
}
