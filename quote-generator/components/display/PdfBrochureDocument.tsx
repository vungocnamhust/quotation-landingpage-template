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
  LabelText,
  MetaText,
  PriceText,
  QuoteText,
} from './atoms.tsx';
import RouteMapClientIsland from './RouteMapClientIsland.tsx';
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
  showPageFooter?: boolean;
  watermark?: boolean;
}

function PdfFooterTier3({
  documentModel,
  className = '',
}: {
  documentModel: DisplayDocument;
  className?: string;
}) {
  const contrastScope = documentModel.colors.sections.staysDivider;
  const quoteText =
    'Your journeys through Vietnam and Indochina, shaped around living heritage, quiet landscapes and the luxury of time.';

  return (
    <div
      className={`pdf-footer-tier3 display-color-scope display-color-scope--contrast ${className}`}
      style={contrastScope?.style as CSSProperties}
    >
      <div className="pdf-footer-tier3__rule" />
      <blockquote className={`pdf-footer-tier3__quote ${getTypographyClassName('quote')}`}>
        &ldquo;{quoteText}&rdquo;
      </blockquote>
      <div className="pdf-footer-tier3__rule" />
    </div>
  );
}

function PdfPage({
  documentModel,
  scope,
  children,
  className = '',
  borderVariant = 'none',
  ornamentVariant = 'none',
  showPageHeader = true,
  showPageFooter = false,
}: PdfPageProps) {
  const colorScope = documentModel.colors.sections[scope as keyof typeof documentModel.colors.sections];
  const brandName =
    textValue(documentModel.page.nav.brandName) ||
    textValue(documentModel.page.hero.footerMeta) ||
    documentModel.tokens.brandKey ||
    'Indochine';
  const logoSrc =
    documentModel.page.nav.brandLogoSrc ||
    documentModel.appChrome?.brandOptions?.[0]?.logoSrc;
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
                          : scope === 'journeyTogetherDivider'
                            ? 'hotel-divider-lantern'
                            : ''
          }`}
          aria-hidden="true"
        />
      ) : null}

      {showPageHeader ? (
        <div className="pdf-page-header">
          <span className="brand" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            {logoSrc ? (
              <Image
                src={logoSrc}
                alt={textValue(documentModel.page.nav.brandLogoAlt) || brandName}
                width={80}
                height={20}
                unoptimized
                style={{ maxHeight: '18px', width: 'auto', objectFit: 'contain', display: 'inline-block' }}
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

      {showPageFooter ? (
        <div className="pdf-page-footer">
          <span className={`pdf-page-footer__brand ${getTypographyClassName('overline')}`}>
            {brandName}
          </span>
          <span className={`pdf-page-footer__ref ${getTypographyClassName('overline')}`}>
            {[documentModel.quotationNumber, 'CONFIDENTIAL'].filter(Boolean).join(' · ')}
          </span>
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
      showPageFooter={false}
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
          <Kicker variant="chapterKicker" tone="accent">{letter.chapterKicker}</Kicker>
          <DisplayTitle as="h2" variant="letterTitle">
            {letter.title}
          </DisplayTitle>
        </header>
        <div className="pdf-letter__grid">
          <aside className="pdf-letter__decor-col">
            {textValue(letter.highlight) ? (
              <div className="pdf-letter__highlight-block">
                <div className="pdf-letter__divider-wrapper">
                  <Image
                    src="/assets/brands/indochine_icon/line_divider.svg"
                    alt=""
                    width={180}
                    height={10}
                    unoptimized
                    className="pdf-letter__divider"
                  />
                </div>
                <QuoteText variant="letterHighlight" tone="accent">{letter.highlight}</QuoteText>
              </div>
            ) : (
              <div />
            )}
            <Image
              src={letter.decorAsset || '/assets/brands/indochine_icon/ruong_bac_thang.svg'}
              alt=""
              width={160}
              height={120}
              unoptimized
              className="pdf-letter__decor-art"
              style={{ width: '100%', maxWidth: '160px', opacity: 0.85, height: 'auto' }}
            />
          </aside>
          <article className="pdf-letter__body-col">
            <div className="pdf-letter__paragraphs">
              <BodyCopy variant="letterBody" tone="default">{letter.greeting}</BodyCopy>
              <BodyCopy variant="letterBody" tone="default">{letter.intro}</BodyCopy>
              {letter.body.map((paragraph, index) => (
                <BodyCopy key={`letter-para-${index}`} variant="letterBody" tone="default">
                  {paragraph}
                </BodyCopy>
              ))}
              <BodyCopy variant="letterBody" tone="default">{letter.outro}</BodyCopy>
              {textValue(letter.signOff) ? (
                <BodyCopy variant="letterBody" tone="default">{letter.signOff}</BodyCopy>
              ) : null}
              {textValue(letter.sender) ? (
                <MetaText variant="signatureMeta" tone="muted">{letter.sender}</MetaText>
              ) : null}
            </div>
            <div className="pdf-letter__signature">
              {letter.signatureGlyph ? (
                <p
                  aria-hidden="true"
                  className={getTypographyClassName('signatureGlyph')}
                  style={{ marginBottom: '0.35rem', opacity: 0.88 }}
                >
                  {textValue(letter.signatureGlyph)}
                </p>
              ) : null}
              <DisplayTitle as="h3" variant="signatureName">
                {letter.signatureName}
              </DisplayTitle>
              <div className="pdf-letter__signature-meta">
                <MetaText variant="signatureMeta" tone="accent">{letter.signatureRole}</MetaText>
                {letter.signatureContactLine ? (
                  <>
                    <span className={getTypographyClassName('caption')}>·</span>
                    <MetaText variant="signatureMeta" tone="muted">{letter.signatureContactLine}</MetaText>
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

function PdfRouteMap({ documentModel }: { documentModel: DisplayDocument }) {
  const route = documentModel.page.routeMap;
  const quotationNumber = documentModel.quotationNumber || 'QUO-2026';
  const quoteText = 'Your journeys through Vietnam and Indochina, shaped around living heritage, quiet landscapes and the luxury of time.';

  return (
    <PdfPage
      documentModel={documentModel}
      scope="routeMap"
      borderVariant="none"
      ornamentVariant="none"
      watermark={false}
      showPageHeader={false}
      showPageFooter={false}
      className="pdf-route-page pdf-route-page--fullbleed"
    >
      <RouteMapClientIsland
        viewModel={route}
        typography={{
          title: 'routeMapTitle',
          body: 'bodySm',
          kicker: 'overline',
          index: 'caption',
          metaPrimary: 'timelineTitle',
          metaSecondary: 'caption',
        }}
        mapColors={{
          route: 'var(--color-accent)',
          marker: 'var(--color-primary)',
          activeMarker: 'var(--color-accent)',
        }}
        viewMode="pdf"
        quotationNumber={quotationNumber}
        pageNumber="03"
        quoteText={quoteText}
      />
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
  const brandName =
    textValue(documentModel.page.nav.brandName) ||
    textValue(documentModel.page.hero.footerMeta) ||
    documentModel.tokens.brandKey ||
    'Indochine';
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
  const heroImageSrc = day.heroImage || images[0]?.src || '/assets/brands/vietnam_safar.png';
  const thumb1 = day.secondaryImages?.[0] || images[1]?.src || heroImageSrc;
  const thumb2 = day.secondaryImages?.[1] || images[2]?.src || thumb1;

  const heroAlt = day.title;
  const thumb1Alt = day.supportingImageAlts?.[0] || images[1]?.alt || day.title;
  const thumb2Alt = day.supportingImageAlts?.[1] || images[2]?.alt || day.title;

  const kickerText = [textValue(day.city), textValue(day.dayLabel)].filter(Boolean).join(' · ');

  return (
    <article className={`day-card ${day.isAlternate ? 'is-alternate' : ''}`}>
      <header className="day-header">
        <div style={{ marginBottom: '2px' }}>
          <Kicker variant="overline" tone="accent">{kickerText}</Kicker>
        </div>
        <div style={{ margin: '0 0 6px' }}>
          <DisplayTitle as="h3" variant="dayTitle">
            {day.title}
          </DisplayTitle>
        </div>
      </header>

      <div className="day-body">
        <div className="day-media">
          <div className="day-media-main">
            <ImageFrame
              src={heroImageSrc}
              alt={heroAlt}
              variant="editorial"
              className="w-full h-full"
            />
          </div>
          <div className="day-media-thumbs">
            <div className="day-media-thumb">
              <ImageFrame
                src={thumb1}
                alt={thumb1Alt}
                variant="editorial"
                className="w-full h-full"
              />
            </div>
            <div className="day-media-thumb">
              <ImageFrame
                src={thumb2}
                alt={thumb2Alt}
                variant="editorial"
                className="w-full h-full"
              />
            </div>
          </div>
        </div>

        <div className="day-content">
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
                  <span className={getTypographyClassName('caption')} style={{ fontWeight: 700 }}>
                    OVERNIGHT:
                  </span>
                  <span className={getTypographyClassName('bodySm')}>
                    {textValue(day.overnight)}
                  </span>
                </div>
              ) : null}
              {day.meals && day.meals.length > 0 ? (
                <div className="day-detail">
                  <span className={getTypographyClassName('caption')} style={{ fontWeight: 700 }}>
                    MEALS:
                  </span>
                  <span className={getTypographyClassName('bodySm')}>
                    {day.meals.map(textValue).join(', ')}
                  </span>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function PdfItinerary({ documentModel }: { documentModel: DisplayDocument }) {
  const itinerary = documentModel.page.itinerary;
  const days = itinerary.days;
  const pairs = chunkItineraryDaysForPdf(days);

  return (
    <>
      {pairs.map((pair, pageIndex) => {
        const isLastPage = pageIndex === pairs.length - 1;
        const shouldShowTier3OnLastPage = isLastPage && pair.length === 1;

        return (
          <PdfPage
            key={`itinerary-page-${pageIndex}`}
            documentModel={documentModel}
            scope="itinerary"
            borderVariant="none"
            ornamentVariant="none"
          >
            <div
              className="page-inner"
              style={{ paddingBottom: shouldShowTier3OnLastPage ? '16px' : undefined }}
            >
              {pageIndex === 0 ? (
                <div className="pdf-itinerary__header" style={{ marginBottom: '12px' }}>
                  <Kicker variant="chapterKicker" tone="accent">{itinerary.kicker}</Kicker>
                  <div style={{ margin: '4px 0 6px' }}>
                    <DisplayTitle as="h2" variant="sectionTitle">
                      {itinerary.title}
                    </DisplayTitle>
                  </div>
                  {itinerary.description && textValue(itinerary.description) ? (
                    <BodyCopy variant="bodySm" className="section-p">
                      {itinerary.description}
                    </BodyCopy>
                  ) : null}
                </div>
              ) : null}
              <div className="pdf-itinerary__pair">
                {pair.map((day) => (
                  <PdfItineraryDay
                    key={textValue(day.dayLabel) || textValue(day.title)}
                    day={day}
                  />
                ))}
              </div>
            </div>

            {shouldShowTier3OnLastPage ? (
              <PdfFooterTier3 documentModel={documentModel} />
            ) : null}
          </PdfPage>
        );
      })}
    </>
  );
}

function PdfHotels({ documentModel }: { documentModel: DisplayDocument }) {
  const hotelsSection = documentModel.page.hotels;
  const roomNotes = hotelsSection.roomNotes;
  const cards = hotelsSection.cards;
  const hotelChunks = chunkHotelsForPdf(cards);

  return (
    <>
      {hotelChunks.map((chunk, pageIndex) => {
        const isLastPage = pageIndex === hotelChunks.length - 1;
        const shouldShowTier3OnLastPage = isLastPage && chunk.length <= 2;
        return (
          <PdfPage
            key={`hotels-page-${pageIndex}`}
            documentModel={documentModel}
            scope="hotels"
            borderVariant="none"
            ornamentVariant={isLastPage ? 'van-mieu' : 'none'}
          >
            <div
              className="page-inner"
              style={{ paddingBottom: shouldShowTier3OnLastPage ? '16px' : undefined }}
            >
              {pageIndex === 0 ? (
                <div className="pdf-hotels__header" style={{ marginBottom: '14px' }}>
                  <Kicker variant="chapterKicker" tone="accent">{hotelsSection.kicker || 'SELECTED HOTEL PLAN'}</Kicker>
                  <div style={{ margin: '4px 0 6px' }}>
                    <DisplayTitle as="h2" variant="sectionTitle">
                      {hotelsSection.title}
                    </DisplayTitle>
                  </div>
                  {hotelsSection.description && textValue(hotelsSection.description) ? (
                    <BodyCopy variant="bodySm" className="section-p">
                      {hotelsSection.description}
                    </BodyCopy>
                  ) : null}
                </div>
              ) : null}

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
                              src={hotel.hotelImage || '/assets/brands/vietnam_safar.png'}
                              alt={hotel.hotelImageAlt || hotel.name}
                              variant="editorial"
                              className="w-full h-full"
                            />
                          </div>
                          <div>
                            <div className="hotel-image-wrapper">
                              <ImageFrame
                                src={hotel.roomImage || hotel.hotelImage || '/assets/brands/vietnam_safar.png'}
                                alt={hotel.roomImageAlt || hotel.roomType || hotel.name}
                                variant="editorial"
                                className="w-full h-full"
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

            {shouldShowTier3OnLastPage ? (
              <PdfFooterTier3 documentModel={documentModel} />
            ) : null}
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
  const options = pricing.options;
  const optionCount = options.length;

  return (
    <PdfPage
      documentModel={documentModel}
      scope="pricing"
      borderVariant="none"
      ornamentVariant="none"
      className="pdf-pricing-page"
    >
      <div className={`page-inner ${optionCount === 1 ? 'pdf-pricing-page-inner--hero' : ''}`}>
        <header className="pdf-pricing__header">
          {pricing.kicker ? (
            <Kicker variant="chapterKicker" tone="accent">{pricing.kicker}</Kicker>
          ) : null}
          <div style={{ margin: '4px 0 6px' }}>
            <DisplayTitle as="h2" variant="chapterTitle">
              {pricing.title}
            </DisplayTitle>
          </div>
          {pricing.description && textValue(pricing.description) ? (
            <BodyCopy variant="bodySm" tone="muted">
              {pricing.description}
            </BodyCopy>
          ) : null}
        </header>

        {optionCount === 1 ? (
          (() => {
            const rawGroupTotal = textValue(options[0].groupTotalPrice);
            const cleanGroupTotal = rawGroupTotal.replace(/\s*(group total|tổng đoàn)\s*$/i, '').trim();
            const groupTotalLabelStr = textValue(options[0].groupTotalLabel) || 'GROUP TOTAL';

            return (
              <div className="pdf-pricing-hero">
                {options[0].label ? (
                  <DisplayTitle as="h3" variant="investmentComparisonTitle" tone="accent" className="pdf-pricing-hero__label">
                    {options[0].label}
                  </DisplayTitle>
                ) : null}
                <div className="pdf-pricing-hero__price-block">
                  <PriceText variant="investmentHeroValue" className="pdf-pricing-hero__amount">
                    {cleanGroupTotal || options[0].groupTotalPrice}
                  </PriceText>
                  <div className={`pdf-pricing-hero__price-label ${getTypographyClassName('overline')}`}>
                    {groupTotalLabelStr}
                  </div>
                </div>
                <div className="pdf-pricing-hero__meta">
                  {options[0].perAdultPrice && options[0].perChildPrice ? (
                    <div className="flex flex-col gap-0.5 items-center">
                      <div className="flex items-center justify-center gap-3">
                        <div className={`pdf-pricing-hero__pax ${getTypographyClassName('investmentHeroMeta')}`}>
                          {textValue(options[0].perAdultPrice)}
                        </div>
                        <div className={`pdf-pricing-hero__pax ${getTypographyClassName('investmentHeroMeta')}`}>
                          {textValue(options[0].perChildPrice)}
                        </div>
                      </div>
                      {options[0].pricingBreakdown && textValue(options[0].pricingBreakdown) ? (
                        <div className={getTypographyClassName('caption')}>
                          {textValue(options[0].pricingBreakdown)}
                        </div>
                      ) : null}
                    </div>
                  ) : options[0].perTravelerPrice && textValue(options[0].perTravelerPrice) ? (
                    <div className={`pdf-pricing-hero__pax ${getTypographyClassName('investmentHeroMeta')}`}>
                      {textValue(options[0].perTravelerPrice)}
                    </div>
                  ) : null}
                  {options[0].description && textValue(options[0].description) ? (
                    <BodyCopy variant="bodySm" tone="muted" className="pdf-pricing-hero__desc">
                      {options[0].description}
                    </BodyCopy>
                  ) : null}
                </div>
              </div>
            );
          })()
        ) : optionCount === 2 ? (
          <div className="pdf-pricing-comparison">
            {options.map((option: PriceOptionViewModel, index: number) => {
              const badgeStr = textValue(option.badge) || (option.isSelection ? 'OUR SELECTION' : '');
              const groupTotalLabelStr = textValue(option.groupTotalLabel) || 'GROUP TOTAL';
              const isLast = index === options.length - 1;

              return (
                <article
                  key={option.index || textValue(option.label) || index}
                  className={`pdf-pricing-comparison__col ${!isLast ? 'pdf-pricing-comparison__col--bordered' : ''}`}
                >
                  <div className="pdf-pricing-comparison__header">
                    <div className="pdf-pricing-comparison__title-line">
                      <DisplayTitle as="h3" variant="investmentComparisonTitle" className="pdf-pricing-comparison__title">
                        {option.label}
                      </DisplayTitle>
                      {badgeStr ? (
                        <span className={`pdf-pricing-comparison__badge ${getTypographyClassName('investmentSelectionText')}`}>
                          {badgeStr}
                        </span>
                      ) : null}
                    </div>
                    {option.description && textValue(option.description) ? (
                      <BodyCopy variant="bodySm" tone="muted" className="pdf-pricing-comparison__desc">
                        {option.description}
                      </BodyCopy>
                    ) : null}
                  </div>

                  <div className="pdf-pricing-comparison__price">
                    <PriceText variant="investmentValue" className="pdf-pricing-comparison__amount">
                      {option.groupTotalPrice}
                    </PriceText>
                    <div className={`pdf-pricing-comparison__price-label ${getTypographyClassName('overline')}`}>
                      {groupTotalLabelStr}
                    </div>
                    {option.perAdultPrice && option.perChildPrice ? (
                      <div className="flex flex-col gap-0.5">
                        <div className={`pdf-pricing-comparison__pax ${getTypographyClassName('caption')}`}>
                          {textValue(option.perAdultPrice)}
                        </div>
                        <div className={`pdf-pricing-comparison__pax ${getTypographyClassName('caption')}`}>
                          {textValue(option.perChildPrice)}
                        </div>
                        {option.pricingBreakdown && textValue(option.pricingBreakdown) ? (
                          <div className={getTypographyClassName('caption')}>
                            {textValue(option.pricingBreakdown)}
                          </div>
                        ) : null}
                      </div>
                    ) : option.perTravelerPrice && textValue(option.perTravelerPrice) ? (
                      <div className={`pdf-pricing-comparison__pax ${getTypographyClassName('caption')}`}>
                        {textValue(option.perTravelerPrice)}
                      </div>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="pdf-pricing-collection">
            {options.map((option: PriceOptionViewModel, index: number) => {
              const displayIdx = textValue(option.displayIndex) || (index + 1 < 10 ? `0${index + 1}` : `${index + 1}`);
              const badgeStr = textValue(option.badge) || (option.isSelection ? 'OUR SELECTION' : '');
              const groupTotalLabelStr = textValue(option.groupTotalLabel) || 'GROUP TOTAL';

              return (
                <article
                  key={option.index || displayIdx || textValue(option.label)}
                  className="pdf-pricing-row"
                >
                  <div className="pdf-pricing-row__main">
                    <div className={`pdf-pricing-row__index ${getTypographyClassName('overline')}`}>
                      {displayIdx}
                    </div>
                    <div className="pdf-pricing-row__identity">
                      <div className="pdf-pricing-row__title-line">
                        <DisplayTitle as="h3" variant="investmentTitle" className="pdf-pricing-row__title">
                          {option.label}
                        </DisplayTitle>
                        {badgeStr ? (
                          <span className={`pdf-pricing-row__badge ${getTypographyClassName('investmentSelectionText')}`}>
                            {badgeStr}
                          </span>
                        ) : null}
                      </div>
                      {option.description && textValue(option.description) ? (
                        <BodyCopy variant="bodySm" tone="muted" className="pdf-pricing-row__desc">
                          {option.description}
                        </BodyCopy>
                      ) : null}
                    </div>
                  </div>

                  <div className="pdf-pricing-row__price">
                    <PriceText variant="investmentValue" className="pdf-pricing-row__amount">
                      {option.groupTotalPrice}
                    </PriceText>
                    <div className={`pdf-pricing-row__price-label ${getTypographyClassName('overline')}`}>
                      {groupTotalLabelStr}
                    </div>
                    {option.perAdultPrice && option.perChildPrice ? (
                      <div className="flex flex-col gap-0.5 items-end">
                        <div className={`pdf-pricing-row__pax ${getTypographyClassName('caption')}`}>
                          {textValue(option.perAdultPrice)}
                        </div>
                        <div className={`pdf-pricing-row__pax ${getTypographyClassName('caption')}`}>
                          {textValue(option.perChildPrice)}
                        </div>
                        {option.pricingBreakdown && textValue(option.pricingBreakdown) ? (
                          <div className={getTypographyClassName('caption')}>
                            {textValue(option.pricingBreakdown)}
                          </div>
                        ) : null}
                      </div>
                    ) : option.perTravelerPrice && textValue(option.perTravelerPrice) ? (
                      <div className={`pdf-pricing-row__pax ${getTypographyClassName('caption')}`}>
                        {textValue(option.perTravelerPrice)}
                      </div>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {note && textValue(note) ? (
          <div className="pdf-pricing-basis">
            <div className="pdf-pricing-basis__divider-wrapper">
              <Image
                src="/assets/brands/indochine_icon/line_divider.svg"
                alt=""
                width={691}
                height={19}
                unoptimized
                className="pdf-pricing-basis__divider"
              />
            </div>
            <div className="pdf-pricing-basis__content">
              {noteLabel && textValue(noteLabel) ? (
                <div className={`pdf-pricing-basis__label ${getTypographyClassName('overline')}`}>
                  {textValue(noteLabel)}
                </div>
              ) : null}
              <BodyCopy variant="bodySm" tone="muted" className="pdf-pricing-basis__text">
                {note}
              </BodyCopy>
            </div>
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
          <Kicker variant="chapterKicker" tone="accent">{details.kicker || 'Package Inclusions & Exclusions'}</Kicker>
          <div style={{ margin: '4px 0 6px' }}>
            <DisplayTitle as="h2" variant="chapterTitle">
              {details.title}
            </DisplayTitle>
          </div>
          {details.inclusionsLead && textValue(details.inclusionsLead) ? (
            <div style={{ marginBottom: '14px' }}>
              <BodyCopy variant="bodySm" tone="muted">
                {details.inclusionsLead}
              </BodyCopy>
            </div>
          ) : null}
          <div className="pdf-details__two-col">
            <div className="pdf-details__panel pdf-details__panel--inclusions">
              <div>
                <Kicker variant="overline" tone="accent">
                  {details.inclusionsTitle || 'Inclusions'}
                </Kicker>
              </div>
              <ul>
                {details.inclusions.map((item, index) => (
                  <li key={`inc-${index}`} className="pdf-details__item">
                    <span className="pdf-details__icon pdf-details__icon--check" aria-hidden="true">✓</span>
                    <div className="pdf-details__text">
                      <BodyCopy variant="bodySm">{inclusionText(item)}</BodyCopy>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="pdf-details__panel pdf-details__panel--exclusions">
              <div>
                <Kicker variant="overline" tone="muted">
                  {details.exclusionsTitle || 'Exclusions'}
                </Kicker>
              </div>
              <ul>
                {details.exclusions.map((item, index) => (
                  <li key={`exc-${index}`} className="pdf-details__item">
                    <span className="pdf-details__icon pdf-details__icon--dash" aria-hidden="true">—</span>
                    <div className="pdf-details__text">
                      <BodyCopy variant="bodySm">{item}</BodyCopy>
                    </div>
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
          <div className="pdf-terms__header" style={{ marginBottom: '16px' }}>
            <Kicker variant="chapterKicker" tone="accent">{terms.kicker || 'Important Notes'}</Kicker>
            <div style={{ margin: '4px 0 6px' }}>
              <DisplayTitle as="h2" variant="chapterTitle">
                {terms.title}
              </DisplayTitle>
            </div>
            {terms.description && textValue(terms.description) ? (
              <BodyCopy variant="bodySm" tone="muted">
                {terms.description}
              </BodyCopy>
            ) : null}
          </div>

          <div className="pdf-terms__rows">
            {terms.terms.map((term, index) => (
              <div key={`term-${index}`} className="pdf-terms__row">
                <div className="pdf-terms__row-label">
                  <span className={`pdf-terms__row-num ${getTypographyClassName('caption')}`}>
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <LabelText variant="termLabel" tone="accent">
                    {term.label}
                  </LabelText>
                </div>
                <div className="pdf-terms__row-content">
                  <BodyCopy variant="termBody" className="whitespace-pre-line">
                    {term.bodyRichText}
                  </BodyCopy>
                </div>
              </div>
            ))}
          </div>
        </div>
      </PdfPage>
    </>
  );
}

function PdfDesigner({ documentModel }: { documentModel: DisplayDocument }) {
  const designer = documentModel.page.designer;
  const contactActions =
    designer.contactActions && designer.contactActions.length > 0
      ? designer.contactActions
      : [
          {
            label: 'CHAT ON WHATSAPP',
            href: 'https://wa.me/84913393119',
            emphasis: 'primary' as const,
            caption: '+84 913 393 119',
          },
          {
            label: 'SEND AN EMAIL',
            href: 'mailto:sales@capellatravel.com',
            emphasis: 'secondary' as const,
            caption: 'sales@capellatravel.com',
          },
        ];

  return (
    <PdfPage
      documentModel={documentModel}
      scope="designer"
      borderVariant="none"
      ornamentVariant="cyclo"
    >
      <div className="page-inner">
        <div className="pdf-designer__circle-decor-1" aria-hidden="true" />
        <div className="pdf-designer__circle-decor-2" aria-hidden="true" />

        {/* 1. Header (Căn lề trái 100%, neo trên đỉnh trang) */}
        <header className="pdf-designer__header">
          <Kicker variant="chapterKicker" tone="accent">
            {designer.kicker}
          </Kicker>
          <div style={{ margin: '4px 0 6px' }}>
            <DisplayTitle as="h2" variant="designerTitle">
              {designer.title}
            </DisplayTitle>
          </div>
          <BodyCopy variant="bodySm" tone="muted">
            {designer.ctaBody && textValue(designer.ctaBody)
              ? designer.ctaBody
              : 'Contact your travel designer to personalize this itinerary.'}
          </BodyCopy>
          <hr className="pdf-designer__header-rule" />
        </header>

        {/* 2. Avatar & Designer Identity (Chính giữa trang, không khung trắng) */}
        <div className="pdf-designer__body">
          <div className="pdf-designer__avatar-frame">
            <Image
              src={designer.avatar || ''}
              alt={textValue(designer.avatarAlt) || textValue(designer.name)}
              fill
              sizes="260px"
              className="object-cover"
              unoptimized
            />
          </div>

          <div className="pdf-designer__info">
            <DisplayTitle as="h3" variant="signatureName">
              {designer.name}
            </DisplayTitle>
            {designer.subtitle ? (
              <MetaText variant="signatureMeta" tone="accent">
                {designer.subtitle}
              </MetaText>
            ) : null}
            <div style={{ marginTop: '2px', marginBottom: '2px' }}>
              <Kicker variant="label">
                {designer.signatureLabel || 'TRAVEL DESIGNER'}
              </Kicker>
            </div>
            <div className="pdf-designer__divider" aria-hidden="true" />
            {designer.experienceNote ? (
              <QuoteText variant="quote" tone="default" className="pdf-designer__experience">
                {designer.experienceNote}
              </QuoteText>
            ) : null}
          </div>

          {/* 3. Quote triết lý thiết kế trong dấu ngoặc kép */}
          {designer.quote && textValue(designer.quote) ? (
            <div className="pdf-designer__quote-wrap">
              <QuoteText variant="designerQuote" tone="default">
                {`“${textValue(designer.quote)}”`}
              </QuoteText>
            </div>
          ) : null}

          {/* 4. Action Buttons (Căn giữa hàng ngang) */}
          <div className="pdf-designer__actions">
            {contactActions.map((action, index) => {
              const isPrimary = action.emphasis === 'primary' || index === 0;
              const btnClass = isPrimary ? 'pdf-designer__whatsapp-btn' : 'pdf-designer__email-btn';
              const captionStr = textValue(action.caption);
              const isWhatsapp = isPrimary || action.href.includes('wa.me');

              return (
                <div key={`designer-act-${index}`} className="pdf-designer__action-col">
                  <a
                    href={action.href}
                    className={`${btnClass} ${getTypographyClassName('buttonPrimary')}`}
                  >
                    {textValue(action.label)}
                  </a>
                  {captionStr ? (
                    <MetaText
                      variant="signatureMeta"
                      tone="accent"
                      className="pdf-designer__action-caption"
                    >
                      {isWhatsapp && !captionStr.toLowerCase().startsWith('no.')
                        ? `No.: ${captionStr}`
                        : !isWhatsapp && !captionStr.toLowerCase().startsWith('email:')
                          ? `Email: ${captionStr}`
                          : captionStr}
                    </MetaText>
                  ) : null}
                </div>
              );
            })}
          </div>

          {/* 5. Closing Statement / Footer Note */}
          {documentModel.page.footer.text && textValue(documentModel.page.footer.text) ? (
            <div className="pdf-designer__closing-footer">
              <QuoteText variant="quote" tone="default" className="pdf-designer__closing-text">
                {documentModel.page.footer.text}
              </QuoteText>
            </div>
          ) : null}
        </div>
      </div>
    </PdfPage>
  );
}

export function PdfBrochureDocument({ documentModel }: { documentModel: DisplayDocument }) {
  const stays = documentModel.page.staysDivider;
  const itin = documentModel.page.itineraryDivider;
  const journeyTogether = documentModel.page.journeyTogetherDivider;
  const showItinDivider = Boolean(itin.showDivider);

  return (
    <div className="pdf-brochure" data-pdf-compositor="a4-v2">
      <PdfCover documentModel={documentModel} />
      <PdfLetter documentModel={documentModel} />
      <PdfRouteMap documentModel={documentModel} />
      {showItinDivider ? (
        <PdfChapterDivider
          documentModel={documentModel}
          scope="itineraryDivider"
          image={itin.image ?? ''}
          imageAlt={itin.imageAlt ?? itin.title}
          kicker={itin.kicker}
          title={itin.title}
          tagline={itin.tagline}
        />
      ) : null}
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
      <PdfChapterDivider
        documentModel={documentModel}
        scope="journeyTogetherDivider"
        image={journeyTogether.image}
        imageAlt={journeyTogether.imageAlt}
        kicker={journeyTogether.kicker}
        title={journeyTogether.title}
        tagline={journeyTogether.tagline}
        closing={journeyTogether.closing}
      />
      <PdfPricing documentModel={documentModel} />
      <PdfDetails documentModel={documentModel} />
      <PdfDesigner documentModel={documentModel} />
    </div>
  );
}
