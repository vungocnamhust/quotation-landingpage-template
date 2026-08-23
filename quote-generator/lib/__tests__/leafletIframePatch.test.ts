import test from 'node:test';
import assert from 'node:assert/strict';

if (typeof globalThis.window === 'undefined') {
  const mockDoc: Record<string, unknown> = {
    documentElement: { style: {} },
    createElement: () => ({ style: {}, className: '', appendChild: () => undefined }),
    createElementNS: () => ({ style: {}, className: '', createSVGRect: () => undefined }),
    body: { style: {}, className: '', classList: { add: () => undefined, remove: () => undefined } },
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  };
  (globalThis as unknown as { window: unknown }).window = {
    document: mockDoc,
    navigator: { userAgent: 'node' },
    devicePixelRatio: 1,
    screen: { deviceXDPI: 1, logicalXDPI: 1 },
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    requestAnimationFrame: (cb: () => void) => setTimeout(cb, 0),
    cancelAnimationFrame: () => undefined,
    SVGElementInstance: class {},
  };
  (globalThis as unknown as { document: unknown }).document = mockDoc;
}

const { default: L } = await import('leaflet');
const { ensureLeafletPatched } = await import('../../components/display/map/web/leafletPatch.ts');

test('ensureLeafletPatched: idempotently applies patch to Leaflet prototypes', () => {
  assert.doesNotThrow(() => {
    ensureLeafletPatched();
    ensureLeafletPatched();
  });
});

test('ensureLeafletPatched: getSizedParentNode safely bounds to element ownerDocument body', () => {
  ensureLeafletPatched();

  // Create mock iframe-like DOM tree
  const mockIframeBody = {
    className: '',
    offsetWidth: 800,
    offsetHeight: 600,
    parentNode: null,
  };
  const mockIframeDoc = {
    body: mockIframeBody,
  };
  const mapPane = {
    className: '',
    offsetWidth: 0,
    offsetHeight: 0,
    parentNode: mockIframeBody,
    ownerDocument: mockIframeDoc,
  };

  const sizedNode = L.DomUtil.getSizedParentNode(mapPane as unknown as HTMLElement);
  assert.equal(sizedNode, mockIframeBody, 'getSizedParentNode should resolve to mock iframe body');
});

test('ensureLeafletPatched: Draggable prototype uses element ownerDocument for event listeners', () => {
  ensureLeafletPatched();

  const eventsRegistered: Array<{ target: unknown; event: string }> = [];
  const eventsRemoved: Array<{ target: unknown; event: string }> = [];

  const originalOn = L.DomEvent.on;
  const originalOff = L.DomEvent.off;

  // Intercept DomEvent.on / off for testing
  (L.DomEvent as unknown as { on: unknown }).on = (target: unknown, types: string) => {
    types.split(' ').forEach((type) => {
      eventsRegistered.push({ target, event: type });
    });
  };
  (L.DomEvent as unknown as { off: unknown }).off = (target: unknown, types: string) => {
    types.split(' ').forEach((type) => {
      eventsRemoved.push({ target, event: type });
    });
  };

  try {
    const mockIframeDoc = {
      body: {
        className: '',
        offsetWidth: 1000,
        offsetHeight: 800,
        parentNode: null,
      },
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    };

    const containerEl = {
      className: '',
      offsetWidth: 1000,
      offsetHeight: 800,
      parentNode: mockIframeDoc.body,
      ownerDocument: mockIframeDoc,
      style: {},
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 800 }),
    };

    const mapPane = {
      className: '',
      offsetWidth: 1000,
      offsetHeight: 800,
      parentNode: containerEl,
      ownerDocument: mockIframeDoc,
      style: {},
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      _leaflet_pos: new L.Point(0, 0),
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 800 }),
    };

    const draggable = new L.Draggable(mapPane as unknown as HTMLElement, containerEl as unknown as HTMLElement);
    draggable.enable();

    // Simulate mousedown (_onDown)
    const mockMouseDown = {
      type: 'mousedown',
      clientX: 100,
      clientY: 100,
      button: 0,
      which: 1,
      preventDefault: () => undefined,
      stopPropagation: () => undefined,
    } as unknown as MouseEvent;

    draggable._onDown(mockMouseDown);

    // Verify listeners registered on mockIframeDoc
    const moveListener = eventsRegistered.find((r) => r.target === mockIframeDoc && r.event === 'mousemove');
    const upListener = eventsRegistered.find((r) => r.target === mockIframeDoc && r.event === 'mouseup');
    assert.ok(moveListener, 'Draggable should register mousemove on ownerDocument');
    assert.ok(upListener, 'Draggable should register mouseup on ownerDocument');

    // Simulate drag finish
    draggable.finishDrag();

    // Verify listeners cleaned up on mockIframeDoc
    const moveRemoved = eventsRemoved.find((r) => r.target === mockIframeDoc && r.event === 'mousemove');
    const upRemoved = eventsRemoved.find((r) => r.target === mockIframeDoc && r.event === 'mouseup');
    assert.ok(moveRemoved, 'Draggable should remove mousemove from ownerDocument on finishDrag');
    assert.ok(upRemoved, 'Draggable should remove mouseup from ownerDocument on finishDrag');
  } finally {
    (L.DomEvent as unknown as { on: unknown }).on = originalOn;
    (L.DomEvent as unknown as { off: unknown }).off = originalOff;
  }
});
