'use client';

import L from 'leaflet';

let isPatched = false;

interface PatchedDraggable {
  _enabled: boolean;
  _moved: boolean;
  _moving: boolean;
  _element: HTMLElement;
  _dragStartTarget: HTMLElement;
  _preventOutline?: boolean;
  _ownerDoc?: Document | null;
  _startPoint: L.Point;
  _startPos: L.Point;
  _parentScale: { x: number; y: number };
  _lastTarget?: EventTarget | null;
  _newPos: L.Point;
  _lastEvent?: Event;
  options: {
    clickTolerance: number;
  };
  fire: (type: string, data?: Record<string, unknown>) => void;
  _onMove: (e: MouseEvent | TouchEvent) => void;
  _onUp: () => void;
  _updatePosition: () => void;
  finishDrag: (noInertia?: boolean) => void;
}

/**
 * Ensures Leaflet's Draggable and DOM utilities properly respect iframe and
 * multi-document React Portal boundaries.
 *
 * In standard Leaflet 1.9.x, L.Draggable hardcodes global `document` for mouse/touch
 * event listeners and body class manipulation. When Leaflet maps are mounted inside
 * an iframe (such as the Live Preview canvas), events inside the iframe do not bubble
 * to the parent `window.document`, preventing dragging until the cursor leaves the iframe.
 */
export function ensureLeafletPatched(): void {
  if (isPatched || typeof window === 'undefined' || !L || !L.Draggable) {
    return;
  }

  isPatched = true;

  // 1. Patch L.DomUtil.getSizedParentNode to avoid crossing outside an iframe root.
  L.DomUtil.getSizedParentNode = function (element: HTMLElement): HTMLElement {
    let current: HTMLElement | null = element;
    const rootBody = element?.ownerDocument?.body ?? (typeof document !== 'undefined' ? document.body : null);
    do {
      current = (current?.parentNode as HTMLElement | null) ?? null;
    } while (current && (!current.offsetWidth || !current.offsetHeight) && current !== rootBody);
    return current || rootBody || element;
  };

  // 2. Patch L.Draggable.prototype._onDown
  L.Draggable.prototype._onDown = function (this: PatchedDraggable, e: MouseEvent | TouchEvent) {
    if (!this._enabled) return;

    this._moved = false;

    if (L.DomUtil.hasClass(this._element, 'leaflet-zoom-anim')) return;

    const touchEvent = e as TouchEvent;
    if (touchEvent.touches && touchEvent.touches.length !== 1) {
      if ((L.Draggable as unknown as { _dragging: unknown })._dragging === this) {
        this.finishDrag();
      }
      return;
    }

    const mouseEvent = e as MouseEvent;
    if (
      (L.Draggable as unknown as { _dragging: unknown })._dragging ||
      mouseEvent.shiftKey ||
      (mouseEvent.which !== 1 && mouseEvent.button !== 1 && !touchEvent.touches)
    ) {
      return;
    }

    (L.Draggable as unknown as { _dragging: unknown })._dragging = this;

    if (this._preventOutline) {
      L.DomUtil.preventOutline(this._element);
    }

    L.DomUtil.disableImageDrag();
    L.DomUtil.disableTextSelection();

    if (this._moving) return;

    this.fire('down');

    const first = touchEvent.touches ? touchEvent.touches[0] : (e as MouseEvent);
    const sizedParent = L.DomUtil.getSizedParentNode(this._element);

    this._startPoint = new L.Point(first.clientX, first.clientY);
    this._startPos = L.DomUtil.getPosition(this._element);
    this._parentScale = L.DomUtil.getScale(sizedParent);

    const isMouseEvent = e.type === 'mousedown';
    const ownerDoc = this._element?.ownerDocument || (typeof document !== 'undefined' ? document : null);
    this._ownerDoc = ownerDoc;

    if (ownerDoc) {
      L.DomEvent.on(ownerDoc, isMouseEvent ? 'mousemove' : 'touchmove', this._onMove, this);
      L.DomEvent.on(ownerDoc, isMouseEvent ? 'mouseup' : 'touchend touchcancel', this._onUp, this);
    }

    if (typeof document !== 'undefined' && ownerDoc !== document) {
      L.DomEvent.on(document, isMouseEvent ? 'mouseup' : 'touchend touchcancel', this._onUp, this);
    }
  };

  // 3. Patch L.Draggable.prototype._onMove
  L.Draggable.prototype._onMove = function (this: PatchedDraggable, e: MouseEvent | TouchEvent) {
    if (!this._enabled) return;

    const touchEvent = e as TouchEvent;
    if (touchEvent.touches && touchEvent.touches.length > 1) {
      this._moved = true;
      return;
    }

    const first = touchEvent.touches && touchEvent.touches.length === 1 ? touchEvent.touches[0] : (e as MouseEvent);
    const offset = new L.Point(first.clientX, first.clientY)._subtract(this._startPoint);

    if (!offset.x && !offset.y) return;
    if (Math.abs(offset.x) + Math.abs(offset.y) < this.options.clickTolerance) return;

    offset.x /= this._parentScale.x;
    offset.y /= this._parentScale.y;

    L.DomEvent.preventDefault(e);

    const ownerDoc = this._ownerDoc || this._element?.ownerDocument || (typeof document !== 'undefined' ? document : null);

    if (!this._moved) {
      this.fire('dragstart');
      this._moved = true;

      if (ownerDoc?.body) {
        L.DomUtil.addClass(ownerDoc.body, 'leaflet-dragging');
      }
      if (typeof document !== 'undefined' && ownerDoc !== document && document.body) {
        L.DomUtil.addClass(document.body, 'leaflet-dragging');
      }

      this._lastTarget = (e.target || (e as unknown as { srcElement: EventTarget }).srcElement) as EventTarget | null;
      if (
        typeof window !== 'undefined' &&
        (window as unknown as { SVGElementInstance?: unknown }).SVGElementInstance &&
        this._lastTarget instanceof (window as unknown as { SVGElementInstance: unknown }).SVGElementInstance
      ) {
        this._lastTarget = (this._lastTarget as unknown as { correspondingUseElement: EventTarget }).correspondingUseElement;
      }
      if (typeof HTMLElement !== 'undefined' && this._lastTarget instanceof HTMLElement) {
        L.DomUtil.addClass(this._lastTarget, 'leaflet-drag-target');
      }
    }

    this._newPos = this._startPos.add(offset);
    this._moving = true;
    this._lastEvent = e;
    this._updatePosition();
  };

  // 4. Patch L.Draggable.prototype.finishDrag
  L.Draggable.prototype.finishDrag = function (this: PatchedDraggable, noInertia?: boolean) {
    const ownerDoc = this._ownerDoc || this._element?.ownerDocument || (typeof document !== 'undefined' ? document : null);

    if (ownerDoc?.body) {
      L.DomUtil.removeClass(ownerDoc.body, 'leaflet-dragging');
    }
    if (typeof document !== 'undefined' && ownerDoc !== document && document.body) {
      L.DomUtil.removeClass(document.body, 'leaflet-dragging');
    }

    if (typeof HTMLElement !== 'undefined' && this._lastTarget instanceof HTMLElement) {
      L.DomUtil.removeClass(this._lastTarget, 'leaflet-drag-target');
      this._lastTarget = null;
    }

    if (ownerDoc) {
      L.DomEvent.off(ownerDoc, 'mousemove touchmove', this._onMove, this);
      L.DomEvent.off(ownerDoc, 'mouseup touchend touchcancel', this._onUp, this);
    }
    if (typeof document !== 'undefined' && ownerDoc !== document) {
      L.DomEvent.off(document, 'mousemove touchmove', this._onMove, this);
      L.DomEvent.off(document, 'mouseup touchend touchcancel', this._onUp, this);
    }

    L.DomUtil.enableImageDrag();
    L.DomUtil.enableTextSelection();

    const fireDragend = this._moved && this._moving;

    this._moving = false;
    (L.Draggable as unknown as { _dragging: unknown })._dragging = false;
    this._ownerDoc = null;

    if (fireDragend) {
      this.fire('dragend', {
        noInertia: Boolean(noInertia),
        distance: this._newPos.distanceTo(this._startPos),
      });
    }
  };
}
