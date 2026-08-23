import type { MapPoint, MapRect } from './contracts.ts';

export function distance(a: MapPoint, b: MapPoint): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function rectContainsPoint(rect: MapRect, point: MapPoint, padding = 0): boolean {
  return (
    point.x >= rect.x - padding &&
    point.x <= rect.x + rect.width + padding &&
    point.y >= rect.y - padding &&
    point.y <= rect.y + rect.height + padding
  );
}

export function rectsOverlap(a: MapRect, b: MapRect, padding = 0): boolean {
  return !(
    a.x + a.width + padding <= b.x ||
    b.x + b.width + padding <= a.x ||
    a.y + a.height + padding <= b.y ||
    b.y + b.height + padding <= a.y
  );
}

export function pointToRectEdge(point: MapPoint, rect: MapRect): MapPoint {
  const clampedX = Math.min(Math.max(point.x, rect.x), rect.x + rect.width);
  const clampedY = Math.min(Math.max(point.y, rect.y), rect.y + rect.height);
  return { x: clampedX, y: clampedY };
}

function cross(a: MapPoint, b: MapPoint, c: MapPoint): number {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

function onSegment(a: MapPoint, b: MapPoint, c: MapPoint): boolean {
  return (
    Math.min(a.x, b.x) <= c.x && c.x <= Math.max(a.x, b.x) &&
    Math.min(a.y, b.y) <= c.y && c.y <= Math.max(a.y, b.y)
  );
}

export function segmentsIntersect(a: MapPoint, b: MapPoint, c: MapPoint, d: MapPoint): boolean {
  const abC = cross(a, b, c);
  const abD = cross(a, b, d);
  const cdA = cross(c, d, a);
  const cdB = cross(c, d, b);

  if (abC === 0 && onSegment(a, b, c)) return true;
  if (abD === 0 && onSegment(a, b, d)) return true;
  if (cdA === 0 && onSegment(c, d, a)) return true;
  if (cdB === 0 && onSegment(c, d, b)) return true;

  return (abC > 0) !== (abD > 0) && (cdA > 0) !== (cdB > 0);
}

export function segmentIntersectsRect(from: MapPoint, to: MapPoint, rect: MapRect, padding = 0): boolean {
  const expanded: MapRect = {
    x: rect.x - padding,
    y: rect.y - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
  if (rectContainsPoint(expanded, from) || rectContainsPoint(expanded, to)) return true;
  const topLeft = { x: expanded.x, y: expanded.y };
  const topRight = { x: expanded.x + expanded.width, y: expanded.y };
  const bottomRight = { x: expanded.x + expanded.width, y: expanded.y + expanded.height };
  const bottomLeft = { x: expanded.x, y: expanded.y + expanded.height };
  return (
    segmentsIntersect(from, to, topLeft, topRight) ||
    segmentsIntersect(from, to, topRight, bottomRight) ||
    segmentsIntersect(from, to, bottomRight, bottomLeft) ||
    segmentsIntersect(from, to, bottomLeft, topLeft)
  );
}

export function polylineIntersectsRect(points: MapPoint[], rect: MapRect, padding = 0): boolean {
  for (let index = 0; index < points.length - 1; index += 1) {
    if (segmentIntersectsRect(points[index], points[index + 1], rect, padding)) return true;
  }
  return false;
}

export function polylinesIntersect(a: MapPoint[], b: MapPoint[]): boolean {
  for (let aIndex = 0; aIndex < a.length - 1; aIndex += 1) {
    for (let bIndex = 0; bIndex < b.length - 1; bIndex += 1) {
      if (segmentsIntersect(a[aIndex], a[aIndex + 1], b[bIndex], b[bIndex + 1])) return true;
    }
  }
  return false;
}

export function quadraticBezier(from: MapPoint, control: MapPoint, to: MapPoint, samples = 18): MapPoint[] {
  return Array.from({ length: samples + 1 }, (_, index) => {
    const t = index / samples;
    const inverse = 1 - t;
    return {
      x: inverse * inverse * from.x + 2 * inverse * t * control.x + t * t * to.x,
      y: inverse * inverse * from.y + 2 * inverse * t * control.y + t * t * to.y,
    };
  });
}

export function polylineLength(points: MapPoint[]): number {
  return points.slice(1).reduce((total, point, index) => total + distance(points[index], point), 0);
}
