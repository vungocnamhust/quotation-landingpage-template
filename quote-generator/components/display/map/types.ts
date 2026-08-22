import type { ViewMode } from '../../../display/contracts.ts';
import type { RouteMapViewModel, TypographySlotMap } from '../../../display/types.ts';
import type { MapTileStyle } from '../../../lib/mapTileStyles.ts';

export type MapRenderState = 'loading' | 'ready' | 'failed' | 'unavailable';

export interface ProjectedPoint {
  x: number;
  y: number;
  visible: boolean;
}

export interface GeoLocationLabel {
  id: string;
  name: string;
  subName?: string;
  coordinates: [number, number]; // [lat, lng]
  type: 'country' | 'sea' | 'island';
  sovereignty?: string;
}

export interface MapColors {
  route: string;
  marker?: string;
  activeMarker?: string;
  land?: string;
  ocean?: string;
}

export interface FullPageMapProps {
  viewModel: RouteMapViewModel;
  typography: TypographySlotMap;
  mapColors: MapColors;
  viewMode: ViewMode;
  className?: string;
  onSegmentSelect?: (sequence: string) => void;
  activeSequence?: string;
  quotationNumber?: string;
  pageNumber?: string;
  quoteText?: string;
  onRenderStateChange?: (state: MapRenderState) => void;
}

export type { MapTileStyle };
