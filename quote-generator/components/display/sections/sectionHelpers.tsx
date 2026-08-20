import Image from 'next/image';
import type {
  BrandThemeTokens,
  PageViewModel,
  PublicSectionId,
  ResolvedColorScope,
  RouteMapViewModel,
  SectionDisplayConfig,
  ThemeDefinition,
  TypographySlotMap,
} from '../../../display/types.ts';
import { textValue } from '../../../display/types.ts';
import type { ViewMode } from '../../../display/contracts.ts';
import { getTypographyClassName } from '../../../config/typography.ts';
import { buildSectionFrameClassName } from '../../../display/layoutRegistry.ts';
import { requireTypographySlot } from '../../../display/typographySlots.ts';
import { cn } from '../../../utils/cn.ts';
import { DisplayTitle, MetaText } from '../atoms.tsx';

export interface BaseSectionProps<T> {
  sectionId: PublicSectionId;
  viewModel: T;
  displayConfig: SectionDisplayConfig;
  tokens: BrandThemeTokens;
  theme: ThemeDefinition;
  viewMode: ViewMode;
  colorScope: ResolvedColorScope;
  pageViewModel?: PageViewModel;
  /** Allows the staff-only Canvas to expose an otherwise empty editable slot. */
  workspaceCanvas?: boolean;
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

export function shellProps(
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

export function sectionOrnaments(theme: ThemeDefinition, ornamentIds: string[]) {
  return ornamentIds.map((ornamentId) => (
    <div key={ornamentId} className={theme.ornamentRegistry[ornamentId]} aria-hidden="true" />
  ));
}

export function SectionOverlay({
  src,
  alt,
  gradientClassName,
}: {
  src?: string;
  alt: import('../../../display/types').TextValue;
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

export function normalizePoint(
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

export function StaticRouteMapPanel({
  viewModel,
  typography,
}: {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
}) {
  if (!viewModel.isInteractiveAvailable) {
    return <div className="display-route-map__unavailable" role="status">{textValue(viewModel.unavailableMessage)}</div>;
  }
  const mapCenter = viewModel.mapViewport.center;
  if (!mapCenter) {
    return <div className="display-route-map__unavailable" role="status">{textValue(viewModel.unavailableMessage)}</div>;
  }
  const projectedPoints = viewModel.interactiveMarkers.map((marker) => ({
    ...marker,
    ...normalizePoint(
      marker.coordinates,
      mapCenter,
      viewModel.mapViewport.latSpan,
      viewModel.mapViewport.lngSpan
    ),
  }));

  const activeSegment =
    viewModel.segments.find((segment) => segment.sequence === viewModel.initialActiveSegment) ?? viewModel.segments[0];

  const routePath = projectedPoints.reduce((pathStr, point, index) => {
    if (index === 0) return `M ${point.x} ${point.y}`;
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
                  {textValue(point.dayLabel)}
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
              <div className={cn('display-route-map__pdf-step-index', getTypographyClassName(requireTypographySlot(typography, 'index')))}>{textValue(segment.dayLabel)}</div>
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
