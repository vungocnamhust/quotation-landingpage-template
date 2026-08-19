---
name: react-component-reuse-governor
description: Enforce standards for reusable, modular, and maintainable React components across the codebase. Use when creating new UI components, refactoring duplicated input controls/pickers/selectors, designing component props APIs, separating headless data hooks from presentation, or standardizing design system elements for Codex and Antigravity.
---

# React Component Reuse & Maintainability Governor

Govern the architecture, props design, styling, and behavior of all reusable React components in the workspace to ensure maximum modularity, reusability, accessibility, and zero code duplication.

## When to Apply

Activate and follow this skill whenever:
- Creating a new form input, selector, picker, modal, or UI component.
- Refactoring fragmented or duplicated UI logic across multiple pages/forms.
- Designing component props interfaces, callbacks, and polymorphic modes.
- Decomposing monolithic components into clean headless hooks and view renderers.
- Standardizing design system controls to work seamlessly in multiple layouts (Full forms, Modals, Table rows, Grids).

---

## The 5 Golden Standards for Reusable Components

Every reusable React component must comply with these **5 Golden Standards**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   5 Golden Reusability Standards                       │
├────────────────────────────────────────────────────────────────────────┤
│  1. Headless Hook Extraction      ──► Decouple state/fetch from JSX   │
│  2. Flexible Value Contract       ──► Controlled, Dual callback, Cast  │
│  3. Size & Variant Matrix         ──► sm/md/lg, default/compact/inline │
│  4. Encapsulated Semantic Tokens  ──► CSS vars, getTypographyClassName │
│  5. Built-in Keyboard & A11y      ──► ARIA, Arrow/Esc, Outside Click   │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Headless Hook Extraction Pattern
- **Rule**: Never embed inline SWR/fetch requests, complex debounce routines, or extensive search/filter algorithms directly within the JSX render component.
- **Implementation**: Always extract into a dedicated custom hook:
  - `use[Feature]Search.ts` or `use[Feature]State.ts` (handles SWR caching, debounce, fallback items, query transformations).
  - `[Feature]Component.tsx` (pure presentation, accepts props, binds event handlers).
- **Benefit**: Presentation and data layer can be tested and modified independently. SWR cache keys are shared and deduplicated across consumers.

### 2. Flexible Value & Change Contract
- **Rule**: Reusable controls must accept flexible value types (both raw primitive `string` and canonical `Object / Ref`) without forcing caller type gymnastics.
- **Unified Callback**: Provide a single, comprehensive `onChange` handler:
  ```typescript
  onChange?: (value: string | null, ref?: ItemRef | null) => void;
  ```
  *Avoid the "dual-callback anti-pattern"* where callers are forced to supply both `onChange` and `onSelect` with messy dual synchronization.
- **Custom Input Escape Hatch**: Provide `allowCustom?: boolean` if users need to type values outside the predefined catalog.

### 3. Responsive Size & Variant Matrix
- **Rule**: Components must natively adapt to different spatial constraints without requiring parents to write hacky CSS overrides.
- **Standard Props**:
  - `size?: "sm" | "md" | "lg"` (default: `"md"`).
  - `variant?: "default" | "compact" | "inline"` (default: `"default"`).
- **Requirement**: `size="sm"` and `variant="compact"` must fit inside compact table cells (`h-9` or `min-h-9`) without overflowing vertical table layouts.

### 4. Encapsulated Semantic Tokens (SSOT Compliance)
- **Rule**: Never hardcode colors (`#hex`, `rgba(...)`), color classes (`bg-blue-500`), or raw tailwind typography metrics (`text-xs`, `font-bold`, `leading-6`) inside reusable component internals.
- **Implementation**:
  - **Colors**: Consume CSS variable semantic tokens: `var(--color-surface)`, `var(--color-surface-hover)`, `var(--color-on-surface)`, `var(--color-border)`, `var(--color-border-strong)`, `var(--color-accent)`, `var(--color-accent-wash)`, `var(--color-muted)`.
  - **Typography**: Consume Typography SSOT via `getTypographyClassName("bodyMd" | "bodySm" | "label" | "caption" | "buttonSecondary")`.

### 5. Built-in Keyboard & A11y Defaults
- **Rule**: Modals, popovers, comboboxes, and dropdowns must encapsulate their own accessibility behaviors out of the box:
  - Outside click listener (auto-closing when clicking outside).
  - Keyboard navigation (`ArrowDown`, `ArrowUp`, `Enter`, `Escape`, `Backspace` for chips).
  - Semantic ARIA attributes: `role="combobox"`, `role="listbox"`, `role="option"`, `aria-expanded`, `aria-haspopup`, `aria-selected`.
- **Benefit**: Zero boilerplate required by the parent consuming the component.

---

## Hard Guardrails

1. ❌ **Do not create multiple specialized components for single vs multi-selection when one polymorphic component can handle both** (use `mode="single" | "multiple"`).
2. ❌ **Do not hardcode static data arrays in forms when a centralized catalog API exists.**
3. ❌ **Do not use raw `<input>` without autocomplete in one form while other forms use a search selector.**
4. ❌ **Do not break existing consumers during refactors**; provide a thin backward-compatibility adapter wrapper if legacy components are being phased out.
5. ❌ **Do not bypass `getTypographyClassName` or theme CSS variables.**
6. ❌ **Do not embed domain calculations or state mutations (like date arithmetic, day re-indexing, stay consolidation) inside reusable UI components or grids**; always delegate calculations to Domain Reconcilers (`lib/rules/*Reconciler.ts`) via standard `onChange` dispatch.

---

## Component Creation & Refactoring Workflow

1. **Audit Existing Usage**: Search the repository for all occurrences of related inputs/controls (e.g. `grep_search`).
2. **Design Data Hook**: Extract data fetching, SWR caching, and fallback presets into `use[Feature]Search.ts`.
3. **Build Core Component**: Create `[Feature]Select.tsx` with Single/Multi modes, size/variant matrix, keyboard navigation, and popover combobox.
4. **Export Clean Public Interface**: Export types, hook, and component via `index.ts`.
5. **Update Legacy Adapters**: Keep old component names as alias wrappers over the new core component to prevent breaking changes.
6. **Migrate Forms & Views**: Replace ad-hoc inputs across all workspace forms with the new unified component.
7. **Run Quality Gates**:
   - `npm run lint`
   - `npm run lint:typography`
   - `npm run build`

---

## References & Examples

- Detailed API standards: `references/component-api-standards.md`
- Anti-patterns & refactoring guide: `references/anti-patterns.md`
- Canonical implementation example: `examples/DestinationSelectExample.tsx`
