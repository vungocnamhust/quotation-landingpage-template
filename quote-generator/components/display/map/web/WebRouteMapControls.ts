'use client';

import type { LatLngBoundsExpression, Map as LeafletMap } from 'leaflet';
import L from 'leaflet';

const HAND_ICON = `
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M8 11V5a1.5 1.5 0 0 1 3 0v5m0-2V4a1.5 1.5 0 0 1 3 0v5m0-1V5a1.5 1.5 0 0 1 3 0v6m0-2V7a1.5 1.5 0 0 1 3 0v6c0 4.4-2.8 7-7 7h-1.1a6 6 0 0 1-4.3-1.8L3.4 14a1.5 1.5 0 0 1 2.1-2.1L8 14.4" />
  </svg>`;

/**
 * Native Leaflet control: manual panning is always available; this button
 * restores the authored bounds after a visitor has explored the map.
 */
export function addWebRouteMapControls(map: LeafletMap, defaultBounds: LatLngBoundsExpression): void {
  L.control.zoom({ position: 'topleft' }).addTo(map);

  const ResetControl = L.Control.extend({
    options: { position: 'topleft' },
    onAdd(controlMap: LeafletMap) {
      const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-web-route-map-reset');
      const button = L.DomUtil.create('button', 'leaflet-control-web-route-map-reset__button', container);
      button.type = 'button';
      button.setAttribute('aria-label', 'Enable map dragging and reset map position');
      button.setAttribute('title', 'Reset map position');
      button.innerHTML = HAND_ICON;
      L.DomEvent.disableClickPropagation(container);
      L.DomEvent.on(button, 'click', () => {
        controlMap.dragging.enable();
        controlMap.touchZoom.enable();
        controlMap.fitBounds(defaultBounds, { animate: true, duration: 0.45, maxZoom: 12 });
      });
      return container;
    },
  });

  new ResetControl().addTo(map);
}
