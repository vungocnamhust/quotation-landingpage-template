export { HelpTooltip, default } from "./HelpTooltip.tsx";
export type {
  HelpTooltipProps,
  HelpTooltipSize,
  HelpTooltipVariant,
} from "./HelpTooltip.tsx";

export {
  useTooltip,
  computeTooltipPosition,
} from "./useTooltip.ts";
export type {
  UseTooltipOptions,
  UseTooltipReturn,
  TooltipPlacement,
  ComputePositionOptions,
  RectLike,
} from "./useTooltip.ts";

export {
  COSTING_GLOSSARY,
  ALL_COSTING_CONCEPT_KEYS,
  getCostingGlossary,
  resolveTooltipContent,
} from "../../../lib/glossary/costingGlossary.ts";
export type {
  CostingConceptKey,
  CostingGlossaryEntry,
  ResolveTooltipContentInput,
  ResolvedTooltipContent,
} from "../../../lib/glossary/costingGlossary.ts";
