export type MapTileStyle = 'google-classic-v1' | 'carto-parchment-nolabels-pdf-v1';
export type MapTileRasterTreatment = 'passthrough' | 'parchment';

export type MapTileProvider = {
  id: 'google-classic' | 'carto-voyager' | 'carto-voyager-nolabels' | 'openstreetmap';
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

const pdfNoLabelProviders: readonly MapTileProvider[] = [
  {
    id: 'carto-voyager-nolabels',
    url: (zoom, x, y) => `https://a.basemaps.cartocdn.com/rastertiles/voyager_nolabels/${zoom}/${x}/${y}.png`,
  },
];

/**
 * PDF maps use a label-free raster so brochure-owned copy has a single visual
 * hierarchy. Screen maps retain independent-provider fallback for availability.
 */
export function resolveMapTileProviders(style: string | null): readonly MapTileProvider[] | null {
  switch (style) {
    case 'google-classic-v1':
      return resilientClassicProviders;
    case 'carto-parchment-nolabels-pdf-v1':
      return pdfNoLabelProviders;
    default:
      return null;
  }
}

export function resolveMapTileRasterTreatment(style: string | null): MapTileRasterTreatment | null {
  if (!resolveMapTileProviders(style)) {
    return null;
  }
  return style === 'carto-parchment-nolabels-pdf-v1' ? 'parchment' : 'passthrough';
}
