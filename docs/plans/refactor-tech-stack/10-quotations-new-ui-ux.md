# 10. Quotation Form UI/UX Redesign (`/quotations/new`)

Contextual media selection and upload use [11-r2-media-file-contract.md](./11-r2-media-file-contract.md).

## 1. Overview & Objectives
The current New Quotation form (`FactsForm.tsx`) functions as a monolithic, vertically stacked sequence of `<details>` blocks. While functional, it lacks a modern SaaS aesthetic, can feel overwhelming to users, and suffers from rendering bottlenecks on very large itineraries.

**Objectives:**
- Transform the page into a visually stunning, premium workspace.
- Improve user guidance through structured navigation and progressive disclosure.
- Optimize rendering performance by strictly adhering to Vercel React Best Practices.

## 2. Structural Layout
We will migrate from a single-column scrolling page to a **Two-Column Workspace Architecture**:

- **Left Column (70% width) - Form Workspace**: 
  - Houses the active form sections. 
  - Sections are rendered as elevated cards (`shadow-[var(--elevation-card)]`) rather than native `<details>` blocks.
- **Right Column (30% width) - Sticky Navigator / Summary Widget**: 
  - A sticky, glassmorphic card (`backdrop-blur-md`, semi-transparent background) that remains in the viewport.
  - Acts as a "Table of Contents" (ScrollSpy) or a Wizard Stepper.
  - Displays real-time progress indicators (e.g., "Programme: 3 Days Complete", "Travellers: Needs Info").
  - Clicking an item smoothly scrolls the Left Column to the respective section.

## 3. UI Aesthetics & Micro-interactions
- **Glassmorphism**: Utilize background blur for sticky elements (headers, navigator, overlays) to create a spatial, layered feel.
- **Form Controls**: 
  - Inputs should have subtle idle states and strong, animated focus rings (`ring-2 ring-[var(--color-accent)] transition-all duration-200`).
  - Use semantic design tokens: `var(--radius-button)` and `var(--radius-card)`.
- **Animations (Framer Motion / CSS)**:
  - Adding a new "Day" or "Hotel" should trigger a smooth slide-down and fade-in animation, avoiding jarring layout shifts.
  - Ghost/Skeleton states should pulse smoothly while assets load.

## 4. Complex Component UX Refinements

### A. The "Daily Programme" (Itinerary Builder)
- Instead of rendering an infinitely long list of open days, apply a controlled accordion or a focused edit mode:
  - **Collapsed View**: Days show only Day Number, Destination, and a Thumbnail.
  - **Expanded View**: Only 1 or 2 days should be open at once by default to prevent visual overload.
- **Empty States**: Use "Ghost" inputs or dotted borders when a new day is added to indicate where content should flow.

### B. Media Picker Integration
- **Current Issue**: The `MediaPicker` renders inline inside the day/hotel card, disrupting the vertical flow of the form and forcing the user to scroll heavily.
- **Proposed Solution**: 
  - Introduce a **Slide-over Drawer (Right Panel)** or a large **Modal** for the Media Picker.
- This keeps the form clean, provides a much larger, immersive grid for browsing the R2 media library, and allows the user to maintain visual context of the form in the background.
  - The drawer offers a refresh run for the indexed R2 library, search/load-more, and clear loading/error/empty states. A new quote holds selections only as presentation staging data; creation maps those `r2Key` values into the canonical document.

## 5. Performance & React Best Practices (Vercel Guidelines)

To ensure the UI remains snappy even with 30+ day itineraries, the following optimizations must be implemented:

1. **`bundle-dynamic-imports`**:
   - The `MediaPicker` (and its R2 fetching logic) must be dynamically imported (`next/dynamic`). 
   - A polished Skeleton loader must be shown during the chunk load to prevent layout shift.

2. **`rerender-memo` & `rerender-functional-setstate`**:
   - The monolithic `FactsForm` passes a single `update` function to every `DayEditor` and `HotelEditor`.
   - We must wrap `DayEditor` and `HotelEditor` in `React.memo` using custom comparison functions if necessary.
   - Callbacks passed to these child components (e.g., `onChange`, `onRemove`) must be stable (using `useCallback` or functional state updates) so that typing into Day 1 does not trigger a re-render of Day 2 through Day 30.

3. **`rendering-content-visibility`**:
   - Apply CSS `content-visibility: auto; contain-intrinsic-size: 500px;` to the outer wrappers of `DayEditor` and `HotelEditor`.
   - This allows the browser to skip styling and layout calculations for off-screen days, dramatically improving scroll performance and Time to Interactive.

## 6. Implementation Strategy

1. **Scaffold the Layout**: Update `NewQuotationClient.tsx` to implement the CSS Grid two-column layout and the sticky navigator component.
2. **Modularize the Form**: Break `FactsForm.tsx` down into smaller, focused components: `<TripSection />`, `<TravellersSection />`, `<ProgrammeSection />`, etc.
3. **Build the Slide-over**: Implement a reusable `<SlideOver />` or `<Modal />` component and wire it to the dynamically imported `MediaPicker`.
4. **Apply Optimizations**: Implement `React.memo`, stable callbacks, and `content-visibility` strictly on the repeatable sections (Days, Hotels).
5. **Wire the State**: Ensure the top-level `QuotationFacts` state continues to act as the single source of truth, passing only necessary slices to child components.
