'use client';

import Image from 'next/image';
import { useState } from 'react';
import type { TextValue, TypographySlotMap } from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import { requireTypographySlot } from '../../display/typographySlots.ts';
import { getTypographyClassName } from '../../config/typography.ts';

export default function ItineraryCarousel({
  images,
  alt,
  alts,
  labels,
  typography,
  className,
}: {
  images: string[];
  alt: TextValue;
  alts?: TextValue[];
  labels: { previous: TextValue; next: TextValue; list: TextValue; show: TextValue };
  typography: TypographySlotMap;
  className?: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeImage = images[activeIndex] ?? images[0];

  if (!activeImage) return null;

  const move = (offset: number) => {
    setActiveIndex((current) => (current + offset + images.length) % images.length);
  };
  const activeAlt = alts?.[activeIndex] ?? alt;

  return (
    <div className={`display-itinerary-carousel ${className ?? ''}`}>
      <Image key={activeImage} src={activeImage} alt={textValue(activeAlt)} data-editable={typeof activeAlt === 'string' ? undefined : activeAlt.path} data-edit-owner={typeof activeAlt === 'string' ? undefined : activeAlt.owner} data-edit-mode={typeof activeAlt === 'string' ? undefined : activeAlt.mode} fill sizes="(min-width: 981px) 46vw, 100vw" className="object-cover" />
      {images.length > 1 ? (
        <>
          <button type="button" onClick={() => move(-1)} className={`display-itinerary-carousel__control is-prev ${getTypographyClassName(requireTypographySlot(typography, 'action'))}`} aria-label={textValue(labels.previous)}>←</button>
          <button type="button" onClick={() => move(1)} className={`display-itinerary-carousel__control is-next ${getTypographyClassName(requireTypographySlot(typography, 'action'))}`} aria-label={textValue(labels.next)}>→</button>
          <div className="display-itinerary-carousel__dots" role="tablist" aria-label={textValue(labels.list)}>
            {images.map((image, index) => (
              <button
                key={image}
                type="button"
                role="tab"
                onClick={() => setActiveIndex(index)}
                className={`display-itinerary-carousel__dot${index === activeIndex ? ' is-active' : ''}`}
                aria-label={textValue(labels.show).replace('{index}', String(index + 1))}
                aria-selected={index === activeIndex}
              />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
