# Display System Contract

`quote-generator` hiện render public UI qua 5 lớp cố định:

1. `theme`
2. `view mode`
3. `layout system`
4. `component system`
5. `section view model`

## Sources of truth

- `display/themes/brochureTheme.ts` là orchestration contract của brochure theme.
- `display/pageBuilder.ts` là nơi map raw brand content sang `PageViewModel`.
- `config/typography.ts` là nguồn duy nhất cho typography variants, kể cả `desktop`, `mobile`, và `pdf`.
- `data/brandsData.ts` chỉ sở hữu `BrandColorPalette` opaque `#RRGGBB`; alpha, scrim, border và shadow thuộc `ThemeColorRecipe`.
- `config/themeTokens.ts` resolve `brand + theme + view mode` thành color scopes trước server render. CSS chỉ đọc `--color-*`; không thêm fallback palette trong CSS.
- `app/globals.css` chỉ làm render layer cho shell/surface/display classes. Font loading, font roles, aliases, and text metrics belong to the typography owner; do not add `@font-face` or raw `--font-*` aliases here.

## Public render contract

- Public sections không đọc `useBrand()` trực tiếp.
- Public sections không import `BRANDS_DATA` trực tiếp.
- Public sections chỉ nhận `viewModel + displayConfig + tokens + theme + viewMode`; màu đến từ scope đã resolve bởi `DisplayPage`.
- `visibilityByViewMode` thay thế cho `no-print` và `no-screen`.

## Theme contract

Một theme phải khai báo:

- `id`
- `supportedViewModes`
- `pageShell`
- `sectionOrder`
- `sectionConfigs`
- `layoutVariants`
- `ornamentRegistry`
- `typographyMap`
- `colorRecipe`
- `pdfRules`

`display/validateTheme.ts` sẽ fail sớm nếu theme thiếu section config, thiếu `desktop/mobile/pdf`, hoặc reference layout/shell không tồn tại.

## View mode contract

- `desktop`: giữ editorial asymmetry của brochure prototype.
- `mobile`: collapse layout về reading order ưu tiên top-down.
- `pdf`: dùng cùng section contracts nhưng render dưới `pdf-page` shell classes và typography overrides của `pdf`.

Các entry point hiện có:

- `/`: auto theo viewport hoặc `?view=desktop|mobile|pdf`
- `/pdf`: force `pdf` view mode

## Guardrails

- `npm run lint:typography` chặn typography utility ad-hoc.
- `npm run lint:display-system` chặn `useBrand()`, `BRANDS_DATA`, `no-print`, `no-screen` quay lại display layer.
- `npm run lint:colors` chặn HEX/RGBA, CSS variable legacy và color prop trực tiếp ngoài resolver/palette owner.
- Color resolver fail khi thiếu scope hoặc cặp text/action/focus không đạt contrast contract.

## Khi thêm section/layout/theme mới

1. Khai báo type trước trong `display/types.ts`.
2. Thêm layout hoặc shell vào registry nếu cần.
3. Thêm section config cho đủ `desktop/mobile/pdf`.
4. Thêm typography slot mapping.
5. Chọn `colorScope` và `colorSlots`; không truyền hex vào component.
6. Map data vào `PageViewModel` trong builder layer.
7. Chỉ sau đó mới render section JSX.
