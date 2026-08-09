# Quote Generator Display System

`quote-generator` hiện là một Next.js brochure display system cho public quotation/landing experiences. Hệ mới chuẩn hóa:

- `theme`
- `view mode`
- `layout system`
- `component system`
- `section view model`

## Getting Started

Chạy local:

```bash
npm run dev
```

Mặc định app chạy ở [http://localhost:8115](http://localhost:8115).

Preview modes:

- `/`
- `/?view=desktop`
- `/?view=mobile`
- `/?view=pdf`
- `/pdf`

## Contracts

- [docs/display-system-contract.md](./docs/display-system-contract.md)
- [docs/typography-contract.md](./docs/typography-contract.md)

## Quality gates

```bash
npm run lint
npm run build
```

`npm run build` hiện dùng `next build --webpack` vì Turbopack panic trong sandbox hiện tại khi parse global CSS. Đây là giới hạn engine ở môi trường này, không phải lỗi của app code.

## Learn More

- `display/pageBuilder.ts` map raw brand content sang `PageViewModel`
- `display/themes/brochureTheme.ts` giữ orchestration của brochure theme
- `config/typography.ts` là SSoT cho semantic typography
- `components/display/` chứa atoms, molecules, và public section renderers

## Notes

- Font assets đã được localize trong `public/fonts` để production build không phụ thuộc fetch Google Fonts.
- Public display layer bị chặn dùng `useBrand()`, `BRANDS_DATA`, `no-print`, và `no-screen` bằng lint script riêng.
