/**
 * Display elements can opt out of workspace inspector capture when they own
 * native gestures (for example, a Leaflet map). The marker is deliberately
 * generic so the canvas remains responsible for selection while an interactive
 * component remains responsible for its own event lifecycle.
 */
export function isWorkspaceNativeInteractionTarget(target: EventTarget | null): boolean {
  if (!target || typeof target !== 'object' || !('closest' in target)) return false;
  const closest = (target as { closest?: unknown }).closest;
  return typeof closest === 'function'
    && closest.call(target, '[data-workspace-interactive="true"]') !== null;
}
