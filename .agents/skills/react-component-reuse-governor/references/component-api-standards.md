# Component API Standards & Reusability Guidelines

This document provides in-depth technical specifications for designing reusable React component APIs, managing controlled state, structuring headless hooks, and implementing accessibility.

---

## 1. Props Interface Architecture

A well-architected reusable component interface follows this structure:

```typescript
export type ComponentMode = "single" | "multiple";
export type ComponentSize = "sm" | "md" | "lg";
export type ComponentVariant = "default" | "compact" | "inline";

export interface ReusableSelectProps<T, TRef = { id: string; name: string }> {
  /** Mode: single (default) or multiple */
  mode?: ComponentMode;

  /** Value for single mode (supports primitive string or rich Ref object) */
  value?: string | TRef | null;

  /** Values for multiple mode */
  values?: TRef[];

  /**
   * Unified change handler
   * - In single mode: (name: string | null, ref: TRef | null) => void
   * - In multiple mode: (refs: TRef[]) => void
   */
  onChange?: (value: any, ref?: TRef | null) => void;

  /** Visual & Dimension modifiers */
  size?: ComponentSize;
  variant?: ComponentVariant;

  /** Form Field integration */
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  error?: string | null;
  helperText?: string;
  allowCustom?: boolean;

  /** Styling escape hatches */
  className?: string;
  inputClassName?: string;
  menuClassName?: string;

  /** Accessibility */
  "aria-label"?: string;
  id?: string;
}
```

---

## 2. Headless Hook Pattern

### Why Decouple?
Embedding data fetching directly in JSX components leads to:
- Inability to reuse the same data querying logic in headless or alternative view modes.
- Bloated component files that mix DOM layout, styling, keyboard listeners, and async HTTP logic.
- Difficulty writing pure unit tests for business logic vs UI layout.

### Implementation Pattern
```typescript
// useFeatureSearch.ts
export function useFeatureSearch(query: string) {
  const deferredQuery = useDeferredValue(query.trim());
  const hasQuery = deferredQuery.length >= 2;

  const { data, error, isLoading } = useSWR(
    hasQuery ? `/api/v2/items?query=${encodeURIComponent(deferredQuery)}` : null,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 30000 }
  );

  const results = useMemo(() => {
    if (!hasQuery) return POPULAR_FALLBACK_ITEMS;
    return data?.items ?? [];
  }, [hasQuery, data]);

  return { results, isLoading: hasQuery && isLoading, error, hasQuery };
}
```

---

## 3. Keyboard Navigation Checklist

Any combobox, dropdown, or popover must implement the following key interactions:

| Key | Context | Expected Action |
|---|---|---|
| `ArrowDown` | Dropdown closed | Opens the dropdown popover |
| `ArrowDown` | Dropdown open | Moves highlight index down (wraps to 0 at end) |
| `ArrowUp` | Dropdown open | Moves highlight index up (wraps to length - 1 at start) |
| `Enter` | Dropdown open | Selects currently highlighted item (or adds custom item if `allowCustom`) |
| `Escape` | Dropdown open | Closes dropdown and restores previous value |
| `Backspace` | Multi-mode, empty query | Removes the last chip badge |
| `Tab` | Any | Closes dropdown and moves focus to next focusable element |

---

## 4. Typography & Theme Token Integration

Never use arbitrary Tailwind classes like `text-xs`, `text-sm`, `font-bold`, `leading-5`, `text-gray-500` inside reusable components.

Always map to project-level design tokens:

```tsx
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

// Label:
<label className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>
  {label}
</label>

// Body text:
<span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
  {item.name}
</span>

// Micro captions / subtexts:
<span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
  {item.description}
</span>
```
