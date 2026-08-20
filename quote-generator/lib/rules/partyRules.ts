/**
 * Pure domain rules for party composition, guest identity, and greeting labels (TypeScript).
 * Re-exports from partyReconciler for backward compatibility.
 */

export {
  resolveClientDisplayName,
  generatePartyLabel,
  inferGreetingName,
  calculateMinEstimatedRooms,
  generateRoomSuggestions,
  partyReconciler,
} from "./partyReconciler.ts";

