import type { WebRouteMapLayoutInput, WebRouteMapLayoutPlan } from './contracts.ts';
import { distance, pointToRectEdge, polylineIntersectsRect, polylineLength, polylinesIntersect, rectsOverlap } from './geometry.ts';

export function validateWebRouteMapLayout(
  input: WebRouteMapLayoutInput,
  plan: WebRouteMapLayoutPlan
): string[] {
  const errors: string[] = [];
  const clearance = input.minimumClearance ?? 12;
  const maximumLeaderLength = input.maxLeaderLength ?? 28;
  for (const marker of plan.markers) {
    const leaderEnd = marker.leader.at(-1);
    if (!leaderEnd || distance(marker.leader[0], marker.point) > 0.01) {
      errors.push(`marker ${marker.sequence} leader is not wired to its geographic pin`);
    } else if (distance(leaderEnd, pointToRectEdge(marker.point, marker.rect)) > 0.01) {
      errors.push(`marker ${marker.sequence} leader is not wired to its capsule`);
    }
    if (
      marker.rect.x < clearance ||
      marker.rect.y < clearance ||
      marker.rect.x + marker.rect.width > input.viewport.width - clearance ||
      marker.rect.y + marker.rect.height > input.viewport.height - clearance
    ) {
      errors.push(`marker ${marker.sequence} is clipped`);
    }
  }
  for (let index = 0; index < plan.markers.length; index += 1) {
    for (let otherIndex = index + 1; otherIndex < plan.markers.length; otherIndex += 1) {
      if (rectsOverlap(plan.markers[index].rect, plan.markers[otherIndex].rect, clearance)) {
        errors.push(`markers ${plan.markers[index].sequence} and ${plan.markers[otherIndex].sequence} overlap`);
      }
    }
  }
  for (const marker of plan.markers) {
    if (polylineLength(marker.leader) > maximumLeaderLength + 0.01) {
      errors.push(`marker ${marker.sequence} leader exceeds local-label limit`);
    }
  }
  for (const route of plan.routes) {
    if (route.points.length < 3 || route.curvature === undefined) {
      errors.push(`route ${route.id} is not curved`);
    }
    for (const marker of plan.markers) {
      if (marker.sequence === route.fromSequence || marker.sequence === route.toSequence) continue;
      if (polylineIntersectsRect(route.points, marker.rect, clearance / 2)) {
        errors.push(`route ${route.id} intersects ${marker.sequence}`);
      }
    }
  }
  for (let index = 0; index < plan.routes.length; index += 1) {
    for (let otherIndex = index + 1; otherIndex < plan.routes.length; otherIndex += 1) {
      const a = plan.routes[index];
      const b = plan.routes[otherIndex];
      const sharesStop =
        a.fromSequence === b.fromSequence ||
        a.fromSequence === b.toSequence ||
        a.toSequence === b.fromSequence ||
        a.toSequence === b.toSequence;
      if (!sharesStop && polylinesIntersect(a.points, b.points)) {
        errors.push(`routes ${a.id} and ${b.id} intersect`);
      }
    }
  }
  return errors;
}
