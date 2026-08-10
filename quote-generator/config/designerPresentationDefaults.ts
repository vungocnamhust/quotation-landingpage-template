/**
 * Prototype-aligned defaults for the per-quotation Designer presentation.
 * These are canonical Fact defaults; Design is only their editing surface.
 */
export const DESIGNER_PRESENTATION_DEFAULTS = {
  kicker: "YOUR JOURNEY DESIGNER",
  title: "Let Us Shape the Final Details Together",
  quote: "I believe the desire to travel is contagious—and it is my privilege to turn that inspiration into thoughtfully designed journeys filled with meaningful experiences, authentic connections, and lasting memories",
  signature: "TRAVEL DESIGNER",
  experience: "Present throughout the planning, quietly working behind the journey.",
  ctaBody: "",
} as const;

export type DesignerPresentationField = keyof typeof DESIGNER_PRESENTATION_DEFAULTS;
