import type { TypographyVariant } from '../config/typography';
import type { TypographySlotMap } from './types';

export function requireTypographySlot(
  typography: TypographySlotMap,
  slot: keyof TypographySlotMap
): TypographyVariant {
  const variant =
    typography[slot] ??
    (slot === 'action'
      ? typography.metaPrimary ?? 'buttonSecondary'
      : slot === 'badge'
        ? typography.metaPrimary ?? 'timelineTitle'
        : slot === 'index'
          ? typography.metaSecondary ?? 'caption'
          : slot === 'link'
            ? typography.metaPrimary ?? 'topbarSectionLink'
            : slot === 'label'
              ? typography.metaSecondary ?? 'label'
              : undefined);
  if (!variant) {
    throw new Error(`Missing typography slot: ${String(slot)}`);
  }
  return variant;
}


