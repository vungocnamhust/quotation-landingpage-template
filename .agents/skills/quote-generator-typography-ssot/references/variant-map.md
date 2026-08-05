# Variant Map

Read `quote-generator/docs/typography-contract.md` for the full public list.

Common brochure mappings:

- hero title -> `pageTitle`
- section kicker -> `chapterKicker`
- section title -> `chapterTitle`
- body copy -> `bodyLg` or `bodyMd`
- CTA text -> `buttonPrimary` or `buttonSecondary`
- topbar select label/value -> `topbarSelectLabel`, `topbarSelectValue`
- topbar action -> `topbarActionValue`

Before adding a new variant, check whether `navMeta`, `label`, `caption`, or existing button variants already cover the need.

## Consumer ownership

- Section renderers own slot selection through `displayConfig.typographySlots`.
- Reusable molecules must receive `TypographySlotMap` or an explicit `TypographyVariant` prop.
- `TextLink`, `ActionGroup`, `InclusionsPanel`, `TermRow`, `SupportBlock`, and designer blocks must not choose fixed variants internally.
- A slot declared by a theme must be consumed by the matching desktop/mobile/pdf render path.
- A text-bearing action must consume two independent slots: `typographySlots.action` for text metrics and `colorSlots.action` for color semantics.
- Topbar text consumes typography variants from `config/typography.ts` and the theme `appChrome` color scope; it is not allowed to borrow a brochure section scope implicitly.
