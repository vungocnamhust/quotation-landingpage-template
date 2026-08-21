# 13. Systemic Color Architecture & Brand Theming Guide

> **Mục đích**: Tài liệu quy chuẩn kỹ thuật hướng dẫn cách thay đổi, mở rộng và bảo trì hệ thống màu sắc đa thương hiệu (Multi-brand Theming) xuyên suốt từ Database (PostgreSQL), Backend (FastAPI) đến Frontend (Next.js App Router / PDF / Mobile / Desktop).

---

## 🏛️ 1. Bản Đồ Kiến Trúc Màu Sắc (Color Ownership Chain)

Hệ thống màu sắc tuân thủ nghiêm ngặt chuỗi sở hữu 5 tầng khép kín:

$$\text{PostgreSQL Database (SSoT)} \longrightarrow \text{Theme Color Recipe (Scopes)} \longrightarrow \text{ThemeTokens Resolver} \longrightarrow \text{CSS Variables} \longrightarrow \text{React Component UI}$$

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Database SSoT (PostgreSQL `brands.render_profile`)                   │
│    Chứa giá trị màu gốc (#RRGGBB) của từng brand: canvas, ink, accent...│
├─────────────────────────────────────────────────────────────────────────┤
│ 2. Theme Color Recipe (`display/themes/brochureTheme.ts`)               │
│    Định nghĩa vai trò ngữ nghĩa (Scopes) và tinh chỉnh viewMode (PDF)   │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. ThemeTokens Resolver (`config/themeTokens.ts` & `runtimeThemeTokens`) │
│    Resolve Scope + Palette thành biến CSS `--color-*`, kiểm tra WCAG AA │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. CSS Render Layer (`app/globals.css`)                                 │
│    Chỉ đọc biến `var(--color-*)`, TUYỆT ĐỐI KHÔNG chứa mã màu hex/rgb   │
├─────────────────────────────────────────────────────────────────────────┤
│ 5. React Display Components (`components/display/sections/*`)           │
│    Nhận `colorScope` và render thuần túy qua token CSS                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 2. Ba Quy Tắc Bất Biến (Hard Guardrails)

1. **Không Hardcode**: Không bao giờ viết mã màu cứng (`#ffffff`, `rgb(...)`, `bg-slate-900`) trong JSX hoặc CSS. Mọi màu sắc hiển thị (kể cả trên PDF) đều phải bắt nguồn từ `BrandColorPalette` và `ThemeTokens`.
2. **Tuân thủ Chuỗi SSoT**: Dữ liệu màu sắc khi ứng dụng chạy thật (production/staging) bắt nguồn từ **Database PostgreSQL** (`brands.render_profile`). File `brandsData.ts` ở frontend chỉ là fixture dự phòng cho mock preview/Storybook.
3. **Độ Tương Phản WCAG 2.1 AA**: Mọi cặp màu chữ/nền (`ink` trên `canvas`, `onContrast` trên `contrast`, `investmentText` trên `investmentSurface`) bắt buộc phải đạt tỉ lệ tương phản tối thiểu **$\ge$ 4.5:1** (và focus ring $\ge$ 3.0:1). Sẽ bị chặn ngay lập tức bởi `npm run lint:colors`.

---

## 🛠️ 3. Quy Trình Thay Đổi Màu Sắc Theo 3 Cấp Độ

---

### 🎨 CẤP ĐỘ 1: Đổi Màu Nhận Diện Thương Hiệu của một Brand (Brand Palette SSoT)
> **Khi nào áp dụng?** Khi thay đổi màu chủ đạo (`accent`), màu nền đặc trưng (`investmentSurface`), màu tương phản (`contrast`) của một thương hiệu, hoặc thêm một thương hiệu mới vào hệ thống.

#### Bước 1: Tạo Alembic Migration để cập nhật PostgreSQL Database
Tạo một migration mới trong `alembic/versions/` (ví dụ: `YYYYMMDD_XX_update_brand_palette.py`):

```python
from alembic import op
import sqlalchemy as sa

revision = "YYYYMMDD_XX"
down_revision = "PREVIOUS_REVISION"

BRANDS = sa.table("brands", sa.column("id", sa.String), sa.column("render_profile", sa.JSON))
PUBLICATION_RELEASES = sa.table("publication_releases", sa.column("id", sa.String), sa.column("render_profile_snapshot", sa.JSON))

def _update_profiles(palette_updates: dict[str, dict[str, str | None]]) -> None:
    bind = op.get_bind()
    # 1. Update bảng brands
    rows = bind.execute(sa.select(BRANDS.c.id, BRANDS.c.render_profile).where(BRANDS.c.id.in_(tuple(palette_updates)))).mappings()
    for row in rows:
        profile = dict(row["render_profile"] or {})
        palette = dict(profile.get("palette") or {})
        palette.update(palette_updates[row["id"]])
        profile["palette"] = palette
        bind.execute(sa.update(BRANDS).where(BRANDS.c.id == row["id"]).values(render_profile=profile))

    # 2. Update snapshot trong publication_releases (nếu cần sync quote đã xuất bản)
    release_rows = bind.execute(sa.select(PUBLICATION_RELEASES.c.id, PUBLICATION_RELEASES.c.render_profile_snapshot)).mappings()
    for r_row in release_rows:
        r_profile = dict(r_row["render_profile_snapshot"] or {})
        brand_id = r_profile.get("id")
        if brand_id in palette_updates:
            r_palette = dict(r_profile.get("palette") or {})
            r_palette.update(palette_updates[brand_id])
            r_profile["palette"] = r_palette
            bind.execute(sa.update(PUBLICATION_RELEASES).where(PUBLICATION_RELEASES.c.id == r_row["id"]).values(render_profile_snapshot=r_profile))

def upgrade() -> None:
    _update_profiles({
        "selvara": {
            "accent": "#7a591a",
            "contrast": "#524018",
            "investmentSurface": "#f6f2ea",
            "investmentText": "#11130f",
        },
    })
```

Thực thi migration vào database:
```bash
docker exec quotation-local-app-1 alembic upgrade head
```

#### Bước 2: Đồng bộ File Mock Fixture ở Frontend
Cập nhật file [`quote-generator/data/brandsData.ts`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/data/brandsData.ts):
```typescript
// Trong brand tương ứng (ví dụ: selvara)
themeTokens: createThemeTokens({
  palette: {
    canvas: '#f9f6f0',
    paper: '#f9f6f0',
    ink: '#11130f',
    mutedInk: '#2c2a29',
    accent: '#7a591a',
    contrast: '#524018',
    storyContrast: '#524018',
    investmentSurface: '#f6f2ea',
    investmentText: '#11130f',
    // ...
  },
}),
```

---

### 🎭 CẤP ĐỘ 2: Đổi Cách Phối Màu của Section hoặc ViewMode (Theme Color Recipe)
> **Khi nào áp dụng?** Khi muốn thay đổi vai trò màu của một Section (ví dụ: chuyển Section `Hotels` sang nền tối `storyContrast`), hoặc tinh chỉnh màu sắc riêng cho chế độ in ấn PDF / Mobile.

Bạn **chỉ cần sửa duy nhất 1 file cấu hình**: [`quote-generator/display/themes/brochureTheme.ts`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/display/themes/brochureTheme.ts):

#### 1. Định nghĩa Scope trong `colorRecipe.scopes`
Map các vai trò ngữ nghĩa của UI (`surface`, `onSurface`, `border`, `action`, `timeline`) sang tên key của Palette:
```typescript
const colorRecipe: ThemeColorRecipe = {
  scopes: {
    pricing: {
      surface: 'investmentSurface',      // Màu nền section
      onSurface: 'investmentText',         // Màu chữ chính
      muted: 'investmentText',             // Màu chữ phụ/chú thích
      accent: 'accentAlt',
      accentAlt: 'accentAlt',
      border: { color: 'investmentText', opacity: 0.2 },
      strongBorder: { color: 'investmentText', opacity: 0.38 },
      action: {
        primary: { surface: 'investmentSurface', text: 'investmentText', border: { color: 'investmentText', opacity: 0.8 } },
        secondary: { surface: 'transparent', text: 'investmentText', border: { color: 'investmentText', opacity: 0.34 } },
      },
      timeline: { route: 'accentAlt', marker: 'investmentText', active: 'accentAlt' },
      shadow: { color: 'ink', opacity: 0.26 },
      ornamentOpacity: 0.14,
      
      // 👇 Điều chỉnh riêng cho PDF (In ấn tiết kiệm mực, độ tương phản cao)
      viewModeAdjustments: {
        pdf: {
          surface: 'paper',                // Đổi nền sang màu giấy sáng
          onSurface: 'ink',                // Đổi chữ sang mực đậm
          muted: 'mutedInk',
          border: { color: 'ink', opacity: 0.14 },
          strongBorder: { color: 'ink', opacity: 0.26 },
          shadow: { color: 'ink', opacity: 0 },
          ornamentOpacity: 0,
        },
      },
    },
  },
};
```

#### 2. Gán Scope cho Section trong `sectionConfigs`
```typescript
pricing: {
  desktop: config('pricing', {
    layoutVariant: 'pricing-investment-ledger',
    backgroundVariant: 'investment',
    // ...
  }),
  pdf: config('pricing', {
    layoutVariant: 'pricing-investment-ledger',
    backgroundVariant: 'paper',
    // Không cần override colorScope! Tự động thừa hưởng 'pricing' scope + viewModeAdjustments.pdf
  }),
}
```

---

### 🧱 CẤP ĐỘ 3: Thêm Token Màu Mới vào Toàn Hệ Thống (Mở Rộng System Schema)
> **Khi nào áp dụng?** Khi thiết kế đòi hỏi một loại token màu mới chưa từng có (ví dụ: `badgeSurface`, `highlightGlow`).

Thực hiện theo đúng **thứ tự phụ thuộc (Dependency Order)**:

```
[1. Types Contract] ──> [2. Backend Schema] ──> [3. ThemeTokens Resolver] ──> [4. CSS Classes] ──> [5. Database & Seed]
```

1. **TypeScript Contracts**: Khai báo tên token trong [`quote-generator/display/types.ts`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/display/types.ts):
   ```typescript
   export type ColorReference =
     | 'canvas' | 'paper' | 'ink' | 'accent'
     | 'myNewToken'; // 👈 Thêm vào ColorReference và BrandColorPalette
   ```
2. **Backend Contract Validation**: Khai báo trong [`schemas/brand_contract.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/schemas/brand_contract.py):
   ```python
   required = {"canvas", "paper", "ink", ..., "myNewToken"}
   ```
3. **Token Resolver Pipeline**: Đăng ký tạo CSS variable trong [`quote-generator/config/themeTokens.ts`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/config/themeTokens.ts) & `runtimeThemeTokens.ts`:
   ```typescript
   '--color-my-new-token': resolveReference(palette, resolved.myNewToken),
   ```
4. **CSS Render Layer**: Áp dụng biến CSS trong [`quote-generator/app/globals.css`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/app/globals.css):
   ```css
   .display-badge--custom {
     background: var(--color-my-new-token);
   }
   ```
5. **Cấp Giá Trị Màu**: Tạo migration Alembic và cập nhật `brandsData.ts` với mã màu `#RRGGBB` cho tất cả các thương hiệu.

---

## 🧪 4. Bộ Lệnh Tự Kiểm Tra (Self-Verification Gates)

Sau bất kỳ thay đổi nào liên quan đến màu sắc, AI và Kỹ sư **BẮT BUỘC** chạy chuỗi kiểm tra sau:

```bash
cd quote-generator

# 1. Rà soát vi phạm Hardcode Hex/RGBA & Kiểm tra tương phản WCAG 2.1 AA (fail nếu ratio < 4.5:1)
npm run lint:colors

# 2. Kiểm tra tính toàn vẹn của Color Scope Resolver cho mọi Brand & ViewMode (Desktop, Mobile, PDF)
node --test lib/__tests__/colorContracts.test.ts

# 3. Kiểm tra Typography SSOT, Display Boundaries & Next.js Production Build
npm run lint
npm run build

# 4. Kiểm tra Backend Domain Rules & Contracts
cd ..
PYTHONPATH=. pytest tests/test_domain_rules.py tests/test_business_gates.py
```
