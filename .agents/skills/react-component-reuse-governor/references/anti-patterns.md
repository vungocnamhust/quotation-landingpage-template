# Component Reusability Anti-Patterns & Refactoring Guide

This document highlights common anti-patterns that undermine component reusability and maintainability, along with recommended refactorings.

---

## 1. Dual-Callback Synchronization Anti-Pattern

### ❌ Problematic Code
```tsx
// Forcing caller to pass two separate callbacks that need manual synchronization
<DestinationInput
  value={day.destination}
  onChange={(val) => patchDay(index, { destination: val, destination_ref: null })}
  onSelect={(ref) => patchDay(index, { destination: ref?.name ?? null, destination_ref: ref })}
/>
```

### ✅ Solution: Unified Callback Contract
```tsx
// Unified onChange handler provides both primitive name and rich reference
<DestinationSelect
  value={day.destination}
  onChange={(name, ref) =>
    patchDay(index, {
      destination: name,
      destination_ref: ref ?? null,
    })
  }
/>
```

---

## 2. Inline Pill Buttons vs Floating Popover

### ❌ Problematic Code
Rendering search results directly in the DOM flow underneath the input:
```tsx
// Layout shifts and breaks vertical table grids!
<input ... />
{results.map(item => (
  <button key={item.id} onClick={() => select(item)}>{item.name}</button>
))}
```

### ✅ Solution: Absolute Positioned Popover with Backdrop
```tsx
// Renders inside an absolute floating menu (z-50) with backdrop click-outside detection
<div className="relative">
  <input ... />
  {isOpen && (
    <div
      role="listbox"
      className="absolute left-0 top-[calc(100%+0.25rem)] z-50 min-w-full overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-surface)] shadow-xl"
    >
      {results.map(item => (
        <button role="option" onClick={() => handleSelect(item)}>{item.name}</button>
      ))}
    </div>
  )}
</div>
```

---

## 3. Hardcoded Static Data in Selects

### ❌ Problematic Code
```tsx
// Hardcoded static array inside form
const DESTINATIONS = ["Vietnam", "Cambodia", "Laos", "Thailand"];

<CustomSelect
  options={DESTINATIONS.map(d => ({ id: d, label: d }))}
  value={state.destination}
  onChange={(val) => onChange(prev => ({ ...prev, destination: val }))}
/>
```

### ✅ Solution: Dynamic Catalog-backed Component with Fallback
```tsx
// Queries catalog dynamically while showing popular presets when query is empty
<DestinationSelect
  value={state.destination}
  onChange={(val) => onChange(prev => ({ ...prev, destination: val ?? "" }))}
/>
```

---

## 4. Unstyled Primitive Inputs in Sub-Grids

### ❌ Problematic Code
```tsx
// Raw text input without autocomplete or catalog validation
<input
  type="text"
  placeholder="e.g. Hanoi"
  value={day.destination}
  onChange={(e) => handleFieldChange(idx, "destination", e.target.value)}
/>
```

### ✅ Solution: Compact Component Variant
```tsx
// Uses compact size variant to fit table cell perfectly while retaining search capabilities
<DestinationSelect
  size="sm"
  variant="compact"
  placeholder="e.g. Hanoi"
  value={day.destination}
  onChange={(val) => handleFieldChange(idx, "destination", val ?? "")}
/>
```
