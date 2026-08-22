export type MapTileStyle = 'google-classic-v1' | 'google-classic-pdf-v1';

export type MapTileProvider = {
  id: 'google-classic' | 'carto-voyager' | 'openstreetmap';
  url: (zoom: number, x: number, y: number) => string;
};

const googleClassic: MapTileProvider = {
  id: 'google-classic',
  url: (zoom, x, y) => `https://mt1.google.com/vt/lyrs=m&x=${x}&y=${y}&z=${zoom}&hl=vi`,
};

const resilientClassicProviders: readonly MapTileProvider[] = [
  googleClassic,
  {
    id: 'carto-voyager',
    url: (zoom, x, y) => `https://a.basemaps.cartocdn.com/rastertiles/voyager/${zoom}/${x}/${y}.png`,
  },
  {
    id: 'openstreetmap',
    url: (zoom, x, y) => `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`,
  },
];

const pdfPrototypeProviders: readonly MapTileProvider[] = [googleClassic];

/**
 * Maps rendered for PDF must use the same Google classic raster as the
 * prototype. Screen maps retain independent-provider fallback for availability.
 */
export function resolveMapTileProviders(style: string | null): readonly MapTileProvider[] | null {
  switch (style) {
    case 'google-classic-v1':
      return resilientClassicProviders;
    case 'google-classic-pdf-v1':
      return pdfPrototypeProviders;
    default:
      return null;
  }
}
