# Typography Contract

Typography trong `quote-generator` đi qua một nguồn sự thật duy nhất:

- `config/typography.ts` là nơi khai báo font role, semantic variant, brand override, và print rules.
- Font loading has one declared owner: `app/fonts.ts` using `next/font`. `app/layout.tsx` attaches its variables and `config/typography.ts` consumes them; `globals.css` is not a second font catalog.
- `app/layout.tsx` inject stylesheet sinh ra từ config này.
- `app/` và `components/` chỉ consume qua semantic class `typo-*`.
- Typography-bearing molecules consume `TypographySlotMap` or an explicit `TypographyVariant`; they must not invent fixed variants internally.

## Semantic variants

- `typo-hero`
- `typo-section-title`
- `typo-card-title`
- `typo-body-lg`
- `typo-body-md`
- `typo-body-sm`
- `typo-caption`
- `typo-overline`
- `typo-label`
- `typo-price`
- `typo-quote`
- `typo-button-primary`
- `typo-button-secondary`
- `typo-topbar-select-value`
- `typo-topbar-action-value`
- `typo-topbar-brand-name`
- `typo-topbar-section-link`
- `typo-nav-title`
- `typo-nav-meta`
- `typo-page-title`
- `typo-chapter-kicker`
- `typo-chapter-title`
- `typo-hero-lede`
- `typo-hero-meta-primary`
- `typo-hero-meta-secondary`
- `typo-letter-title`
- `typo-letter-highlight`
- `typo-letter-body`
- `typo-signature-name`
- `typo-signature-meta`
- `typo-route-map-title`
- `typo-route-map-body`
- `typo-timeline-title`
- `typo-timeline-meta`
- `typo-day-title`
- `typo-day-body`
- `typo-hotel-title`
- `typo-hotel-meta`
- `typo-hotel-body`
- `typo-investment-title`
- `typo-investment-value`
- `typo-investment-meta`
- `typo-term-title`
- `typo-term-body`
- `typo-designer-title`
- `typo-designer-quote`
- `typo-footer-text`
- `typo-state-title`

## Rules

- Không thêm `text-xs`, `text-sm`, `text-xl`, `font-bold`, `leading-*`, `tracking-*`, `uppercase`, `italic`, `font-heading`, `font-body`, `font-accent` vào `app/` hoặc `components/`.
- Nếu cần một style mới, thêm variant mới trong `config/typography.ts` trước rồi mới dùng trong JSX.
- `brand-btn-primary` và `brand-badge` chỉ giữ phần chrome của component; typography phải đến từ `typo-*`.
- `BrandSpecModal` được phép đọc config typography để hiển thị spec/debug, nhưng không tự định nghĩa token riêng.
- `theme + viewMode` có thể override cùng một semantic variant, nhưng không được tạo SSoT typography thứ hai trong section JSX hoặc CSS riêng.
- `globals.css` không được chứa `@font-face`, `--font-*` role aliases, `font:`, hoặc content typography declarations.
- Map markers, PDF indices, investment badges, and links must receive their typography through the section's `TypographySlotMap` (`index`, `badge`, `link`, or `action`).

## Quick examples

Đúng:

```tsx
<h2 className="typo-section-title text-[var(--text-primary)]">Bộ sưu tập hành trình</h2>
<p className="typo-body-sm text-[var(--text-muted)]">Mô tả ngắn.</p>
<button className="brand-btn-primary typo-button-primary px-5 py-2.5">Yêu cầu báo giá</button>
```

Sai:

```tsx
<h2 className="text-3xl font-bold font-heading">Bộ sưu tập hành trình</h2>
<p className="text-sm font-body leading-relaxed">Mô tả ngắn.</p>
<button className="brand-btn-primary text-xs uppercase tracking-wide">Yêu cầu báo giá</button>
```
