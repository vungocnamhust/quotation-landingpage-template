import Image from 'next/image';
import type { CSSProperties, ReactNode } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder.ts';
import type { InclusionItemViewModel, ItineraryDayViewModel, TextValue } from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import { AvatarFrame, BodyCopy, DisplayTitle, ImageFrame, Kicker, MetaText, PriceText, QuoteText } from './atoms.tsx';
import RouteMapClientIsland from './RouteMapClientIsland.tsx';

type PdfPageProps = {
  documentModel: DisplayDocument;
  scope: string;
  children: ReactNode;
  className?: string;
  slogan?: boolean;
};

function PdfPage({ documentModel, scope, children, className = '', slogan = false }: PdfPageProps) {
  const colorScope = documentModel.colors.sections[scope as keyof typeof documentModel.colors.sections];
  const brandName = textValue(documentModel.page.footer.text) || documentModel.tokens.brandKey || 'Indochine';
  const quotationRef = [brandName, documentModel.quotationNumber].filter(Boolean).join(' · ');
  const showPageHeader = scope !== 'hero';

  return (
    <section
      className={`pdf-brochure-page display-color-scope display-color-scope--${colorScope?.id ?? 'paper'} ${className}`}
      style={colorScope?.style as CSSProperties}
      data-pdf-page={scope}
    >
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
            <span>{brandName} — Luxury Quotation</span>
          </span>
          <span className="ref">{documentModel.quotationNumber}</span>
        </div>
      ) : null}
      <div className="pdf-brochure-page__content">{children}</div>
      {slogan && documentModel.pdfWhitespaceSlogan ? (
        <MetaText variant="footerText" className="pdf-brochure-page__slogan">
          {textValue(documentModel.pdfWhitespaceSlogan)}
        </MetaText>
      ) : null}
      {showPageHeader ? (
        <div className="pdf-brochure-page__footer">
          <MetaText variant="footerText">{`${quotationRef} · Confidential`}</MetaText>
        </div>
      ) : null}
    </section>
  );
}

function PdfCover({ documentModel }: { documentModel: DisplayDocument }) {
  const hero = documentModel.page.hero;
  return (
    <PdfPage documentModel={documentModel} scope="hero" className="pdf-cover">
      <Image src={hero.backgroundImage} alt={textValue(hero.backgroundImageAlt)} data-editable={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.path} data-edit-owner={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.owner} data-edit-mode={typeof hero.backgroundImageAlt === 'string' ? undefined : hero.backgroundImageAlt.mode} fill priority sizes="794px" className="pdf-cover__image" />
      <div className="pdf-cover__veil" />
      <div className="pdf-cover__top">
        <Kicker variant="chapterKicker" tone="inverse">{hero.kicker}</Kicker>
        <DisplayTitle as="h1" variant="hero" tone="inverse">{hero.title}</DisplayTitle>
      </div>
      <div className="pdf-cover__bottom">
        <BodyCopy variant="heroLede" tone="inverse">{hero.lede}</BodyCopy>
        <MetaText variant="heroMetaPrimary" tone="inverse">{hero.metaPrimary}</MetaText>
        <MetaText variant="heroMetaSecondary" tone="inverse">{hero.metaSecondary}</MetaText>
      </div>
    </PdfPage>
  );
}

function PdfLetter({ documentModel }: { documentModel: DisplayDocument }) {
  const letter = documentModel.page.letter;
  return <PdfPage documentModel={documentModel} scope="letter" className="pdf-letter">
    <aside className="pdf-letter__rail">
      <Kicker variant="chapterKicker">{letter.chapterKicker}</Kicker>
      <Image src="/assets/brands/indochine_icon/ruong_bac_thang.svg" alt="" width={100} height={100} className="pdf-letter__ornament" />
    </aside>
    <article className="pdf-letter__body">
      <DisplayTitle as="h2" variant="letterTitle">{letter.title}</DisplayTitle>
      {textValue(letter.highlight) ? <QuoteText variant="letterHighlight">{letter.highlight}</QuoteText> : null}
      <BodyCopy variant="letterBody">{letter.greeting}</BodyCopy>
      <BodyCopy variant="letterBody">{letter.intro}</BodyCopy>
      {letter.body.map((paragraph, index) => <BodyCopy key={index} variant="letterBody">{paragraph}</BodyCopy>)}
      <BodyCopy variant="letterBody">{letter.outro}</BodyCopy>
      <div className="pdf-letter__signature">
        <DisplayTitle as="h3" variant="signatureName">{letter.signatureName}</DisplayTitle>
        <MetaText variant="signatureMeta">{letter.signatureRole}</MetaText>
        {letter.signatureContactLine ? <MetaText variant="signatureMeta">{letter.signatureContactLine}</MetaText> : null}
      </div>
    </article>
  </PdfPage>;
}

function PdfRouteMap({ documentModel }: { documentModel: DisplayDocument }) {
  const route = documentModel.page.routeMap;
  const quoteText =
    textValue(documentModel.page.footer.secondaryMeta) ||
    'Your journeys through Vietnam and Indochina, shaped around living heritage, quiet landscapes and the luxury of time.';
  const count = Math.max(route.segments.length, 1);

  return (
    <PdfPage documentModel={documentModel} scope="routeMap" className="pdf-route">
      <header>
        <Kicker variant="chapterKicker">{route.title}</Kicker>
        <DisplayTitle as="h2" variant="routeMapTitle">
          {route.title}
        </DisplayTitle>
      </header>
      <div className="pdf-route__map">
        <RouteMapClientIsland
          viewModel={route}
          typography={{
            title: 'routeMapTitle',
            body: 'routeMapBody',
            kicker: 'chapterKicker',
            metaPrimary: 'timelineTitle',
            metaSecondary: 'timelineMeta',
          }}
          mapColors={{
            route: 'var(--color-accent)',
            marker: 'var(--color-accent)',
            activeMarker: 'var(--color-accent)',
          }}
          viewMode="pdf"
        />
      </div>
      <div className={`pdf-route__summary pdf-route__summary--${count === 1 ? 'single' : 'multiple'}`}>
        {route.segments.map((segment) => (
          <article key={segment.sequence}>
            <MetaText variant="timelineMeta">{segment.duration ?? ''}</MetaText>
            <DisplayTitle as="h3" variant="timelineTitle">
              {segment.city}
            </DisplayTitle>
            <BodyCopy variant="bodySm">{segment.description}</BodyCopy>
            {segment.hotelName ? <MetaText variant="timelineMeta">{segment.hotelName}</MetaText> : null}
          </article>
        ))}
      </div>
      <div className="pdf-route__quote-banner">
        <div className="pdf-route__quote-rule" />
        <blockquote className="pdf-route__quote-text">&ldquo;{quoteText}&rdquo;</blockquote>
        <div className="pdf-route__quote-rule" />
      </div>
    </PdfPage>
  );
}

function dayImages(day: ItineraryDayViewModel): Array<{ src: string; alt: TextValue }> {
  return day.carouselImages.map((src, index) => ({ src, alt: day.carouselImageAlts[index] ?? day.title })).filter((image, index, images) => Boolean(image.src) && images.findIndex((candidate) => candidate.src === image.src) === index).slice(0, 3);
}

function PdfItineraryDay({ day }: { day: ItineraryDayViewModel }) {
  const images = dayImages(day);
  return (
    <article className="pdf-itinerary-day">
      <header>
        <Kicker variant="chapterKicker">{day.dayLabel}</Kicker>
        <DisplayTitle as="h3" variant="dayTitle">
          {day.title}
        </DisplayTitle>
      </header>
      <div className="pdf-itinerary-day__grid">
        <ImageFrame src={images[0]?.src ?? ''} alt={images[0]?.alt ?? day.title} variant="editorial" className="pdf-itinerary-day__hero" />
        <div className="pdf-itinerary-day__thumbs">
          <ImageFrame src={images[1]?.src ?? ''} alt={images[1]?.alt ?? day.title} variant="editorial" />
          <ImageFrame src={images[2]?.src ?? ''} alt={images[2]?.alt ?? day.title} variant="editorial" />
        </div>
      </div>
      <div className="pdf-itinerary-day__copy">
        {day.description.map((paragraph, index) => (
          <BodyCopy key={`day-para-${index}`} variant="dayBody">
            {paragraph}
          </BodyCopy>
        ))}
      </div>
    </article>
  );
}

function PdfItinerary({ documentModel }: { documentModel: DisplayDocument }) {
  const days = documentModel.page.itinerary.days;
  const pages = Array.from({ length: Math.ceil(days.length / 2) }, (_, index) => days.slice(index * 2, index * 2 + 2));
  return (
    <>
      {pages.map((pair, pageIndex) => (
        <PdfPage key={`itinerary-page-${pageIndex}`} documentModel={documentModel} scope="itinerary" className="pdf-itinerary" slogan={pair.length === 1}>
          <div className="pdf-itinerary__pair">
            {pair.map((day) => (
              <PdfItineraryDay key={textValue(day.dayLabel) || textValue(day.title)} day={day} />
            ))}
          </div>
        </PdfPage>
      ))}
    </>
  );
}

function PdfDivider({
  documentModel,
  image,
  imageAlt,
  kicker,
  title,
  tagline,
  scope,
}: {
  documentModel: DisplayDocument;
  image: string;
  imageAlt: TextValue;
  kicker: TextValue;
  title: TextValue;
  tagline?: TextValue;
  scope: string;
}) {
  const brandName = textValue(documentModel.page.footer.text) || documentModel.tokens.brandKey || 'Indochine';
  const reference = [brandName, documentModel.quotationNumber].filter(Boolean).join(' · ');
  const durationText = textValue(documentModel.page.hero.metaPrimary);
  const routeText = documentModel.page.routeMap.segments.map((s) => s.city).filter(Boolean).join(' — ');

  return (
    <section className="pdf-brochure-page pdf-chapter-divider" data-pdf-page={scope}>
      {image ? (
        <Image
          src={image}
          alt={textValue(imageAlt)}
          fill
          priority
          unoptimized
          className="pdf-chapter-divider__bg"
        />
      ) : null}
      <div className="pdf-chapter-divider__veil" />
      <div className="pdf-chapter-divider-top">
        <Kicker variant="chapterKicker" tone="inverse" className="pdf-chapter-divider-kicker">
          {kicker}
        </Kicker>
        <DisplayTitle as="h2" variant="chapterTitle" tone="inverse" className="pdf-chapter-divider-title">
          {title}
        </DisplayTitle>
      </div>
      <div className="pdf-chapter-divider-bottom">
        {tagline && textValue(tagline) ? (
          <BodyCopy variant="bodyLg" tone="inverse" className="pdf-chapter-divider-tagline">
            {tagline}
          </BodyCopy>
        ) : null}
        {durationText || routeText ? (
          <div className="pdf-chapter-divider-stats">
            {durationText ? (
              <div>
                <span className="label">Duration</span>
                <span>{durationText}</span>
              </div>
            ) : null}
            {routeText ? (
              <div>
                <span className="label">Route</span>
                <span>{routeText}</span>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="pdf-chapter-divider-footer">
        <span>{reference}</span>
        <span>{textValue(kicker)}</span>
      </div>
    </section>
  );
}

function chunkHotels<T>(cards: T[]): T[][] {
  const n = cards.length;
  if (n <= 3) return [cards];
  if (n === 4) return [cards.slice(0, 2), cards.slice(2, 4)];
  if (n === 5) return [cards.slice(0, 3), cards.slice(3, 5)];
  const chunks: T[][] = [];
  for (let i = 0; i < n; i += 3) {
    chunks.push(cards.slice(i, i + 3));
  }
  return chunks;
}

function PdfHotels({ documentModel }: { documentModel: DisplayDocument }) {
  const roomNotes = documentModel.page.hotels.roomNotes;
  const cards = documentModel.page.hotels.cards;
  const hotelChunks = chunkHotels(cards);

  return (
    <>
      {hotelChunks.map((chunk, pageIndex) => {
        const isLastPage = pageIndex === hotelChunks.length - 1;
        return (
          <PdfPage key={`hotels-page-${pageIndex}`} documentModel={documentModel} scope="hotels" className="pdf-hotel" slogan>
            <div className="hotel-plan-container" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {chunk.map((hotel) => {
                const globalIndex = cards.indexOf(hotel);
                const telephone = hotel.telephone;
                const telephonePrefix = hotel.telephonePrefix;
                return (
                  <article key={textValue(hotel.name) || `hotel-${globalIndex}`} className={`pdf-hotel__card ${hotel.layoutParity === 'even' ? 'is-even' : ''}`} data-hotel-index={globalIndex}>
                    <header>
                      <MetaText variant="hotelMeta">{hotel.city}</MetaText>
                      <DisplayTitle as="h2" variant="hotelTitle">{hotel.name}</DisplayTitle>
                      <MetaText variant="hotelMeta">{hotel.dateRanges.map(textValue).filter(Boolean).join(' · ')}</MetaText>
                    </header>
                    <div className="pdf-hotel__images">
                      <ImageFrame src={hotel.hotelImage} alt={hotel.hotelImageAlt} variant="editorial" />
                      <div>
                        <ImageFrame src={hotel.roomImage} alt={hotel.roomImageAlt} variant="editorial" />
                        <MetaText variant="hotelMeta">{hotel.roomType}</MetaText>
                      </div>
                    </div>
                    {hotel.intro ? <BodyCopy variant="hotelBody">{hotel.intro}</BodyCopy> : null}
                    {telephone && textValue(telephone) ? (
                      <div className={getTypographyClassName('hotelMeta')}>
                        <span {...(typeof telephonePrefix === 'string' || !telephonePrefix ? {} : { 'data-editable': telephonePrefix.path, 'data-edit-owner': telephonePrefix.owner, 'data-edit-mode': telephonePrefix.mode })}>{textValue(telephonePrefix)}</span>{' '}
                        <span {...(typeof telephone === 'string' ? {} : { 'data-editable': telephone.path, 'data-edit-owner': telephone.owner, 'data-edit-mode': telephone.mode })}>{textValue(telephone)}</span>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
            {isLastPage && roomNotes && textValue(roomNotes) ? (
              <div className={getTypographyClassName('bodySm')} style={{ marginTop: '20px' }}>
                <strong>Room Notes &amp; Special Requests:</strong>{' '}
                <span {...(typeof roomNotes === 'string' ? {} : { 'data-editable': roomNotes.path, 'data-edit-owner': roomNotes.owner, 'data-edit-mode': roomNotes.mode })}>{textValue(roomNotes)}</span>
              </div>
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
  return (
    <PdfPage documentModel={documentModel} scope="pricing" className="pdf-pricing">
      <Kicker variant="chapterKicker">{pricing.kicker}</Kicker>
      <DisplayTitle as="h2" variant="investmentTitle">{pricing.title}</DisplayTitle>
      <BodyCopy variant="bodyLg">{pricing.description}</BodyCopy>
      <div className="pdf-pricing__ledger">
        {pricing.options.map((option) => (
          <article key={option.index || textValue(option.displayIndex) || textValue(option.label)} className="pdf-pricing__row">
            <MetaText variant="investmentMeta">{option.displayIndex}</MetaText>
            <div>
              <DisplayTitle as="h3" variant="investmentTitle">{option.label}</DisplayTitle>
              {option.isConfirmedMainOption ? <MetaText variant="investmentMeta">{pricing.confirmedMainOptionLabel}</MetaText> : null}
            </div>
            <div>
              <PriceText variant="investmentValue">{option.perTravelerPrice}</PriceText>
              <MetaText variant="investmentMeta">{option.groupTotalPrice}</MetaText>
            </div>
          </article>
        ))}
      </div>
      {note ? (
        <div className={getTypographyClassName('bodySm')}>
          <span {...(typeof noteLabel === 'string' ? {} : { 'data-editable': noteLabel.path, 'data-edit-owner': noteLabel.owner, 'data-edit-mode': noteLabel.mode })}>{textValue(noteLabel)}</span>{': '}
          <span {...(typeof note === 'string' ? {} : { 'data-editable': note.path, 'data-edit-owner': note.owner, 'data-edit-mode': note.mode })}>{textValue(note)}</span>
        </div>
      ) : null}
    </PdfPage>
  );
}

function inclusionText(item: InclusionItemViewModel): TextValue {
  return typeof item === 'string' || 'value' in item ? item : `${textValue(item.title)} — ${textValue(item.desc)}`;
}

function PdfDetails({ documentModel }: { documentModel: DisplayDocument }) {
  const details = documentModel.page.inclusionsExclusions;
  const terms = documentModel.page.paymentTerms;
  return (
    <>
      <PdfPage documentModel={documentModel} scope="inclusionsExclusions" className="pdf-details">
        <DisplayTitle as="h2" variant="sectionTitle">{details.title}</DisplayTitle>
        <section>
          <DisplayTitle as="h3" variant="termTitle">{details.inclusionsTitle ?? ''}</DisplayTitle>
          {details.inclusions.map((item, index) => (
            <BodyCopy key={`inc-${index}`} variant="bodyMd">{inclusionText(item)}</BodyCopy>
          ))}
        </section>
        <section>
          <DisplayTitle as="h3" variant="termTitle">{details.exclusionsTitle ?? ''}</DisplayTitle>
          {details.exclusions.map((item, index) => (
            <BodyCopy key={`exc-${index}`} variant="bodyMd">{item}</BodyCopy>
          ))}
        </section>
      </PdfPage>
      <PdfPage documentModel={documentModel} scope="paymentTerms" className="pdf-terms">
        <div>
          <Kicker variant="chapterKicker">{terms.kicker}</Kicker>
          <DisplayTitle as="h2" variant="termTitle">{terms.title}</DisplayTitle>
          <BodyCopy variant="termBody">{terms.description}</BodyCopy>
        </div>
        <div>
          {terms.terms.map((term, index) => (
            <article key={`term-${index}`}>
              <MetaText variant="termLabel">{term.label}</MetaText>
              <BodyCopy variant="termBody">{term.bodyRichText}</BodyCopy>
            </article>
          ))}
        </div>
      </PdfPage>
    </>
  );
}

function PdfDesigner({ documentModel }: { documentModel: DisplayDocument }) {
  const designer = documentModel.page.designer;
  return <PdfPage documentModel={documentModel} scope="designer" className="pdf-designer"><AvatarFrame src={designer.avatar} alt={designer.avatarAlt} variant="editorial" className="pdf-designer__avatar" /><div><Kicker variant="chapterKicker">{designer.kicker}</Kicker><DisplayTitle as="h2" variant="designerTitle">{designer.title}</DisplayTitle><QuoteText variant="designerQuote">{designer.quote}</QuoteText>{designer.ctaBody && textValue(designer.ctaBody) ? <BodyCopy variant="bodyMd">{designer.ctaBody}</BodyCopy> : null}<DisplayTitle as="h3" variant="signatureName">{designer.name}</DisplayTitle>{designer.subtitle ? <MetaText variant="signatureMeta">{designer.subtitle}</MetaText> : null}<BodyCopy variant="bodyMd">{designer.experienceNote}</BodyCopy></div></PdfPage>;
}

export function PdfBrochureDocument({ documentModel }: { documentModel: DisplayDocument }) {
  const stays = documentModel.page.staysDivider;
  return <div className="pdf-brochure" data-pdf-compositor="a4-v1">
    <PdfCover documentModel={documentModel} />
    <PdfLetter documentModel={documentModel} />
    <PdfRouteMap documentModel={documentModel} />
    <PdfItinerary documentModel={documentModel} />
    <PdfDivider documentModel={documentModel} scope="itineraryDivider" image={documentModel.page.itineraryDivider.image ?? ''} imageAlt={documentModel.page.itineraryDivider.imageAlt ?? documentModel.page.itineraryDivider.title} kicker={documentModel.page.itineraryDivider.kicker} title={documentModel.page.itineraryDivider.title} tagline={documentModel.page.itineraryDivider.tagline} />
    <PdfHotels documentModel={documentModel} />
    <PdfDivider documentModel={documentModel} scope="staysDivider" image={stays.image} imageAlt={stays.imageAlt} kicker={stays.kicker} title={stays.pdfTitle} tagline={stays.closing} />
    <PdfPricing documentModel={documentModel} />
    <PdfDetails documentModel={documentModel} />
    <PdfDesigner documentModel={documentModel} />
  </div>;
}
