# Parity Checklist

Review in this order:

1. App chrome
2. Section order
3. Section composition and DOM order
4. Shell, borders, ornaments, and surface language
5. Brand palette and theme color recipe
6. Typography hierarchy
7. Interaction parity
8. Responsive behavior
9. PDF behavior
10. Source contract ownership:
    - typography: config -> semantic class -> theme slot -> component consumer
    - color: brand palette -> theme recipe -> resolved scope -> component role

Findings should name the drift, its impact, and the current file that owns the mismatch.
The review is not complete until the deterministic display, typography, and color audits have run.
