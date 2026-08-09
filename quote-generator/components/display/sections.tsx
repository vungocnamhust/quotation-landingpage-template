import Image from 'next/image';
import type {
  BrandThemeTokens,
  ChapterDividerViewModel,
  DesignerViewModel,
  FooterViewModel,
  HeroViewModel,
  HotelsViewModel,
  InclusionsExclusionsViewModel,
  ItinerarySectionViewModel,
  LetterViewModel,
  NavViewModel,
  PageViewModel,
  PaymentTermsViewModel,
  PricingViewModel,
  PublicSectionId,
  RouteMapViewModel,
  ResolvedColorScope,
  SectionDisplayConfig,
  StaysDividerViewModel,
  ThemeDefinition,
  TypographySlotMap,
  FinalizationViewModel,
} from '../../display/types';
import { textValue } from '../../display/types';
import type { ViewMode } from '../../display/contracts';
import { getTypographyClassName } from '../../config/typography';
import { buildSectionFrameClassName, getLayoutSlots } from '../../display/layoutRegistry';
import { requireTypographySlot } from '../../display/typographySlots';
import { cn } from '../../utils/cn';
import {
  ActionButton,
  BodyCopy,
  DisplayTitle,
  Kicker,
  MetaText,
  QuoteText,
  TextLink,
} from './atoms';
import AppTopBar from '../AppTopBar';
import RouteMapClientIsland from './RouteMapClientIsland';
import {
  ActionGroup,
  DesignerPortraitRail,
  FooterMetaRow,
  HeroRuleMeta,
  HotelEditorialCard,
  InclusionsPanel,
  InvestmentRow,
  ItineraryDayMultiLayout,
  ItineraryDaySingleLayout,
  SectionHeader,
  SupportBlock,
  TermRow,
} from './molecules';

interface BaseSectionProps<T> {
  sectionId: PublicSectionId;
  viewModel: T;
  displayConfig: SectionDisplayConfig;
  tokens: BrandThemeTokens;
  theme: ThemeDefinition;
  viewMode: ViewMode;
  colorScope: ResolvedColorScope;
  pageViewModel?: PageViewModel;
}

export function getItineraryDayColor(index: number, totalDays: number): 'canvas' | 'borderless' {
  const g = Math.floor(index / 3);
  if (g === 0) return 'canvas';

  let currentColor: 'canvas' | 'borderless' = 'canvas';
  for (let groupIndex = 1; groupIndex <= g; groupIndex++) {
    const isFull = (groupIndex + 1) * 3 <= totalDays;
    if (isFull) {
      currentColor = groupIndex % 2 === 0 ? 'canvas' : 'borderless';
    }
  }
  return currentColor;
}

function shellProps(
  sectionId: PublicSectionId,
  displayConfig: SectionDisplayConfig,
  viewMode: ViewMode,
  extraClassName?: string
) {
  return buildSectionFrameClassName(
    displayConfig.layoutVariant,
    displayConfig.shellVariant,
    viewMode,
    cn(
      'display-section',
      `display-section--${sectionId}`,
      `display-section--bg-${displayConfig.backgroundVariant}`,
      `display-section--space-${displayConfig.spacingVariant}`,
      displayConfig.surfaceStyle && `display-section--surface-${displayConfig.surfaceStyle}`,
      displayConfig.stickyBehavior && `display-section--sticky-${displayConfig.stickyBehavior}`,
      displayConfig.sectionIntroStyle && `display-section--intro-${displayConfig.sectionIntroStyle}`,
      displayConfig.mobileOrderStrategy && `display-section--mobile-${displayConfig.mobileOrderStrategy}`,
      displayConfig.interactionPreset && `display-section--interaction-${displayConfig.interactionPreset}`,
      extraClassName,
      displayConfig.printBehavior.pageBreakBefore && 'display-page-break-before',
      displayConfig.printBehavior.pageBreakAfter && 'display-page-break-after',
      displayConfig.printBehavior.avoidBreakInside && 'display-avoid-break-inside',
      displayConfig.printBehavior.allowCondensedVariant && 'display-condensed-ok',
      displayConfig.printBehavior.pageGroupWithNext && 'display-page-group-next'
    )
  );
}

function sectionOrnaments(theme: ThemeDefinition, ornamentIds: string[]) {
  return ornamentIds.map((ornamentId) => (
    <div key={ornamentId} className={theme.ornamentRegistry[ornamentId]} aria-hidden="true" />
  ));
}

function SectionOverlay({
  src,
  alt,
  gradientClassName,
}: {
  src?: string;
  alt: import('../../display/types').TextValue;
  gradientClassName?: string;
}) {
  const hasValidSrc = typeof src === 'string' && src.trim() !== '';

  return (
    <div className="display-section-overlay">
      {hasValidSrc ? (
        <Image src={src} alt={textValue(alt)} data-editable={typeof alt === 'string' ? '/labels/sectionImage' : alt.path} data-edit-owner={typeof alt === 'string' ? 'system' : alt.owner} data-edit-mode={typeof alt === 'string' ? 'altText' : alt.mode} fill priority sizes="100vw" className="object-cover" />
      ) : null}
      <div className={cn('display-section-overlay__gradient', gradientClassName)} />
    </div>
  );
}

function normalizePoint(
  coordinates: [number, number],
  center: [number, number],
  latSpan: number,
  lngSpan: number
) {
  const [lat, lng] = coordinates;
  const [centerLat, centerLng] = center;

  const x = ((lng - (centerLng - lngSpan / 2)) / lngSpan) * 100;
  const y = (1 - (lat - (centerLat - latSpan / 2)) / latSpan) * 100;

  return {
    x: Math.min(92, Math.max(8, x)),
    y: Math.min(88, Math.max(10, y)),
  };
}

function StaticRouteMapPanel({
  viewModel,
  typography,
}: {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
}) {
  const projectedPoints = viewModel.interactiveMarkers.map((marker) => ({
    ...marker,
    ...normalizePoint(
      marker.coordinates,
      viewModel.mapViewport.center,
      viewModel.mapViewport.latSpan,
      viewModel.mapViewport.lngSpan
    ),
  }));

  const activeSegment =
    viewModel.segments.find((segment) => segment.sequence === viewModel.initialActiveSegment) ?? viewModel.segments[0];

  const routePath = projectedPoints
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');

  return (
    <div className="display-route-map display-route-map--pdf">
      <div className="display-route-map__pdf-map">
        <div className="display-route-map__canvas display-route-map__canvas--static display-route-map__canvas--pdf">
          <svg
            viewBox="0 0 100 100"
            className="display-route-map__svg"
            aria-label={textValue(viewModel.overviewAriaLabel)}
            data-editable={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.path}
            data-edit-owner={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.owner}
            data-edit-mode={typeof viewModel.overviewAriaLabel === 'string' ? undefined : viewModel.overviewAriaLabel.mode}
            preserveAspectRatio="none"
          >
            <path d={routePath} className="display-route-map__path" />
            {projectedPoints.map((point) => (
              <g key={point.sequence}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={activeSegment.sequence === point.sequence ? 3.2 : 2.3}
                  className={cn(
                    'display-route-map__marker display-route-map__marker--pdf',
                    activeSegment.sequence === point.sequence && 'is-active'
                  )}
                />
                <text x={point.x} y={point.y - 5} textAnchor="middle" className={cn('display-route-map__marker-label', getTypographyClassName(requireTypographySlot(typography, 'index')))}>
                  {point.sequence}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      <div className="display-route-map__pdf-timeline" role="list">
        {viewModel.segments.map((segment, index) => (
          <div key={segment.sequence} className="display-route-map__pdf-step">
            <div role="listitem" className="display-route-map__pdf-step-card">
              <div className={cn('display-route-map__pdf-step-index', getTypographyClassName(requireTypographySlot(typography, 'index')))}>{index + 1}</div>
              <div className="display-route-map__pdf-step-copy">
                <DisplayTitle as="h3" variant={requireTypographySlot(typography, 'metaPrimary')}>
                  {segment.city}
                </DisplayTitle>
                {segment.sidebarLabel ? (
                  <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="accent">
                    {segment.sidebarLabel}
                  </MetaText>
                ) : null}
                {segment.hotelName ? (
                  <MetaText variant={requireTypographySlot(typography, 'metaSecondary')} tone="muted">
                    {segment.hotelName}
                  </MetaText>
                ) : null}
              </div>
            </div>
            {index < viewModel.segments.length - 1 ? <div className="display-route-map__pdf-step-connector" /> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function NavSection({
  sectionId,
  viewModel,
  displayConfig,
  viewMode,
}: BaseSectionProps<NavViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="top" className={shellProps(sectionId, displayConfig, viewMode, 'display-nav')}>
      <div className={slots.container}>
        <AppTopBar viewModel={viewModel} typography={displayConfig.typographySlots} />
      </div>
    </section>
  );
}

export function HeroSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<HeroViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="hero" className={shellProps(sectionId, displayConfig, viewMode, 'display-hero')}>
      <SectionOverlay
        src={viewModel.backgroundImage}
        alt={viewModel.backgroundImageAlt}
      />
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.content}>
          <Kicker variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')} tone="inverse">
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle
            as="h1"
            variant={requireTypographySlot(displayConfig.typographySlots, 'title')}
            className="display-hero__title"
            tone="inverse"
          >
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy
            variant={requireTypographySlot(displayConfig.typographySlots, 'body')}
            className="display-hero__lede"
            tone="inverse"
          >
            {viewModel.lede}
          </BodyCopy>
          <HeroRuleMeta
            primary={viewModel.metaPrimary}
            secondary={viewModel.metaSecondary}
            typography={displayConfig.typographySlots}
          />
          <div className="display-hero__actions">
            <ActionButton href={viewModel.primaryCta.href} colorRole="primary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')} className="display-hero__primary-action">
              {viewModel.primaryCta.label}
            </ActionButton>
          </div>
        </div>
        <div className={slots.footer}>
          <MetaText
            variant={requireTypographySlot(displayConfig.typographySlots, 'footer')}
            className="display-hero__footer"
            tone="inverse"
          >
            {viewModel.footerMeta}
          </MetaText>
        </div>
      </div>
    </section>
  );
}

export function OpenLetterSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<LetterViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="letter" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader
            kicker={viewModel.chapterKicker}
            title={viewModel.title}
            typography={displayConfig.typographySlots}
          />
        </div>

        <div className={slots.content}>
          <aside className={slots.aside}>
            <QuoteText
              variant={requireTypographySlot(displayConfig.typographySlots, 'quote')}
              className="display-letter__highlight"
            >
              {viewModel.highlight}
            </QuoteText>
            {typeof viewModel.decorAsset === 'string' && viewModel.decorAsset.trim() !== '' ? (
              <div className="display-letter__decor">
                <Image src={viewModel.decorAsset} alt="" width={220} height={240} className="display-letter__decor-image" />
              </div>
            ) : null}
          </aside>

          <div className={slots.media}>
            <div className="display-letter__copy">
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="default">
                {viewModel.greeting}
              </BodyCopy>
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>{viewModel.intro}</BodyCopy>
              {viewModel.body.map((paragraph) => (
                <BodyCopy key={textValue(paragraph)} variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
                  {paragraph}
                </BodyCopy>
              ))}
              <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>{viewModel.outro}</BodyCopy>

              <div className="display-letter__signature">
                <DisplayTitle
                  as="h3"
                  variant={requireTypographySlot(displayConfig.typographySlots, 'signature')}
                >
                  {viewModel.signatureName}
                </DisplayTitle>
                <div className="display-letter__signature-meta">
                  <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')} tone="muted">
                    {viewModel.signatureRole}
                  </MetaText>
                  {viewModel.signatureContactLine ? (
                    <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')} tone="muted">
                      {viewModel.signatureContactLine}
                    </MetaText>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

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
              }}
              viewMode={viewMode}
            />
          )}
        </div>
      </div>
    </section>
  );
}

export function ItineraryDividerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<ChapterDividerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const isImageMode = displayConfig.backgroundVariant === 'image-overlay' && typeof viewModel.image === 'string' && viewModel.image.trim() !== '';

  return (
    <section id="divider-itinerary" className={shellProps(sectionId, displayConfig, viewMode)}>
      {isImageMode && viewModel.image ? (
        <SectionOverlay
          src={viewModel.image}
          alt={viewModel.imageAlt ?? viewModel.title}
          gradientClassName="display-section-overlay__gradient--chapter"
        />
      ) : null}
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.content}>
          <Kicker
            variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')}
            tone={isImageMode ? 'inverse' : 'accent'}
          >
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle
            as="h2"
            variant={requireTypographySlot(displayConfig.typographySlots, 'title')}
            tone={isImageMode ? 'inverse' : 'default'}
          >
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy
            variant={requireTypographySlot(displayConfig.typographySlots, 'body')}
            tone={isImageMode ? 'inverse' : 'muted'}
            className="display-chapter-divider__tagline"
          >
            {viewModel.tagline}
          </BodyCopy>
          {viewModel.journeyMeta?.length ? (
            <dl className={cn('display-chapter-divider__meta', isImageMode && 'is-inverse')}>
              {viewModel.journeyMeta.map((item) => (
                <div key={textValue(item.label)} className="display-chapter-divider__meta-row">
                  <dt>
                    <MetaText
                      variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')}
                      tone={isImageMode ? 'inverse' : 'accent'}
                    >
                      {item.label}
                    </MetaText>
                  </dt>
                  <dd>
                    <MetaText
                      variant={requireTypographySlot(displayConfig.typographySlots, 'metaPrimary')}
                      tone={isImageMode ? 'inverse' : 'default'}
                    >
                      {item.value}
                    </MetaText>
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
          {viewModel.exploreHref && viewModel.exploreLabel ? (
            <span className={cn('display-chapter-divider__explore', isImageMode && 'is-inverse')}>
              <TextLink href={viewModel.exploreHref} colorRole="secondary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')}>{viewModel.exploreLabel}</TextLink>
              <span aria-hidden="true">→</span>
            </span>
          ) : null}
        </div>
      </div>
    </section>
  );
}

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
          {viewModel.roomNotes ? (
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
              {viewModel.roomNotes}
            </BodyCopy>
          ) : null}
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
      </div>
    </section>
  );
}

export function StaysDividerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<StaysDividerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  const hasValidImage = typeof viewModel.image === 'string' && viewModel.image.trim() !== '';

  return (
    <section id="divider-hotels" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className="display-stays-divider__journey-line" aria-hidden="true" />
      <div className={slots.container}>
        {hasValidImage ? (
          <div className={slots.media}>
            <div className="display-stays-divider__image">
              <Image src={viewModel.image} alt={textValue(viewModel.imageAlt)} data-editable={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.path} data-edit-owner={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.owner} data-edit-mode={typeof viewModel.imageAlt === 'string' ? undefined : viewModel.imageAlt.mode} fill sizes="(min-width: 1024px) 50vw, 100vw" className="object-cover" />
            </div>
          </div>
        ) : null}
        <div className={slots.content}>
          <Kicker variant={requireTypographySlot(displayConfig.typographySlots, 'kicker')}>
            {viewModel.kicker}
          </Kicker>
          <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')}>
            {viewModel.title}
          </DisplayTitle>
          <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')}>
            {viewModel.tagline}
          </BodyCopy>
          <QuoteText variant={requireTypographySlot(displayConfig.typographySlots, 'footer')}>
            {viewModel.closing}
          </QuoteText>
        </div>
      </div>
    </section>
  );
}

export function PricingSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<PricingViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="pricing" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            {viewModel.kicker ? (
              <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'label')} tone="accent" className="mb-2 block">
                {viewModel.kicker}
              </MetaText>
            ) : null}
            <DisplayTitle as="h2" variant={requireTypographySlot(displayConfig.typographySlots, 'title')} tone="default">
              {viewModel.title}
            </DisplayTitle>
          </div>
          {viewModel.description ? (
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="muted" className="sm:text-right">
              {viewModel.description}
            </BodyCopy>
          ) : null}
        </div>
        <div className={cn(slots.content, 'space-y-4')}>
          {viewModel.options.map((option) => (
            <InvestmentRow key={option.index} option={option} typography={displayConfig.typographySlots} />
          ))}
        </div>
        {viewModel.importantNote ? (
          <div className="mt-10 pt-6 border-t border-[var(--color-border)]">
            <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'label')} tone="accent" className="mb-1 block">
              {viewModel.importantNoteLabel}
            </MetaText>
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="muted">
              {viewModel.importantNote}
            </BodyCopy>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function InclusionsExclusionsSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<InclusionsExclusionsViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="inclusions" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader title={viewModel.title} typography={displayConfig.typographySlots} />
        </div>
        <div className={slots.content}>
          <InclusionsPanel
            title={viewModel.inclusionsTitle ?? viewModel.title}
            lead={viewModel.inclusionsLead}
            items={viewModel.inclusions}
            typography={displayConfig.typographySlots}
          />
          <InclusionsPanel
            title={viewModel.exclusionsTitle ?? viewModel.title}
            lead={viewModel.exclusionsLead}
            items={viewModel.exclusions}
            typography={displayConfig.typographySlots}
          />
        </div>
      </div>
    </section>
  );
}

export function PaymentTermsSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<PaymentTermsViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="payment-terms" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <aside className={slots.aside}>
          <div className="whitespace-pre-line">
            <SectionHeader
              kicker={viewModel.kicker}
              title={viewModel.title}
              body={viewModel.description}
              typography={displayConfig.typographySlots}
            />
          </div>
          <span className="display-payment-terms__cta">
            <TextLink href={viewModel.cta.href} colorRole="secondary" typographyVariant={requireTypographySlot(displayConfig.typographySlots, 'action')}>{viewModel.cta.label}</TextLink>
            <span aria-hidden="true">→</span>
          </span>
        </aside>

        <div className={slots.content}>
          {viewModel.terms.map((term) => (
            <TermRow key={textValue(term.label)} term={term} typography={displayConfig.typographySlots} />
          ))}
        </div>
      </div>
    </section>
  );
}

export function DesignerSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<DesignerViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <section id="designer" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <aside className={slots.aside}>
          <DesignerPortraitRail item={viewModel} typography={displayConfig.typographySlots} />
        </aside>

        <div className={cn(slots.content, 'display-designer__content')}>
          <div className="display-designer__divider" aria-hidden="true" />
          <SectionHeader
            kicker={viewModel.kicker}
            title={viewModel.title}
            typography={displayConfig.typographySlots}
          />
          <QuoteText variant={requireTypographySlot(displayConfig.typographySlots, 'quote')}>
            {viewModel.quote}
          </QuoteText>
          <ActionGroup actions={viewModel.contactActions} typography={displayConfig.typographySlots} />
          {viewModel.supportBlocks.length > 0 ? (
            <div className={slots.footer}>
              {viewModel.supportBlocks.map((block) => (
                <SupportBlock key={textValue(block.title)} block={block} typography={displayConfig.typographySlots} />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function FinalizationSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<FinalizationViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);
  return (
    <section id="finalization" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <div className={slots.header}>
          <SectionHeader kicker={viewModel.kicker} title={viewModel.title} body={viewModel.description} typography={displayConfig.typographySlots} />
        </div>
        <div className={slots.content}>
          <InclusionsPanel title={viewModel.required.title} items={viewModel.required.items} typography={displayConfig.typographySlots} />
          <InclusionsPanel title={viewModel.afterConfirmation.title} items={viewModel.afterConfirmation.items} typography={displayConfig.typographySlots} />
        </div>
      </div>
    </section>
  );
}

export function FooterSection({
  sectionId,
  viewModel,
  displayConfig,
  theme,
  viewMode,
}: BaseSectionProps<FooterViewModel>) {
  const slots = getLayoutSlots(displayConfig.layoutVariant, viewMode);

  return (
    <footer id="footer" className={shellProps(sectionId, displayConfig, viewMode)}>
      {sectionOrnaments(theme, displayConfig.ornaments)}
      <div className={slots.container}>
        <FooterMetaRow
          primary={
            <BodyCopy variant={requireTypographySlot(displayConfig.typographySlots, 'body')} tone="default">
              {viewModel.text}
            </BodyCopy>
          }
          secondary={
            viewModel.secondaryMeta ? (
              <MetaText variant={requireTypographySlot(displayConfig.typographySlots, 'metaSecondary')}>
                {viewModel.secondaryMeta}
              </MetaText>
            ) : undefined
          }
        />
      </div>
    </footer>
  );
}

export const sectionRegistry = {
  nav: NavSection,
  hero: HeroSection,
  letter: OpenLetterSection,
  routeMap: RouteMapSection,
  itineraryDivider: ItineraryDividerSection,
  itinerary: ItinerarySection,
  hotels: HotelsSection,
  staysDivider: StaysDividerSection,
  pricing: PricingSection,
  inclusionsExclusions: InclusionsExclusionsSection,
  paymentTerms: PaymentTermsSection,
  finalization: FinalizationSection,
  designer: DesignerSection,
  footer: FooterSection,
};
