export const VIEW_MODES = ['desktop', 'mobile', 'pdf'] as const;

export type ViewMode = (typeof VIEW_MODES)[number];

export const THEME_IDS = ['brochure'] as const;

export type ThemeId = (typeof THEME_IDS)[number];

export const LANGUAGE_CODES = ['en', 'vi', 'ar'] as const;

export type LanguageCode = (typeof LANGUAGE_CODES)[number];
