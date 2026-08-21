import Image from 'next/image';
import type { CSSProperties, ReactNode } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder.ts';
import type {
  HotelCardViewModel,
  InclusionItemViewModel,
  ItineraryDayViewModel,
  PriceOptionViewModel,
  TextValue,
} from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import {
  BodyCopy,
  DisplayTitle,
  ImageFrame,
  Kicker,
  MetaText,
  PriceText,
  QuoteText,
} from './atoms.tsx';
import { normalizePoint } from './sections/sectionHelpers.tsx';
import {
  chunkItineraryDaysForPdf,
  chunkHotelsForPdf,
} from '../../lib/rules/pdfRules.ts';

export { chunkItineraryDaysForPdf, chunkHotelsForPdf };

interface PdfPageProps {
  documentModel: DisplayDocument;
  scope: string;
  children: ReactNode;
  className?: string;
  borderVariant?: 'none' | 'indochine'; // Strictly 'indochine' ONLY for letter & pricing
  ornamentVariant?: 'lantern' | 'cyclo' | 'van-mieu' | 'cloud' | 'none';
  showPageHeader?: boolean;
  watermark?: boolean;
}

function PdfPage({
  documentModel,
  scope,
  children,
  className = '',
  borderVariant = 'none',
  ornamentVariant = 'none',
  showPageHeader = true,
  watermark = true,
}: PdfPageProps) {
  const colorScope = documentModel.colors.sections[scope as keyof typeof documentModel.colors.sections];
  const brandName = textValue(documentModel.page.footer.text) || documentModel.tokens.brandKey || 'Indochine';
  const quotationRef = [brandName, documentModel.quotationNumber].filter(Boolean).join(' · ');
  const hasIndochineBorder = borderVariant === 'indochine';

  return (
    <section
      className={`pdf-brochure-page display-color-scope display-color-scope--${colorScope?.id ?? 'paper'} ${
        hasIndochineBorder ? 'pdf-brochure-page--indochine-shell' : ''
      } ${className}`}
      style={colorScope?.style as CSSProperties}
      data-pdf-page={scope}
    >
      {ornamentVariant !== 'none' ? (
        <div
          className={`pdf-indochine-art pdf-indochine-art--${ornamentVariant} ${
            scope === 'hero'
              ? 'cover-lantern'
              : scope === 'routeMap'
                ? 'route-cyclo'
                : scope === 'hotels'
                  ? 'hotel-plan-van-mieu'
                  : scope === 'pricing'
                    ? 'pricing-cloud'
                    : scope === 'paymentTerms'
                      ? 'terms-buffalo'
                      : scope === 'designer'
                        ? 'designer-cyclo'
                        : scope === 'itineraryDivider'
                          ? 'divider-lantern'
                          : scope === 'staysDivider'
                            ? 'hotel-divider-lantern'
                            : ''
          }`}
          aria-hidden="true"
        />
      ) : null}

      {showPageHeader ? (
        <div className="pdf-page-header">
          <span className="brand">
            {documentModel.appChrome?.brandOptions?.[0]?.logoSrc ? (
              <Image
                src={documentModel.appChrome.brandOptions[0].logoSrc}
                alt=""
                width={14}
                height={14}
                unoptimized
                style={{ objectFit: 'contain', display: 'inline-block' }}
              />
            ) : null}
            <span className={getTypographyClassName('overline')}>
              {brandName} — Luxury Quotation
            </span>
          </span>
          <span className={`ref ${getTypographyClassName('overline')}`}>
            {documentModel.quotationNumber}
          </span>
        </div>
      ) : null}

      <div className="pdf-brochure-page__content">{children}</div>

      {watermark ? (
        <div className={`pdf-watermark ${getTypographyClassName('caption')}`}>
          {`${quotationRef} · Confidential`}
        </div>
      ) : null}
    </section>
  );
}

function PdfCover({ documentModel }: { documentModel: DisplayDocument }) {
  const hero = documentModel.page.hero;
  return (
    <PdfPage
      documentModel={documentModel}
      scope="hero"
      borderVariant="none"
      ornamentVariant="lantern"
      showPageHeader={false}
      watermark={false}
      className="pdf-cover"
    >
      <Image
        src={hero.backgroundImage}
        alt={textValue(hero.backgroundImageAlt)}
        data-editable={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.path}
        data-edit-owner={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.owner}
        data-edit-mode={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.mode}
        fill
        priority
        sizes="794px"
        className="pdf-cover__image"
      />
      <div className="pdf-cover__veil" />
      <div className="pdf-cover__body">
        <div className="pdf-cover__top">
          <Kicker variant="chapterKicker" tone="inverse">
            {hero.kicker}
          </Kicker>
          <DisplayTitle as="h1" variant="hero" tone="inverse">
            {hero.title}
          </DisplayTitle>
        </div>
        <div className="pdf-cover__bottom">
          <BodyCopy variant="heroLede" tone="inverse">
            {hero.lede}
          </BodyCopy>
          <div className="pdf-cover__meta-box">
            <MetaText variant="heroMetaPrimary" tone="inverse">
              {hero.metaPrimary}
            </MetaText>
            <MetaText variant="heroMetaSecondary" tone="inverse">
              {hero.metaSecondary}
            </MetaText>
          </div>
        </div>
      </div>
    </PdfPage>
  );
}

function PdfLetter({ documentModel }: { documentModel: DisplayDocument }) {
  const letter = documentModel.page.letter;
  return (
    <PdfPage
      documentModel={documentModel}
      scope="letter"
      borderVariant="indochine"
      ornamentVariant="none"
      className="pdf-letter"
    >
      <div className="page-inner">
        <header className="pdf-letter__header">
          <Kicker variant="chapterKicker">{letter.chapterKicker}</Kicker>
          <DisplayTitle as="h2" variant="letterTitle">
            {letter.title}
          </DisplayTitle>
          <hr className="pdf-letter__header-rule" />
        </header>
        <div className="pdf-letter__grid">
          <aside className="pdf-letter__decor-col">
            {textValue(letter.highlight) ? (
              <QuoteText variant="letterHighlight">{letter.highlight}</QuoteText>
            ) : (
              <div />
            )}
            <Image
              src="/assets/brands/indochine_icon/ruong_bac_thang.svg"
              alt=""
              width={160}
              height={120}
              unoptimized
              style={{ width: '100%', maxWidth: '160px', opacity: 0.85, height: 'auto' }}
            />
          </aside>
          <article className="pdf-letter__body-col">
            <div className="pdf-letter__paragraphs">
              <BodyCopy variant="letterBody">{letter.greeting}</BodyCopy>
              <BodyCopy variant="letterBody">{letter.intro}</BodyCopy>
              {letter.body.map((paragraph, index) => (
                <BodyCopy key={`letter-para-${index}`} variant="letterBody">
                  {paragraph}
                </BodyCopy>
              ))}
              <BodyCopy variant="letterBody">{letter.outro}</BodyCopy>
            </div>
            <div className="pdf-letter__signature">
              <DisplayTitle as="h3" variant="signatureName">
                {letter.signatureName}
              </DisplayTitle>
              <div className="pdf-letter__signature-meta">
                <MetaText variant="signatureMeta">{letter.signatureRole}</MetaText>
                {letter.signatureContactLine ? (
                  <>
                    <span className={getTypographyClassName('caption')}>·</span>
                    <MetaText variant="signatureMeta">{letter.signatureContactLine}</MetaText>
                  </>
                ) : null}
              </div>
            </div>
          </article>
        </div>
      </div>
    </PdfPage>
  );
}

function PdfRouteMapSvg({ route }: { route: DisplayDocument['page']['routeMap'] }) {
  const mapCenter = route.mapViewport.center || [16.0, 107.5];
  const latSpan = Math.max(route.mapViewport.latSpan || 8, 0.5);
  const lngSpan = Math.max(route.mapViewport.lngSpan || 8, 0.5);
  const sourceMarkers = route.interactiveMarkers.length > 0
    ? route.interactiveMarkers
    : route.segments.map((s) => ({
        sequence: s.sequence,
        coordinates: s.coordinates,
        title: s.title,
        city: s.city,
        dayLabel: s.dayLabel,
      }));

  const projectedPoints = sourceMarkers.map((marker, idx) => {
    const coords = marker.coordinates || [16.0 + (idx - 2) * 2, 107.5 + (idx % 2 === 0 ? -1 : 1)];
    return {
      ...marker,
      ...normalizePoint(coords, mapCenter, latSpan, lngSpan),
    };
  });

  const activeSegment =
    route.segments.find((segment) => segment.sequence === route.initialActiveSegment) ?? route.segments[0];

  const routePath = projectedPoints.reduce((pathStr, point, index) => {
    if (index === 0) return `M ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
    const prev = projectedPoints[index - 1];
    const midX = (prev.x + point.x) / 2;
    const midY = (prev.y + point.y) / 2;
    const dx = point.x - prev.x;
    const dy = point.y - prev.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const offset = Math.max(1.5, Math.min(6, len * 0.12));
    const ctrlX = midX - (dy / (len || 1)) * offset;
    const ctrlY = midY + (dx / (len || 1)) * offset;
    return `${pathStr} Q ${ctrlX.toFixed(2)} ${ctrlY.toFixed(2)} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
  }, '');

  return (
    <svg
      viewBox="0 0 100 100"
      className="display-route-map__svg"
      aria-label={textValue(route.overviewAriaLabel)}
      data-editable={typeof route.overviewAriaLabel === 'string' ? undefined : route.overviewAriaLabel.path}
      data-edit-owner={typeof route.overviewAriaLabel === 'string' ? undefined : route.overviewAriaLabel.owner}
      data-edit-mode={typeof route.overviewAriaLabel === 'string' ? undefined : route.overviewAriaLabel.mode}
      preserveAspectRatio="none"
    >
      <path d={routePath} className="pdf-route__line" />
      {projectedPoints.map((point) => (
        <g key={point.sequence}>
          <circle
            cx={point.x.toFixed(2)}
            cy={point.y.toFixed(2)}
            r={activeSegment?.sequence === point.sequence ? '3.2' : '2.3'}
            className="pdf-route__marker"
          />
          <text
            x={point.x.toFixed(2)}
            y={(point.y - 5).toFixed(2)}
            textAnchor="middle"
            className={`pdf-route__marker-text ${getTypographyClassName('caption')}`}
          >
            {textValue(point.dayLabel)}
          </text>
        </g>
      ))}
    </svg>
  );
}

function PdfRouteMap({ documentModel }: { documentModel: DisplayDocument }) {
  const route = documentModel.page.routeMap;
  const quoteText =
    textValue(documentModel.page.footer.secondaryMeta) ||
    'Your journeys through Vietnam and Indochina, shaped around living heritage, quiet landscapes and the luxury of time.';

  return (
    <PdfPage
      documentModel={documentModel}
      scope="routeMap"
      borderVariant="none"
      ornamentVariant="cyclo"
      className="pdf-route-page"
    >
      <div className="pdf-route__top-half">
        <Kicker variant="chapterKicker">{route.title}</Kicker>
        <DisplayTitle as="h2" variant="routeMapTitle">
          {route.title}
        </DisplayTitle>
        {route.description ? (
          <BodyCopy variant="bodySm">{route.description}</BodyCopy>
        ) : null}
        <div className="pdf-route__map-frame">
          <PdfRouteMapSvg route={route} />
        </div>
      </div>

      <div className="pdf-route__mid-tier">
        <div style={{ textAlign: 'center', marginBottom: '14px' }}>
          <Kicker variant="overline">Route Overview</Kicker>
        </div>
        <div className="pdf-route__timeline">
          {route.segments.map((segment, index) => (
            <div
              key={segment.sequence || `seg-${index}`}
              style={{ display: 'contents' }}
            >
              <div className="pdf-route__timeline-item">
                <div className={`pdf-route__timeline-dot ${getTypographyClassName('caption')}`}>
                  {index + 1}
                </div>
                <div className="pdf-route__timeline-info">
                  <DisplayTitle as="h3" variant="timelineTitle">
                    {segment.city}
                  </DisplayTitle>
                  {segment.duration ? (
                    <MetaText variant="caption">{segment.duration}</MetaText>
                  ) : null}
                  {segment.hotelName ? (
                    <MetaText variant="caption">{segment.hotelName}</MetaText>
                  ) : null}
                </div>
              </div>
              {index < route.segments.length - 1 ? (
                <div className="pdf-route__timeline-connector" />
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <div className="pdf-route__bottom-tier">
        <div className="pdf-route__quote-rule" />
        <blockquote className={`pdf-route__quote-text ${getTypographyClassName('quote')}`}>
          &ldquo;{quoteText}&rdquo;
        </blockquote>
        <div className="pdf-route__quote-rule" />
      </div>
    </PdfPage>
  );
}

function PdfChapterDivider({
  documentModel,
  scope,
  image,
  imageAlt,
  kicker,
  title,
  tagline,
  closing,
}: {
  documentModel: DisplayDocument;
  scope: string;
  image: string;
  imageAlt: TextValue;
  kicker: TextValue;
  title: TextValue;
  tagline?: TextValue;
  closing?: TextValue;
}) {
  const brandName = textValue(documentModel.page.footer.text) || documentModel.tokens.brandKey || 'Indochine';
  const reference = [brandName, documentModel.quotationNumber].filter(Boolean).join(' · ');

  return (
    <section className="pdf-brochure-page pdf-divider-page" data-pdf-page={scope}>
      <div className="pdf-divider__top-media">
        {image ? (
          <Image
            src={image}
            alt={textValue(imageAlt)}
            fill
            priority
            unoptimized
            className="pdf-divider__image"
          />
        ) : null}
        <div className="pdf-divider__gradient-overlay" />
      </div>
      <div className="pdf-divider__bottom-content">
        <div className="pdf-divider__gold-line" />
        <div style={{ marginBottom: '12px' }}>
          <Kicker variant="overline">{kicker}</Kicker>
        </div>
        <div style={{ marginBottom: '16px' }}>
          <DisplayTitle as="h2" variant="chapterTitle">
            {title}
          </DisplayTitle>
        </div>
        {tagline && textValue(tagline) ? (
          <div style={{ marginBottom: '12px' }}>
            <BodyCopy variant="bodyLg">
              {tagline}
            </BodyCopy>
          </div>
        ) : null}
        {closing && textValue(closing) ? (
          <QuoteText variant="quote">{closing}</QuoteText>
        ) : null}
        <div className={`pdf-divider__info-bar ${getTypographyClassName('caption')}`}>
          <span>{reference}</span>
          <span>{textValue(kicker)}</span>
        </div>
      </div>
    </section>
  );
}

function dayImages(day: ItineraryDayViewModel): Array<{ src: string; alt: TextValue }> {
  return day.carouselImages
    .map((src, index) => ({ src, alt: day.carouselImageAlts[index] ?? day.title }))
    .filter(
      (image, index, images) =>
        Boolean(image.src) && images.findIndex((candidate) => candidate.src === image.src) === index
    )
    .slice(0, 3);
}

function PdfItineraryDay({ day }: { day: ItineraryDayViewModel }) {
  const images = dayImages(day);
  const heroImageSrc = images[0]?.src || day.heroImage || '/assets/brands/vietnam_safar.png';
  const thumb1 = images[1]?.src || heroImageSrc;
  const thumb2 = images[2]?.src || thumb1;

  const kickerText = [textValue(day.city), textValue(day.dayLabel)].filter(Boolean).join(' · ');

  return (
    <article className={`day-card ${day.isAlternate ? 'is-alternate' : ''}`}>
      <div className="day-content">
        <div style={{ marginBottom: '6px' }}>
          <Kicker variant="overline">{kickerText}</Kicker>
        </div>
        <div style={{ margin: '0 0 8px' }}>
          <DisplayTitle as="h3" variant="dayTitle">
            {day.title}
          </DisplayTitle>
        </div>
        <div className="day-copy">
          {day.description.map((paragraph, index) => (
            <BodyCopy key={`day-para-${index}`} variant="dayBody">
              {paragraph}
            </BodyCopy>
          ))}
          {day.highlights && textValue(day.highlights) ? (
            <div className="day-highlights">
              <span className={getTypographyClassName('label')}>Highlights: </span>
              <BodyCopy variant="bodySm">{day.highlights}</BodyCopy>
            </div>
          ) : null}
          {day.notes && day.notes.length > 0 ? (
            <div className="day-notes">
              <span className={getTypographyClassName('label')}>Notes:</span>
              <ul>
                {day.notes.map((note, index) => (
                  <li key={`note-${index}`}>
                    <BodyCopy variant="bodySm">{note}</BodyCopy>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        {day.overnight || (day.meals && day.meals.length > 0) ? (
          <div className="day-detail-list">
            {day.overnight ? (
              <div className="day-detail">
                <span className={getTypographyClassName('caption')}>OVERNIGHT</span>
                <DisplayTitle as="h4" variant="cardTitle">
                  {day.overnight}
                </DisplayTitle>
              </div>
            ) : null}
            {day.meals && day.meals.length > 0 ? (
              <div className="day-detail">
                <span className={getTypographyClassName('caption')}>MEALS</span>
                <MetaText variant="caption">
                  {day.meals.map(textValue).join(', ')}
                </MetaText>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="day-media">
        <div className="day-media-main">
          <ImageFrame src={heroImageSrc} alt={images[0]?.alt ?? day.title} variant="editorial" />
        </div>
        <div className="day-media-thumbs">
          <div className="day-media-thumb">
            <ImageFrame src={thumb1} alt={images[1]?.alt ?? day.title} variant="editorial" />
          </div>
          <div className="day-media-thumb">
            <ImageFrame src={thumb2} alt={images[2]?.alt ?? day.title} variant="editorial" />
          </div>
        </div>
      </div>
    </article>
  );
}

function PdfItinerary({ documentModel }: { documentModel: DisplayDocument }) {
  const days = documentModel.page.itinerary.days;
  const dayPairs = chunkItineraryDaysForPdf(days);

  return (
    <>
      {dayPairs.map((pair, pageIndex) => (
        <PdfPage
          key={`itinerary-page-${pageIndex}`}
          documentModel={documentModel}
          scope="itinerary"
          borderVariant="none"
          ornamentVariant="none"
        >
          <div className="page-inner">
            <div className="pdf-itinerary__pair">
              {pair.map((day) => (
                <PdfItineraryDay
                  key={textValue(day.dayLabel) || textValue(day.title)}
                  day={day}
                />
              ))}
            </div>
          </div>
        </PdfPage>
      ))}
    </>
  );
}

function PdfHotels({ documentModel }: { documentModel: DisplayDocument }) {
  const roomNotes = documentModel.page.hotels.roomNotes;
  const cards = documentModel.page.hotels.cards;
  const hotelChunks = chunkHotelsForPdf(cards);

  return (
    <>
      {hotelChunks.map((chunk, pageIndex) => {
        const isLastPage = pageIndex === hotelChunks.length - 1;
        return (
          <PdfPage
            key={`hotels-page-${pageIndex}`}
            documentModel={documentModel}
            scope="hotels"
            borderVariant="none"
            ornamentVariant={isLastPage ? 'van-mieu' : 'none'}
          >
            <div className="page-inner">
              <div className="hotel-plan-container">
                {chunk.map((hotel: HotelCardViewModel, cardIndex: number) => {
                  const isEven = cardIndex % 2 === 1;
                  const telephone = hotel.telephone;
                  const telephonePrefix = hotel.telephonePrefix;
                  const datesText = hotel.dateRanges.map(textValue).filter(Boolean).join(' · ');

                  return (
                    <article
                      key={textValue(hotel.name) || `hotel-${cardIndex}`}
                      className="hotel-card-editorial"
                    >
                      <div className={`hotel-editorial-grid ${isEven ? 'even-row' : 'odd-row'}`}>
                        <div className="hotel-images-group">
                          <div className="hotel-image-wrapper">
                            <ImageFrame
                              src={hotel.hotelImage}
                              alt={hotel.hotelImageAlt}
                              variant="editorial"
                            />
                          </div>
                          <div>
                            <div className="hotel-image-wrapper">
                              <ImageFrame
                                src={hotel.roomImage}
                                alt={hotel.roomImageAlt}
                                variant="editorial"
                              />
                            </div>
                            {hotel.roomType ? (
                              <div style={{ marginTop: '4px' }}>
                                <MetaText variant="caption">{hotel.roomType}</MetaText>
                              </div>
                            ) : null}
                          </div>
                        </div>

                        <div className="hotel-info-block">
                          <MetaText variant="caption">{hotel.city}</MetaText>
                          <DisplayTitle as="h3" variant="hotelTitle">
                            {hotel.name}
                          </DisplayTitle>
                          {hotel.intro ? (
                            <BodyCopy variant="hotelBody">{hotel.intro}</BodyCopy>
                          ) : null}
                          <div className="hotel-tags">
                            {datesText ? (
                              <span className={getTypographyClassName('caption')}>
                                {datesText}
                              </span>
                            ) : null}
                            {telephone && textValue(telephone) ? (
                              <span className={getTypographyClassName('caption')}>
                                {textValue(telephonePrefix) || 'TEL:'} {textValue(telephone)}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>

              {isLastPage && roomNotes && textValue(roomNotes) ? (
                <div className="hotel-room-notes">
                  <span className={getTypographyClassName('label')}>
                    Room Notes &amp; Special Requests:{' '}
                  </span>
                  <span
                    className={getTypographyClassName('bodySm')}
                    {...(typeof roomNotes === 'string'
                      ? {}
                      : {
                          'data-editable': roomNotes.path,
                          'data-edit-owner': roomNotes.owner,
                          'data-edit-mode': roomNotes.mode,
                        })}
                  >
                    {textValue(roomNotes)}
                  </span>
                </div>
              ) : null}
            </div>
          </PdfPage>
        );
      })}
    </>
  );
}

function PdfPricing({ documentModel }: { documentModel: DisplayDocument }) {
  const pricing = documentModel.page.pricing;
  const noteLabel = pricing.importantNoteLabel;
  const note = pricing.importantNote;

  return (
    <PdfPage
      documentModel={documentModel}
      scope="pricing"
      borderVariant="indochine"
      ornamentVariant="cloud"
      className="pdf-pricing-page"
    >
      <div className="page-inner" style={{ justifyContent: 'center', height: 'calc(100% - 38px)' }}>
        <Kicker variant="chapterKicker">{pricing.kicker}</Kicker>
        <div style={{ margin: '8px 0' }}>
          <DisplayTitle as="h2" variant="investmentTitle">
            {pricing.title}
          </DisplayTitle>
        </div>
        {pricing.description ? (
          <div style={{ marginBottom: '20px' }}>
            <BodyCopy variant="bodyLg">
              {pricing.description}
            </BodyCopy>
          </div>
        ) : null}

        <div className="price-cards">
          {pricing.options.map((option: PriceOptionViewModel, index: number) => (
            <article
              key={option.index || textValue(option.displayIndex) || textValue(option.label)}
              className="price-card"
            >
              <div className={`price-card__num ${getTypographyClassName('investmentTitle')}`}>
                {index + 1 < 10 ? `0${index + 1}` : index + 1}
              </div>
              <div>
                <DisplayTitle as="h3" variant="cardTitle">
                  {option.label}
                </DisplayTitle>
              </div>
              <div>
                <PriceText variant="investmentValue">{option.groupTotalPrice}</PriceText>
                {option.perTravelerPrice && textValue(option.perTravelerPrice) ? (
                  <div style={{ marginTop: '2px' }}>
                    <MetaText variant="caption">
                      {`Per person: ${textValue(option.perTravelerPrice)}`}
                    </MetaText>
                  </div>
                ) : null}
              </div>
              <div>
                {option.isConfirmedMainOption ? (
                  <div className={`price-card__badge-confirmed ${getTypographyClassName('caption')}`}>
                    {textValue(pricing.confirmedMainOptionLabel) || '✓ CONFIRMED MAIN OPTION'}
                  </div>
                ) : (
                  <div className={`price-card__badge-alternative ${getTypographyClassName('caption')}`}>
                    ALTERNATIVE OPTION
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>

        {note && textValue(note) ? (
          <div className="price-important-note">
            <span className={getTypographyClassName('label')}>
              {textValue(noteLabel) || 'Important Note'}:
            </span>
            <BodyCopy variant="bodySm">{note}</BodyCopy>
          </div>
        ) : null}
      </div>
    </PdfPage>
  );
}

function inclusionText(item: InclusionItemViewModel): TextValue {
  return typeof item === 'string' || 'value' in item
    ? item
    : `${textValue(item.title)} — ${textValue(item.desc)}`;
}

function PdfDetails({ documentModel }: { documentModel: DisplayDocument }) {
  const details = documentModel.page.inclusionsExclusions;
  const terms = documentModel.page.paymentTerms;

  return (
    <>
      {/* Page 1: Inclusions & Exclusions */}
      <PdfPage
        documentModel={documentModel}
        scope="inclusionsExclusions"
        borderVariant="none"
        ornamentVariant="none"
      >
        <div className="page-inner">
          <Kicker variant="overline">Package Inclusions &amp; Exclusions</Kicker>
          <div style={{ margin: '8px 0 20px' }}>
            <DisplayTitle as="h2" variant="sectionTitle">
              {details.title}
            </DisplayTitle>
          </div>
          <div className="pdf-details__two-col">
            <div className="pdf-details__panel">
              <DisplayTitle as="h3" variant="cardTitle">
                {details.inclusionsTitle || 'Inclusions'}
              </DisplayTitle>
              <ul>
                {details.inclusions.map((item, index) => (
                  <li key={`inc-${index}`}>
                    <BodyCopy variant="bodySm">{inclusionText(item)}</BodyCopy>
                  </li>
                ))}
              </ul>
            </div>
            <div className="pdf-details__panel">
              <DisplayTitle as="h3" variant="cardTitle">
                {details.exclusionsTitle || 'Exclusions'}
              </DisplayTitle>
              <ul>
                {details.exclusions.map((item, index) => (
                  <li key={`exc-${index}`}>
                    <BodyCopy variant="bodySm">{item}</BodyCopy>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </PdfPage>

      {/* Page 2: Booking & Payment Terms */}
      <PdfPage
        documentModel={documentModel}
        scope="paymentTerms"
        borderVariant="none"
        ornamentVariant="cloud"
      >
        <div className="page-inner">
          <div className="pdf-terms__grid">
            <div>
              <Kicker variant="chapterKicker">{terms.kicker}</Kicker>
              <div style={{ margin: '8px 0 14px' }}>
                <DisplayTitle as="h2" variant="termTitle">
                  {terms.title}
                </DisplayTitle>
              </div>
              <BodyCopy variant="termBody">{terms.description}</BodyCopy>
            </div>
            <div className="pdf-terms__rows">
              {terms.terms.map((term, index) => (
                <div key={`term-${index}`} className="pdf-terms__row">
                  <DisplayTitle as="h3" variant="cardTitle">
                    {term.label}
                  </DisplayTitle>
                  <BodyCopy variant="termBody">{term.bodyRichText}</BodyCopy>
                </div>
              ))}
            </div>
          </div>
        </div>
      </PdfPage>
    </>
  );
}

function PdfDesigner({ documentModel }: { documentModel: DisplayDocument }) {
  const designer = documentModel.page.designer;

  return (
    <PdfPage
      documentModel={documentModel}
      scope="designer"
      borderVariant="none"
      ornamentVariant="cyclo"
    >
      <div className="page-inner" style={{ position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
        <div className="pdf-designer__circle-decor-1" />
        <div className="pdf-designer__circle-decor-2" />

        <div className="pdf-designer__grid">
          <div style={{ textAlign: 'center' }}>
            <div className="pdf-designer__avatar-frame">
              <ImageFrame src={designer.avatar} alt={designer.avatarAlt} variant="editorial" />
            </div>
            <div style={{ margin: '0 0 2px' }}>
              <DisplayTitle as="h3" variant="signatureName">
                {designer.name}
              </DisplayTitle>
            </div>
            {designer.subtitle ? (
              <MetaText variant="signatureMeta">{designer.subtitle}</MetaText>
            ) : null}
            <div style={{ marginTop: '8px', marginBottom: '14px' }}>
              <Kicker variant="label">{designer.signatureLabel || 'TRAVEL DESIGNER'}</Kicker>
            </div>
            <div
              style={{
                width: '40px',
                height: '1px',
                background: 'var(--color-accent)',
                margin: '0 auto 16px',
              }}
            />
            <QuoteText variant="quote">{designer.experienceNote}</QuoteText>
          </div>

          <div className="pdf-designer__right-col">
            <div>
              <Kicker variant="chapterKicker">{designer.kicker}</Kicker>
              <div style={{ margin: '8px 0 16px' }}>
                <DisplayTitle as="h2" variant="designerTitle">
                  {designer.title}
                </DisplayTitle>
              </div>
              <QuoteText variant="designerQuote">{designer.quote}</QuoteText>
            </div>
            <div className="pdf-designer__actions">
              <a href="https://wa.me/84913393119" className={`pdf-designer__whatsapp-btn ${getTypographyClassName('buttonPrimary')}`}>
                CHAT ON WHATSAPP
              </a>
              <a href="mailto:sales@capellatravel.com" className={`pdf-designer__email-btn ${getTypographyClassName('buttonPrimary')}`}>
                EMAIL
              </a>
            </div>
          </div>
        </div>
      </div>
    </PdfPage>
  );
}

export function PdfBrochureDocument({ documentModel }: { documentModel: DisplayDocument }) {
  const stays = documentModel.page.staysDivider;
  const itin = documentModel.page.itineraryDivider;

  return (
    <div className="pdf-brochure" data-pdf-compositor="a4-v2">
      <PdfCover documentModel={documentModel} />
      <PdfLetter documentModel={documentModel} />
      <PdfRouteMap documentModel={documentModel} />
      <PdfChapterDivider
        documentModel={documentModel}
        scope="itineraryDivider"
        image={itin.image ?? ''}
        imageAlt={itin.imageAlt ?? itin.title}
        kicker={itin.kicker}
        title={itin.title}
        tagline={itin.tagline}
      />
      <PdfItinerary documentModel={documentModel} />
      <PdfChapterDivider
        documentModel={documentModel}
        scope="staysDivider"
        image={stays.image}
        imageAlt={stays.imageAlt}
        kicker={stays.kicker}
        title={stays.pdfTitle || stays.title}
        tagline={stays.tagline}
        closing={stays.closing}
      />
      <PdfHotels documentModel={documentModel} />
      <PdfPricing documentModel={documentModel} />
      <PdfDetails documentModel={documentModel} />
      <PdfDesigner documentModel={documentModel} />
    </div>
  );
}
