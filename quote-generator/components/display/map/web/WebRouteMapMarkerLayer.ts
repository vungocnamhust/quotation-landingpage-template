'use client';

import type { CircleMarker, LatLngExpression, Map as LeafletMap, Marker, Polyline } from 'leaflet';
import L from 'leaflet';
import { useEffect, useRef } from 'react';
import type { RouteSegmentViewModel } from '../../../../display/types.ts';
import { textValue } from '../../../../display/types.ts';
import type { WebRouteMapLayoutPlan } from './layout/contracts.ts';
import { pointToRectEdge, quadraticBezier } from './layout/geometry.ts';

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  })[character] ?? character);
}

function markerMarkup({
  dayLabel,
  city,
  isCluster,
  memberCount,
  isActive,
  typographyClassName,
}: {
  dayLabel: string;
  city: string;
  isCluster: boolean;
  memberCount: number;
  isActive: boolean;
  typographyClassName: string;
}) {
  const badge = isCluster ? String(memberCount) : dayLabel;
  const label = isCluster ? 'STOPS' : city;
  const ariaLabel = isCluster ? `${memberCount} itinerary stops including ${city}` : `${dayLabel}, ${city}`;
  return `<button type="button" class="display-route-map-marker display-route-map-marker--classic display-route-map-marker--planned${isActive ? ' is-active' : ''}" aria-label="${escapeHtml(ariaLabel)}">
    <span class="display-route-map-marker__capsule">
      <span class="display-route-map-marker__badge ${typographyClassName}">${escapeHtml(badge)}</span>
      <span class="display-route-map-marker__label ${typographyClassName}">${escapeHtml(label)}</span>
    </span>
  </button>`;
}

function getMarkerButton(marker: Marker): HTMLButtonElement | null {
  const element = marker.getElement();
  if (element instanceof HTMLButtonElement) return element;
  return element?.querySelector<HTMLButtonElement>('button') ?? null;
}

/**
 * Leaflet applies an icon anchor after the browser has laid out the capsule.
 * Use that final DOM rectangle for the last, short leader segment so a font
 * metric or div-icon offset can never leave a label visually disconnected.
 */
function resolveRenderedLeader(map: LeafletMap, marker: Marker, plannedPoint: { x: number; y: number }) {
  const capsule = getMarkerButton(marker);
  if (!capsule) return null;
  const mapRect = map.getContainer().getBoundingClientRect();
  const capsuleRect = capsule.getBoundingClientRect();
  const source = map.latLngToContainerPoint(marker.getLatLng());
  const rect = {
    x: capsuleRect.left - mapRect.left,
    y: capsuleRect.top - mapRect.top,
    width: capsuleRect.width,
    height: capsuleRect.height,
  };
  const from = { x: source.x, y: source.y };
  const to = pointToRectEdge(from, rect);
  if (Math.hypot(to.x - from.x, to.y - from.y) < 0.01) return null;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.hypot(dx, dy);
  const normal = { x: -dy / length, y: dx / length };
  const bend = Math.min(4, length * 0.12) * (plannedPoint.x <= to.x ? 1 : -1);
  return quadraticBezier(
    from,
    { x: (from.x + to.x) / 2 + normal.x * bend, y: (from.y + to.y) / 2 + normal.y * bend },
    to,
    6
  );
}

export function WebRouteMapMarkerLayer({
  map,
  plan,
  segments,
  activeSequence,
  typographyClassName,
  leaderColor,
  routeColor,
  markerColor,
  activeMarkerColor,
  onSelect,
}: {
  map: LeafletMap | null;
  plan: WebRouteMapLayoutPlan | null;
  segments: RouteSegmentViewModel[];
  activeSequence: string;
  typographyClassName: string;
  leaderColor: string;
  routeColor: string;
  markerColor: string;
  activeMarkerColor: string;
  onSelect: (sequence: string) => void;
}) {
  const markerRef = useRef<Map<string, Marker>>(new Map());
  const leaderRef = useRef<Polyline[]>([]);
  const pinRef = useRef<CircleMarker[]>([]);
  const pendingKeyboardFocusRef = useRef<string | null>(null);
  useEffect(() => {
    const markers = markerRef.current;
    const leaders = leaderRef.current;
    const pins = pinRef.current;
    markers.forEach((marker) => marker.remove());
    markers.clear();
    leaders.forEach((line) => line.remove());
    leaders.length = 0;
    pins.forEach((pin) => pin.remove());
    pins.length = 0;
    if (!map || !plan) return;
    const segmentBySequence = new Map(segments.map((segment) => [segment.sequence, segment]));
    const orderedSequences = segments.map((segment) => segment.sequence);
    for (const placement of plan.markers) {
      const segment = segmentBySequence.get(placement.sequence);
      if (!segment) continue;
      const isActive = placement.memberSequences.includes(activeSequence);
      const icon = L.divIcon({
        className: 'display-route-map-marker-icon display-route-map-marker-icon--planned',
        html: markerMarkup({
          dayLabel: textValue(segment.dayLabel),
          city: textValue(segment.city),
          isCluster: placement.isCluster,
          memberCount: placement.memberSequences.length,
          isActive,
          typographyClassName,
        }),
        iconSize: [placement.rect.width, placement.rect.height],
        iconAnchor: [placement.point.x - placement.rect.x, placement.point.y - placement.rect.y],
      });
      const marker = L.marker(map.containerPointToLatLng([placement.point.x, placement.point.y]) as LatLngExpression, { icon, keyboard: true });
      marker.on('click', () => onSelect(placement.sequence));
      marker.on('add', () => {
        const button = getMarkerButton(marker);
        button?.addEventListener('keydown', (event) => {
          if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
          event.preventDefault();
          const currentIndex = orderedSequences.indexOf(placement.sequence);
          const nextIndex = event.key === 'ArrowLeft' ? currentIndex - 1 : currentIndex + 1;
          if (nextIndex >= 0 && nextIndex < orderedSequences.length) {
            const nextSequence = orderedSequences[nextIndex];
            pendingKeyboardFocusRef.current = nextSequence;
            onSelect(nextSequence);
          }
        });
      });
      const isDirectlyActive = placement.sequence === activeSequence;
      marker.addTo(map);
      const renderedLeader = resolveRenderedLeader(map, marker, placement.point);
      const leader = renderedLeader
        ? L.polyline(
            renderedLeader.map((point) => map.containerPointToLatLng([point.x, point.y])),
            {
              color: isActive ? routeColor : leaderColor,
              weight: isActive ? 2 : 1.5,
              opacity: 1,
              lineCap: 'round',
              lineJoin: 'round',
              interactive: false,
            }
          ).addTo(map)
        : null;
      const pin = L.circleMarker(map.containerPointToLatLng([placement.point.x, placement.point.y]), {
        radius: isDirectlyActive ? 5 : 4,
        color: isDirectlyActive ? activeMarkerColor : markerColor,
        fillColor: isDirectlyActive ? activeMarkerColor : markerColor,
        fillOpacity: 1,
        weight: 1.5,
        interactive: false,
      }).addTo(map);
      if (pendingKeyboardFocusRef.current === placement.sequence) {
        requestAnimationFrame(() => {
          getMarkerButton(marker)?.focus();
          pendingKeyboardFocusRef.current = null;
        });
      }
      markers.set(placement.sequence, marker);
      if (leader) leaders.push(leader);
      pins.push(pin);
    }
    return () => {
      markers.forEach((marker) => marker.remove());
      markers.clear();
      leaders.forEach((line) => line.remove());
      leaders.length = 0;
      pins.forEach((pin) => pin.remove());
      pins.length = 0;
    };
  }, [activeMarkerColor, activeSequence, leaderColor, map, markerColor, onSelect, plan, routeColor, segments, typographyClassName]);
  return null;
}
