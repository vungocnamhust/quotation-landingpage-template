import Image from 'next/image';
import type { ReactNode } from 'react';
import type {
  DesignerSupportBlockViewModel,
  DesignerViewModel,
  HotelCardViewModel,
  InclusionItemViewModel,
  ItineraryDayViewModel,
  NavActionViewModel,
  PaymentTermItemViewModel,
  PriceOptionViewModel,
  TypographySlotMap,
  TextValue,
} from '../../display/types.ts';
import { textValue } from '../../display/types.ts';
import { cn } from '../../utils/cn.ts';
import { requireTypographySlot } from '../../display/typographySlots.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import {
  ActionButton,
  AvatarFrame,
  BodyCopy,
  DisplayTitle,
  ImageFrame,
  Kicker,
  MetaText,
  PriceText,
  QuoteText,
} from './atoms.tsx';
import ItineraryCarousel from './ItineraryCarousel.tsx';

export function SectionHeader({
  kicker,
  title,
  body,
  typography,
  align = 'left',
  kickerStyle = 'plain',
}: {
  kicker?: TextValue;
  title: TextValue;
  body?: TextValue;
  typography: TypographySlotMap;
  align?: 'left' | 'center';
  kickerStyle?: 'plain' | 'soft-badge';
}) {
  return (
    <div className={cn('display-section-header', align === 'center' && 'is-center')}>
      {kicker ? (
        <div className={cn('display-section-header__kicker', kickerStyle === 'soft-badge' && 'is-badge')}>
          <Kicker variant={requireTypographySlot(typography, 'kicker')}>{kicker}</Kicker>
        </div>
      ) : null}
      <DisplayTitle as="h2" variant={requireTypographySlot(typography, 'title')}>
        {title}
      </DisplayTitle>
      {body ? <BodyCopy variant={requireTypographySlot(typography, 'body')}>{body}</BodyCopy> : null}
    </div>
  );
}

export function HeroRuleMeta({
  primary,
  secondary,
  typography,
}: {
  primary: TextValue;
  secondary: TextValue;
  typography: TypographySlotMap;
}) {
  return (
    <div className="display-hero-rule-meta">
      <MetaText variant={requireTypographySlot(typography, 'metaPrimary')} tone="inverse">
        {primary}
      </MetaText>
      <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="inverse">
        {secondary}
      </MetaText>
    </div>
  );
}

export function ItineraryDaySingleLayout({
  day,
  typography,
}: {
  day: ItineraryDayViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <article className={cn('display-itinerary-day', day.isAlternate && 'is-alternate')}>
      <div className={cn('display-itinerary-day__single', day.isAlternate && 'is-alternate')}>
        <div className="display-itinerary-day__single-media">
          <ItineraryCarousel
            images={day.carouselImages}
            alt={day.title}
            alts={day.carouselImageAlts}
            labels={day.carouselLabels}
            typography={typography}
            className="display-itinerary-carousel--hero"
          />
        </div>
        <div className="display-itinerary-day__single-copy">
          <DayHeader day={day} typography={typography} />
          <DayBody day={day} typography={typography} />
        </div>
      </div>
    </article>
  );
}

export function ItineraryDayMultiLayout({
  day,
  typography,
}: {
  day: ItineraryDayViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <article className={cn('display-itinerary-day', day.isAlternate && 'is-alternate')}>
      <div className={cn('display-itinerary-day__multi', day.isAlternate && 'is-alternate')}>
        <div className="display-itinerary-day__multi-copy">
          <DayHeader day={day} typography={typography} />
          <DayBody day={day} typography={typography} />
        </div>

        <div className="display-itinerary-day__multi-media">
          <div className={cn('display-itinerary-day__supporting-grid', day.isAlternate && 'is-alternate')}>
            <ItineraryCarousel images={day.carouselImages} alt={day.title} alts={day.carouselImageAlts} labels={day.carouselLabels} typography={typography} />
            <div className="display-itinerary-day__supporting-stack">
              {day.supportingImages.slice(0, 2).map((image, index) => (
                <ImageFrame
                  key={image}
                  src={image}
                  alt={day.supportingImageAlts[index] ?? day.title}
                  className="aspect-[4/3]"
                  variant="editorial"
                  sizes="(min-width: 1024px) 18vw, 100vw"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function DayHeader({
  day,
  typography,
}: {
  day: ItineraryDayViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <div className="display-day-header">
      <div className="display-day-header__meta">
        <MetaText variant={requireTypographySlot(typography, 'label')} tone="muted">
          {day.dayLabel}
        </MetaText>
        <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="accent">
          {day.city}
        </MetaText>
      </div>
      <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'metaPrimary')}>
        {day.title}
      </DisplayTitle>
      <div className="display-day-header__divider" aria-hidden="true" />
    </div>
  );
}

function DayBody({
  day,
  typography,
}: {
  day: ItineraryDayViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <div className="display-day-body">
      <div className="display-day-body__copy">
        {day.description.map((paragraph) => (
          <BodyCopy key={textValue(paragraph)} variant={requireTypographySlot(typography, 'body')}>
            {paragraph}
          </BodyCopy>
        ))}
      </div>

      <dl className="display-day-details">
        {day.detailRows.map((row) => (
          <div key={`${textValue(day.dayLabel)}-${textValue(row.label)}`} className="display-day-details__row">
            <dt>
              <MetaText variant={requireTypographySlot(typography, 'label')} tone="default">
                {row.label}
              </MetaText>
            </dt>
            <dd>
              <BodyCopy variant={requireTypographySlot(typography, 'body')} tone="default">
                {row.value}
              </BodyCopy>
            </dd>
          </div>
        ))}
      </dl>

      {day.notes?.length ? (
        <div className="display-day-notes">
          {day.notes.map((note) => (
            <BodyCopy key={textValue(note)} variant={requireTypographySlot(typography, 'body')}>
              {note}
            </BodyCopy>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function HotelEditorialCard({
  item,
  typography,
}: {
  item: HotelCardViewModel;
  typography: TypographySlotMap;
}) {
  const isEven = item.layoutParity === 'even';

  return (
    <article className="display-hotel-card">
      <div className={cn('display-hotel-card__grid', isEven && 'is-even')}>
        <div className="display-hotel-card__title-block">
          <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="muted">
            {item.city}
          </MetaText>
          <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'metaPrimary')}>
            {item.name}
          </DisplayTitle>
        </div>

        <div className={cn('display-hotel-card__images', isEven && 'is-even')}>
          <ImageFrame src={item.hotelImage} alt={item.hotelImageAlt} className="aspect-[4/3]" variant="editorial" />
          <div className="display-hotel-card__sub-image">
            <ImageFrame
              src={item.roomImage}
              alt={item.roomImageAlt}
              className="aspect-[4/3]"
              variant="editorial"
              sizes="(min-width: 1024px) 28vw, 100vw"
            />
            <MetaText variant={requireTypographySlot(typography, 'metaSecondary')}>{item.roomType}</MetaText>
          </div>
        </div>

        <div className="display-hotel-card__body">
          {item.intro ? (
            <BodyCopy variant={requireTypographySlot(typography, 'body')}>{item.intro}</BodyCopy>
          ) : null}

          <div className="display-hotel-card__meta">
            <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="default">
              {item.dateRanges.map(textValue).filter(Boolean).join(' • ')}
            </MetaText>
            {item.telephone ? (
              <div className={getTypographyClassName(requireTypographySlot(typography, 'metaSecondary'))}>
                <span {...(typeof item.telephonePrefix === 'string' ? {} : { 'data-editable': item.telephonePrefix?.path, 'data-edit-owner': item.telephonePrefix?.owner, 'data-edit-mode': item.telephonePrefix?.mode })}>{textValue(item.telephonePrefix)}</span>{' '}
                <span {...(typeof item.telephone === 'string' ? {} : { 'data-editable': item.telephone.path, 'data-edit-owner': item.telephone.owner, 'data-edit-mode': item.telephone.mode })}>{textValue(item.telephone)}</span>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}

export function InvestmentHero({
  option,
  typography,
}: {
  option: PriceOptionViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <article className="display-investment-hero">
      {option.label ? (
        <DisplayTitle
          as="h3"
          variant={requireTypographySlot(typography, 'metaPrimary')}
          tone="accent"
          className="display-investment-hero__label"
        >
          {option.label}
        </DisplayTitle>
      ) : null}
      <div className="display-investment-hero__price-block">
        <PriceText
          variant={requireTypographySlot(typography, 'price')}
          tone="default"
          className="display-investment-hero__total"
        >
          {option.groupTotalPrice}
        </PriceText>
        {option.groupTotalLabel ? (
          <MetaText
            variant={requireTypographySlot(typography, 'label')}
            tone="accent"
            className="display-investment-hero__price-label"
          >
            {option.groupTotalLabel}
          </MetaText>
        ) : null}
      </div>
      <div className="display-investment-hero__meta">
        {option.perTravelerPrice ? (
          <PriceText
            variant={requireTypographySlot(typography, 'body')}
            tone="muted"
            className="display-investment-hero__pax"
          >
            {option.perTravelerPrice}
          </PriceText>
        ) : null}
        {option.description ? (
          <BodyCopy
            variant={requireTypographySlot(typography, 'metaSecondary')}
            tone="muted"
            className="display-investment-hero__desc"
          >
            {option.description}
          </BodyCopy>
        ) : null}
      </div>
    </article>
  );
}

export function InvestmentComparisonCard({
  option,
  typography,
  isLast,
}: {
  option: PriceOptionViewModel;
  typography: TypographySlotMap;
  isLast?: boolean;
}) {
  return (
    <article className={cn('display-investment-comparison', !isLast && 'display-investment-comparison--bordered')}>
      <div className="display-investment-comparison__header">
        <div className="display-investment-comparison__title-line">
          <DisplayTitle
            as="h3"
            variant={requireTypographySlot(typography, 'metaPrimary')}
            tone="default"
            className="display-investment-comparison__title"
          >
            {option.label}
          </DisplayTitle>
          {option.isSelection || option.badge ? (
            <span className="display-investment-comparison__selection">
              <MetaText variant={requireTypographySlot(typography, 'badge')} tone="accent">
                {option.badge || 'OUR SELECTION'}
              </MetaText>
            </span>
          ) : null}
        </div>
        {option.description ? (
          <BodyCopy
            variant={requireTypographySlot(typography, 'metaSecondary')}
            tone="muted"
            className="display-investment-comparison__desc"
          >
            {option.description}
          </BodyCopy>
        ) : null}
      </div>

      <div className="display-investment-comparison__price">
        <PriceText
          variant={requireTypographySlot(typography, 'price')}
          tone="default"
          className="display-investment-comparison__total"
        >
          {option.groupTotalPrice}
        </PriceText>
        {option.groupTotalLabel ? (
          <MetaText
            variant={requireTypographySlot(typography, 'label')}
            tone="accent"
            className="display-investment-comparison__price-label"
          >
            {option.groupTotalLabel}
          </MetaText>
        ) : null}
        {option.perTravelerPrice ? (
          <PriceText
            variant={requireTypographySlot(typography, 'body')}
            tone="muted"
            className="display-investment-comparison__pax"
          >
            {option.perTravelerPrice}
          </PriceText>
        ) : null}
      </div>
    </article>
  );
}

export function InvestmentRow({
  option,
  typography,
  hideIndex = false,
}: {
  option: PriceOptionViewModel;
  typography: TypographySlotMap;
  hideIndex?: boolean;
}) {
  return (
    <article className="display-investment-row">
      <div className="display-investment-row__content">
        {!hideIndex && option.displayIndex ? (
          <MetaText
            variant={requireTypographySlot(typography, 'index')}
            tone="accent"
            className="display-investment-row__index"
          >
            {option.displayIndex}
          </MetaText>
        ) : null}
        <div className="display-investment-row__identity">
          <div className="display-investment-row__title-line">
            <DisplayTitle
              as="h3"
              variant={requireTypographySlot(typography, 'metaPrimary')}
              tone="default"
              className="display-investment-row__category"
            >
              {option.label}
            </DisplayTitle>
            {option.isSelection || option.badge ? (
              <span className="display-investment-row__selection">
                <MetaText variant={requireTypographySlot(typography, 'badge')} tone="accent">
                  {option.badge || 'OUR SELECTION'}
                </MetaText>
              </span>
            ) : null}
          </div>
          {option.description ? (
            <BodyCopy
              variant={requireTypographySlot(typography, 'metaSecondary')}
              tone="muted"
              className="display-investment-row__desc"
            >
              {option.description}
            </BodyCopy>
          ) : null}
        </div>
      </div>
      <div className="display-investment-row__value">
        <PriceText
          variant={requireTypographySlot(typography, 'price')}
          tone="default"
          className="display-investment-row__total"
        >
          {option.groupTotalPrice}
        </PriceText>
        {option.groupTotalLabel ? (
          <MetaText
            variant={requireTypographySlot(typography, 'label')}
            tone="accent"
            className="display-investment-row__price-label"
          >
            {option.groupTotalLabel}
          </MetaText>
        ) : null}
        {option.perTravelerPrice ? (
          <PriceText
            variant={requireTypographySlot(typography, 'body')}
            tone="muted"
            className="display-investment-row__pax"
          >
            {option.perTravelerPrice}
          </PriceText>
        ) : null}
      </div>
    </article>
  );
}

export function InclusionsPanel({
  title,
  lead,
  items,
  typography,
}: {
  title: TextValue;
  lead?: TextValue;
  items: Array<InclusionItemViewModel | string>;
  typography: TypographySlotMap;
}) {
  return (
    <article className="display-inclusion-panel">
      <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'metaPrimary')} className="display-inclusion-panel__title">
        {title}
      </DisplayTitle>
      {lead ? <BodyCopy variant={requireTypographySlot(typography, 'body')} tone="muted" className="display-inclusion-panel__lead">{lead}</BodyCopy> : null}
      <ul className="display-inclusion-panel__list">
        {items.map((item, index) =>
          typeof item === 'string' || ('path' in item && 'value' in item) ? (
            <li key={`${textValue(title)}-${index}`} className="display-inclusion-panel__bullet">
              <BodyCopy variant={requireTypographySlot(typography, 'body')} tone="default">
                {item}
              </BodyCopy>
            </li>
          ) : (
            <li key={`${textValue(title)}-${textValue(item.title)}`} className="display-inclusion-panel__feature">
              <MetaText variant={requireTypographySlot(typography, 'metaPrimary')} tone="default" className="display-inclusion-panel__feature-title">
                {item.title}
              </MetaText>
              <BodyCopy variant={requireTypographySlot(typography, 'body')}>{item.desc}</BodyCopy>
            </li>
          )
        )}
      </ul>
    </article>
  );
}

export function TermRow({
  term,
  typography,
}: {
  term: PaymentTermItemViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <article className="display-term-row">
      <div className="display-term-row__label">
        <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'label')} className="display-term-row__title">
          {term.label}
        </DisplayTitle>
      </div>
      <BodyCopy variant={requireTypographySlot(typography, 'body')} className="display-term-row__body">
        {term.bodyRichText}
      </BodyCopy>
    </article>
  );
}

export function DesignerPortraitRail({
  item,
  typography,
}: {
  item: DesignerViewModel;
  typography: TypographySlotMap;
}) {
  return (
    <div className="display-designer-rail">
      <AvatarFrame
        src={item.avatar}
        alt={item.avatarAlt}
        variant="editorial"
        className="display-designer-rail__portrait"
      />
      <div className="display-designer-rail__copy">
        <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'signature')}>
          {item.name}
        </DisplayTitle>
        {item.subtitle ? (
          <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="accent">
            {item.subtitle}
          </MetaText>
        ) : null}
        <MetaText variant={requireTypographySlot(typography, 'metaSecondary')}>
          {item.signatureLabel}
        </MetaText>
      </div>
      <QuoteText variant={requireTypographySlot(typography, 'body')} className="display-designer-rail__note">
        {item.experienceNote}
      </QuoteText>
    </div>
  );
}

export function SupportBlock({ block, typography }: { block: DesignerSupportBlockViewModel; typography: TypographySlotMap }) {
  return (
    <div className="display-support-block">
      <div className="display-support-block__icon">
        <Image src={block.iconSrc} alt="" width={28} height={28} />
      </div>
      <div className="display-support-block__copy">
        <MetaText variant={requireTypographySlot(typography, 'label')} tone="default">
          {block.title}
        </MetaText>
        <ul className="display-support-block__list">
          {block.items.map((item) => (
            <li key={textValue(item)}>
              <BodyCopy variant={requireTypographySlot(typography, 'body')}>{item}</BodyCopy>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function FooterMetaRow({
  primary,
  secondary,
}: {
  primary: ReactNode;
  secondary?: ReactNode;
}) {
  return (
    <div className="display-footer-meta-row">
      <div>{primary}</div>
      {secondary ? <div>{secondary}</div> : null}
    </div>
  );
}

export function ActionGroup({
  actions,
  typography,
}: {
  actions: NavActionViewModel[];
  typography: TypographySlotMap;
}) {
  return (
    <div className="display-action-group">
      {actions.map((action) => (
        <div key={textValue(action.label)} className="display-action-group__item">
          <ActionButton
            href={action.href}
            colorRole={action.emphasis ?? 'primary'}
            typographyVariant={requireTypographySlot(typography, 'action')}
          >
            {action.label}
          </ActionButton>
          {action.caption ? (
            <MetaText variant={requireTypographySlot(typography, 'footer')} className="display-action-group__caption" tone="accent">
              {action.caption}
            </MetaText>
          ) : null}
        </div>
      ))}
    </div>
  );
}
