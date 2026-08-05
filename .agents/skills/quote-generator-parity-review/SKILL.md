---
name: quote-generator-parity-review
description: Audit quote-generator brochure UI against the prototype source of truth. Use when users ask for review, drift analysis, parity gaps, compare with prototype, or responsive/pdf fidelity checks. Compare current components, layout composition, typography, shell language, and view-mode behavior against templates/prototype_itinerary_imagery.html and templates/prototype_itinerary_imagery_pdf.html.
---

# Quote Generator Parity Review

Review brochure UI with a prototype-first mindset and a source-contract audit.
Visual parity is not sufficient when typography or theme slots can drift at
runtime.

## Read First

- Read `templates/prototype_itinerary_imagery.html`.
- Read `templates/prototype_itinerary_imagery_pdf.html`.
- Read `quote-generator/docs/display-system-contract.md`.
- Read `quote-generator/docs/typography-contract.md` and `quote-generator/config/typography.ts` when typography is in scope.
- Read `quote-generator/config/themeTokens.ts`, `quote-generator/display/validateColorContracts.ts`, and `quote-generator/scripts/lint-colors.mjs` for any color, button, shell, map, or brand-switching review.

## Review Workflow

1. Compare section order and composition before visual details.
2. Check each section across `desktop`, `mobile`, and `pdf`.
3. Review these categories in order:
   - app chrome and public navigation
   - layout ratios and DOM order
   - shell/surface/ornament language
   - brand palette and theme color recipe
   - typography hierarchy
   - interaction parity such as route-map behavior
4. Report findings first, with file references and concrete drift descriptions.
5. Audit implementation ownership:
   - typography: config -> semantic class -> theme slot -> molecule/atom consumer
   - color: brand palette -> theme recipe -> resolved scope -> component role/CSS variable
6. Check the brand x theme x view-mode matrix for color scope presence, action contrast, focus contrast, and absence of color fallbacks.
7. Run the deterministic display, typography, and color audits and record failures separately from visual findings.

## Hard Guardrails

- Prefer source-of-truth prototype evidence over generic design opinions.
- Flag dead config when theme contracts exist but runtime consumers do not.
- Call out missing tests or missing view-mode coverage if parity cannot be trusted.
- Treat hardcoded CSS typography, font loading outside the declared owner, and molecule-level variant literals as parity blockers, even when the screenshot looks correct.
- Treat hardcoded colors, legacy color variables, missing `colorScope`, missing `colorSlots`, failed contrast, and app-chrome scope leakage as parity blockers.
- Do not close a parity review on `npm run lint:typography` alone; it must be paired with the contract audit and build.

## Use References

- Audit checklist: `references/parity-checklist.md`
- Section-by-section prototype map: `references/prototype-map.md`
