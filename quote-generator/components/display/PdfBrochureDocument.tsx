import Image from 'next/image';
import type { CSSProperties, ReactNode } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder';
import type { InclusionItemViewModel, ItineraryDayViewModel, TextValue } from '../../display/types';
import { textValue } from '../../display/types';
import { getTypographyClassName } from '../../config/typography';
import { AvatarFrame, BodyCopy, DisplayTitle, editableProps, ImageFrame, Kicker, MetaText, PriceText, QuoteText } from './atoms';

type PdfPageProps = {
  documentModel: DisplayDocument;
  scope: string;
  children: ReactNode;
  className?: string;
  slogan?: boolean;
};

function PdfPage({ documentModel, scope, children, className = '', slogan = false }: PdfPageProps) {
  const colorScope = documentModel.colors.sections[scope as keyof typeof documentModel.colors.sections];
  const reference = [textValue(documentModel.page.footer.secondaryMeta), documentModel.quotationNumber].filter(Boolean).join(' · ');
  return (
    <section
      className={`pdf-brochure-page display-color-scope display-color-scope--${colorScope.id} ${className}`}
      style={colorScope.style as CSSProperties}
      data-pdf-page={scope}
    >
      <div className="pdf-brochure-page__content">{children}</div>
      {slogan ? <MetaText variant="footerText" className="pdf-brochure-page__slogan">{documentModel.pdfWhitespaceSlogan}</MetaText> : null}
      <MetaText variant="footerText" className="pdf-brochure-page__footer">{reference}</MetaText>
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
        <MetaText variant="footerText" tone="inverse">{hero.footerMeta}</MetaText>
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
  const footerSecondaryMeta = documentModel.page.footer.secondaryMeta ?? '';
  const count = Math.max(route.segments.length, 1);
  return <PdfPage documentModel={documentModel} scope="routeMap" className="pdf-route">
    <header><Kicker variant="chapterKicker">{route.title}</Kicker><DisplayTitle as="h2" variant="routeMapTitle">{route.title}</DisplayTitle><BodyCopy variant="routeMapBody">{route.description}</BodyCopy></header>
    <div className="pdf-route__map">
      <svg viewBox="0 0 1000 250" role="img" aria-label={textValue(route.overviewAriaLabel)} {...editableProps(route.overviewAriaLabel)}>
        <path d="M90 145 C260 35, 390 220, 560 105 S790 70, 910 135" className="pdf-route__line" />
        {route.segments.map((segment, index) => <g key={segment.sequence} transform={`translate(${count === 1 ? 500 : 90 + (820 * index) / (count - 1)} ${count === 1 ? 125 : 135})`}><circle r="18" className="pdf-route__marker" /><text y="6" textAnchor="middle" className="pdf-route__marker-text">{textValue(segment.dayLabel)}</text></g>)}
      </svg>
    </div>
    <div className={`pdf-route__summary pdf-route__summary--${count === 1 ? 'single' : 'multiple'}`}>
      {route.segments.map((segment) => <article key={segment.sequence}><MetaText variant="timelineMeta">{segment.duration ?? ''}</MetaText><DisplayTitle as="h3" variant="timelineTitle">{segment.city}</DisplayTitle><BodyCopy variant="bodySm">{segment.description}</BodyCopy><MetaText variant="timelineMeta">{segment.hotelName ?? ''}</MetaText></article>)}
    </div>
    <QuoteText variant="quote" className="pdf-route__quote">
      <span {...editableProps(footerSecondaryMeta)}>{textValue(footerSecondaryMeta)}</span>
      {footerSecondaryMeta && documentModel.quotationNumber ? ' · ' : ''}
      {documentModel.quotationNumber}
    </QuoteText>
  </PdfPage>;
}

function dayImages(day: ItineraryDayViewModel): Array<{ src: string; alt: TextValue }> {
  return day.carouselImages.map((src, index) => ({ src, alt: day.carouselImageAlts[index] ?? day.title })).filter((image, index, images) => Boolean(image.src) && images.findIndex((candidate) => candidate.src === image.src) === index).slice(0, 3);
}

function PdfItineraryDay({ day }: { day: ItineraryDayViewModel }) {
  const images = dayImages(day);
  return <article className="pdf-itinerary-day">
    <header><Kicker variant="chapterKicker">{day.dayLabel}</Kicker><DisplayTitle as="h3" variant="dayTitle">{day.title}</DisplayTitle></header>
    <div className="pdf-itinerary-day__grid"><ImageFrame src={images[0]?.src ?? ''} alt={images[0]?.alt ?? day.title} variant="editorial" className="pdf-itinerary-day__hero" /><div className="pdf-itinerary-day__thumbs"><ImageFrame src={images[1]?.src ?? ''} alt={images[1]?.alt ?? day.title} variant="editorial" /><ImageFrame src={images[2]?.src ?? ''} alt={images[2]?.alt ?? day.title} variant="editorial" /></div></div>
    <div className="pdf-itinerary-day__copy">{day.description.slice(0, 2).map((paragraph, index) => <BodyCopy key={index} variant="dayBody">{paragraph}</BodyCopy>)}</div>
  </article>;
}

function PdfItinerary({ documentModel }: { documentModel: DisplayDocument }) {
  const days = documentModel.page.itinerary.days;
  const pages = Array.from({ length: Math.ceil(days.length / 2) }, (_, index) => days.slice(index * 2, index * 2 + 2));
  return <>{pages.map((pair, index) => <PdfPage key={index} documentModel={documentModel} scope="itinerary" className="pdf-itinerary" slogan={pair.length === 1}><div className="pdf-itinerary__pair">{pair.map((day) => <PdfItineraryDay key={textValue(day.dayLabel)} day={day} />)}</div></PdfPage>)}</>;
}

function PdfDivider({ documentModel, image, imageAlt, kicker, title, tagline, scope }: { documentModel: DisplayDocument; image: string; imageAlt: TextValue; kicker: TextValue; title: TextValue; tagline: TextValue; scope: string }) {
  return <PdfPage documentModel={documentModel} scope={scope} className="pdf-divider"><ImageFrame src={image} alt={imageAlt} variant="editorial" className="pdf-divider__image" /><div className="pdf-divider__copy"><Kicker variant="chapterKicker">{kicker}</Kicker><DisplayTitle as="h2" variant="chapterTitle">{title}</DisplayTitle><BodyCopy variant="bodyLg">{tagline}</BodyCopy></div></PdfPage>;
}

function PdfHotels({ documentModel }: { documentModel: DisplayDocument }) {
  const roomNotes = documentModel.page.hotels.roomNotes;
  const cards = documentModel.page.hotels.cards;
  return <>{cards.map((hotel, index) => {
    const telephone = hotel.telephone;
    const telephonePrefix = hotel.telephonePrefix;
    const isLast = index === cards.length - 1;
    return <PdfPage key={textValue(hotel.name)} documentModel={documentModel} scope="hotels" className="pdf-hotel" slogan>
    <article className={`pdf-hotel__card ${hotel.layoutParity === 'even' ? 'is-even' : ''}`} data-hotel-index={index}>
      <header><MetaText variant="hotelMeta">{hotel.city}</MetaText><DisplayTitle as="h2" variant="hotelTitle">{hotel.name}</DisplayTitle><MetaText variant="hotelMeta">{hotel.dateRanges.map(textValue).filter(Boolean).join(' · ')}</MetaText></header>
      <div className="pdf-hotel__images"><ImageFrame src={hotel.hotelImage} alt={hotel.hotelImageAlt} variant="editorial" /><div><ImageFrame src={hotel.roomImage} alt={hotel.roomImageAlt} variant="editorial" /><MetaText variant="hotelMeta">{hotel.roomType}</MetaText></div></div>
      {hotel.intro ? <BodyCopy variant="hotelBody">{hotel.intro}</BodyCopy> : null}
      {telephone && textValue(telephone) ? <div className={getTypographyClassName('hotelMeta')}><span {...(typeof telephonePrefix === 'string' || !telephonePrefix ? {} : { 'data-editable': telephonePrefix.path, 'data-edit-owner': telephonePrefix.owner, 'data-edit-mode': telephonePrefix.mode })}>{textValue(telephonePrefix)}</span>{' '}<span {...(typeof telephone === 'string' ? {} : { 'data-editable': telephone.path, 'data-edit-owner': telephone.owner, 'data-edit-mode': telephone.mode })}>{textValue(telephone)}</span></div> : null}
      {isLast && roomNotes && textValue(roomNotes) ? <p style={{ marginTop: '15px' }}><strong>Room Notes &amp; Special Requests:</strong> <span {...(typeof roomNotes === 'string' ? {} : { 'data-editable': roomNotes.path, 'data-edit-owner': roomNotes.owner, 'data-edit-mode': roomNotes.mode })}>{textValue(roomNotes)}</span></p> : null}
    </article>
  </PdfPage>; })}</>;
}

function PdfPricing({ documentModel }: { documentModel: DisplayDocument }) {
  const pricing = documentModel.page.pricing;
  const noteLabel = pricing.importantNoteLabel;
  const note = pricing.importantNote;
  return <PdfPage documentModel={documentModel} scope="pricing" className="pdf-pricing"><Kicker variant="chapterKicker">{pricing.kicker}</Kicker><DisplayTitle as="h2" variant="investmentTitle">{pricing.title}</DisplayTitle><BodyCopy variant="bodyLg">{pricing.description}</BodyCopy><div className="pdf-pricing__ledger">{pricing.options.map((option) => <article key={option.index} className="pdf-pricing__row"> <MetaText variant="investmentMeta">{option.displayIndex}</MetaText><div><DisplayTitle as="h3" variant="investmentTitle">{option.label}</DisplayTitle>{option.isConfirmedMainOption ? <MetaText variant="investmentMeta">{pricing.confirmedMainOptionLabel}</MetaText> : null}</div><div><PriceText variant="investmentValue">{option.perTravelerPrice}</PriceText><MetaText variant="investmentMeta">{option.groupTotalPrice}</MetaText></div></article>)}</div>{note ? <div className={getTypographyClassName('bodySm')}><span {...(typeof noteLabel === 'string' ? {} : { 'data-editable': noteLabel.path, 'data-edit-owner': noteLabel.owner, 'data-edit-mode': noteLabel.mode })}>{textValue(noteLabel)}</span>{': '}<span {...(typeof note === 'string' ? {} : { 'data-editable': note.path, 'data-edit-owner': note.owner, 'data-edit-mode': note.mode })}>{textValue(note)}</span></div> : null}</PdfPage>;
}

function inclusionText(item: InclusionItemViewModel): TextValue { return typeof item === 'string' || 'value' in item ? item : `${textValue(item.title)} — ${textValue(item.desc)}`; }

function PdfDetails({ documentModel }: { documentModel: DisplayDocument }) {
  const details = documentModel.page.inclusionsExclusions;
  const terms = documentModel.page.paymentTerms;
  return <><PdfPage documentModel={documentModel} scope="inclusionsExclusions" className="pdf-details"><DisplayTitle as="h2" variant="sectionTitle">{details.title}</DisplayTitle><section><DisplayTitle as="h3" variant="termTitle">{details.inclusionsTitle ?? ''}</DisplayTitle>{details.inclusions.map((item, index) => <BodyCopy key={index} variant="bodyMd">{inclusionText(item)}</BodyCopy>)}</section><section><DisplayTitle as="h3" variant="termTitle">{details.exclusionsTitle ?? ''}</DisplayTitle>{details.exclusions.map((item, index) => <BodyCopy key={index} variant="bodyMd">{item}</BodyCopy>)}</section></PdfPage>
  <PdfPage documentModel={documentModel} scope="paymentTerms" className="pdf-terms"><div><Kicker variant="chapterKicker">{terms.kicker}</Kicker><DisplayTitle as="h2" variant="termTitle">{terms.title}</DisplayTitle><BodyCopy variant="termBody">{terms.description}</BodyCopy></div><div>{terms.terms.map((term, index) => <article key={index}><MetaText variant="termLabel">{term.label}</MetaText><BodyCopy variant="termBody">{term.bodyRichText}</BodyCopy></article>)}</div></PdfPage></>;
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
