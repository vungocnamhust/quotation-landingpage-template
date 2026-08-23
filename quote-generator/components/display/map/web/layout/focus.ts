import type { ViewMode } from '../../../../../display/contracts.ts';

export function resolveWebRouteMapFocusZoom(currentZoom: number, viewMode: Exclude<ViewMode, 'pdf'>): number {
  return Math.max(currentZoom, viewMode === 'mobile' ? 6.4 : 7.6);
}
