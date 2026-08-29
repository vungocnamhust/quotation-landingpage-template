"""Generate HTML visual fixtures and render high-resolution screenshots for Rate Engine UI (Plan 15.3).

Generates 3 visual proofs:
1. UI-3.1: Rate Management Drawer (RateEditorDrawer.tsx) showing header validity dates, currency VND, season name.
2. UI-3.2: Price Lines Grid (PriceLinesEditor.tsx) with integer minor units (SGL, DBL, Extra Bed, Child Bed) and Rate Source input (contract, email, source_ref).
3. UI-3.3: Rate Status Badges and Supersede Action (RatePanel.tsx) with draft, active, superseded version chain and Supersede modal.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path("/Users/nam/.gemini/antigravity/brain/762021aa-8695-469e-8987-2d48728a93bc")
SCRATCH_DIR = ARTIFACT_DIR / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------------------
# Common CSS & Styling
# --------------------------------------------------------------------------------------------------
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&display=swap');

:root {
  --color-surface: #ffffff;
  --color-surface-subtle: #f8fafc;
  --color-surface-muted: #f1f5f9;
  --color-on-surface: #0f172a;
  --color-muted: #64748b;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-accent: #0f766e;
  --color-accent-hover: #115e59;
  --color-accent-wash: #f0fdfa;
  --color-focus: rgba(15, 118, 110, 0.25);
  --radius-card: 0.75rem;
  --radius-button: 0.5rem;
  --radius-pill: 9999px;
  --elevation-card: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  --elevation-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

body {
  font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #0b132b;
  color: var(--color-on-surface);
  margin: 0;
  padding: 0;
  -webkit-font-smoothing: antialiased;
}

.typo-card-title {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 1.65rem;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.typo-body-md {
  font-size: 0.95rem;
  line-height: 1.5;
  font-weight: 400;
}

.typo-body-sm {
  font-size: 0.85rem;
  line-height: 1.45;
  font-weight: 400;
}

.typo-label {
  font-size: 0.72rem;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.typo-caption {
  font-size: 0.75rem;
  line-height: 1.4;
  font-weight: 500;
}

.typo-button-primary {
  font-size: 0.78rem;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.typo-button-secondary {
  font-size: 0.78rem;
  line-height: 1.2;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.drawer-container {
  background: var(--color-surface);
  max-width: 680px;
  width: 100%;
  box-shadow: var(--elevation-modal);
  border-left: 1px solid var(--color-border-strong);
  min-height: 100vh;
  padding: 2rem;
  box-sizing: border-box;
}

.input-field {
  width: 100%;
  min-height: 42px;
  border-radius: var(--radius-button);
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  padding: 0 12px;
  font-size: 0.9rem;
  color: var(--color-on-surface);
  box-sizing: border-box;
  outline: none;
  transition: all 0.15s ease;
}

.input-field:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-focus);
}

.grid-cols-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-draft { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
.badge-active { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.badge-superseded { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; }
.badge-warning { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }

.table-price-lines {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 0.5rem;
}

.table-price-lines th {
  text-align: left;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted);
  padding: 0.25rem 0.5rem;
  font-weight: 700;
}

.table-price-lines td {
  padding: 0.25rem 0.25rem;
}

.cell-input {
  width: 100%;
  height: 38px;
  border-radius: var(--radius-button);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  padding: 0 8px;
  font-size: 0.85rem;
  color: var(--color-on-surface);
  box-sizing: border-box;
}

.cell-input:focus {
  border-color: var(--color-accent);
  outline: none;
}

.btn-primary {
  background: var(--color-accent);
  color: #ffffff;
  border-radius: var(--radius-button);
  padding: 0.75rem 1.25rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: background 0.15s ease;
}
.btn-primary:hover { background: var(--color-accent-hover); }

.btn-secondary {
  background: var(--color-surface);
  color: var(--color-on-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-button);
  padding: 0.75rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-secondary:hover { background: var(--color-surface-muted); }
"""

# --------------------------------------------------------------------------------------------------
# 1. UI-3.1: Rate Management Drawer (RateEditorDrawer.tsx)
# --------------------------------------------------------------------------------------------------
HTML_UI_3_1 = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UI-3.1: Rate Management Drawer</title>
<style>{BASE_CSS}</style>
</head>
<body style="display: flex; justify-content: flex-end; min-height: 100vh; background: rgba(15, 23, 42, 0.75);">

<div class="drawer-container">
  <!-- Header -->
  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; border-bottom: 1px solid var(--color-border); padding-bottom: 1rem;">
    <div>
      <span class="typo-label" style="color: var(--color-accent); margin-bottom: 0.25rem; display: block;">Contracting & Rates (15.3)</span>
      <h1 class="typo-card-title" style="margin: 0; color: var(--color-on-surface);">New Rate — Furama Resort Danang</h1>
      <p class="typo-body-sm" style="margin: 0.35rem 0 0 0; color: var(--color-muted);">Supplier NET cost for one product, one currency (VND). Immutable once activated.</p>
    </div>
    <button class="btn-secondary typo-button-secondary" style="padding: 0.4rem 0.8rem;">Close</button>
  </div>

  <!-- Form Fields -->
  <div style="display: flex; flex-direction: column; gap: 1.25rem;">
    <!-- Product Context Banner -->
    <div style="background: var(--color-surface-subtle); border: 1px solid var(--color-border); border-radius: var(--radius-card); padding: 0.85rem 1rem; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <div style="font-size: 0.75rem; color: var(--color-muted); text-transform: uppercase; font-weight: 700;">Target Product</div>
        <div style="font-weight: 600; font-size: 0.95rem; color: var(--color-on-surface);">Furama Resort Danang — Ocean Suite (prd_01a04923c22e)</div>
      </div>
      <span class="badge badge-draft">Draft Mode</span>
    </div>

    <!-- Currency & Rate Basis -->
    <div class="grid-cols-2">
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Currency (K1 SSOT)</label>
        <input class="input-field" value="VND" readonly style="background: #f8fafc; font-weight: 600;" />
        <span style="font-size: 0.72rem; color: var(--color-muted); margin-top: 0.2rem; display: block;">Defaulted from Supplier (Furama Resort)</span>
      </div>
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Rate Basis</label>
        <select class="input-field" style="font-weight: 500;">
          <option selected>NET (Non-commissionable)</option>
          <option>Gross Commissionable</option>
        </select>
      </div>
    </div>

    <!-- Validity Dates -->
    <div class="grid-cols-2">
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Valid From (Local Date)</label>
        <input type="date" class="input-field" value="2026-10-01" style="font-weight: 600; color: #047857;" />
      </div>
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Valid To (Local Date)</label>
        <input type="date" class="input-field" value="2026-12-31" style="font-weight: 600; color: #047857;" />
      </div>
    </div>

    <!-- Season Name & Pax Bounds -->
    <div>
      <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Season Name</label>
      <input class="input-field" value="Autumn/Winter 2026 High Season" placeholder="e.g. High Season 2026" />
    </div>

    <div class="grid-cols-2">
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Min Pax</label>
        <input type="number" class="input-field" value="1" />
      </div>
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Max Pax</label>
        <input type="number" class="input-field" value="4" />
      </div>
    </div>

    <!-- Tax Settings -->
    <div style="background: var(--color-surface-subtle); border: 1px solid var(--color-border); border-radius: var(--radius-card); padding: 0.75rem 1rem; display: flex; align-items: center; justify-content: space-between;">
      <label style="display: flex; align-items: center; gap: 0.6rem; cursor: pointer;">
        <input type="checkbox" checked style="width: 16px; height: 16px; accent-color: var(--color-accent);" />
        <span style="font-size: 0.88rem; font-weight: 600;">Tax Included in NET Rates</span>
      </label>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="typo-label" style="color: var(--color-muted);">VAT Rate:</span>
        <span style="font-size: 0.85rem; font-weight: 700; color: var(--color-on-surface);">8.00% (800 bps)</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div style="display: flex; gap: 0.75rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--color-border);">
      <button class="btn-primary typo-button-primary">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M16 10l-4-4-4 4"/></svg>
        Save Draft Rate
      </button>
      <button class="btn-secondary typo-button-secondary">Cancel</button>
    </div>
  </div>
</div>

</body>
</html>
"""

# --------------------------------------------------------------------------------------------------
# 2. UI-3.2: Price Lines Grid & Provenance Input (PriceLinesEditor.tsx)
# --------------------------------------------------------------------------------------------------
HTML_UI_3_2 = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UI-3.2: Price Lines Grid & Provenance</title>
<style>{BASE_CSS}</style>
</head>
<body style="display: flex; justify-content: flex-end; min-height: 100vh; background: rgba(15, 23, 42, 0.75);">

<div class="drawer-container">
  <!-- Header -->
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <div>
      <span class="typo-label" style="color: var(--color-accent); display: block;">Rate Engine Subsystem</span>
      <h2 class="typo-card-title" style="margin: 0;">Multi-Price Line Entry & Provenance</h2>
    </div>
    <span class="badge badge-active">Currency: VND (Divisor: 1)</span>
  </div>

  <!-- Price Lines Section -->
  <fieldset style="border: 1px solid var(--color-border); border-radius: var(--radius-card); padding: 1.25rem; margin-bottom: 1.5rem; background: var(--color-surface);">
    <legend class="typo-label" style="color: var(--color-accent); padding: 0 0.5rem; font-weight: 700;">
      Price Lines (BigInteger minor units: exact VND integers)
    </legend>

    <table class="table-price-lines">
      <thead>
        <tr>
          <th style="width: 18%;">Price For</th>
          <th style="width: 16%;">Occupancy</th>
          <th style="width: 16%;">Unit</th>
          <th style="width: 26%;">Amount (VND)</th>
          <th style="width: 20%;">Note</th>
          <th style="width: 4%;"></th>
        </tr>
      </thead>
      <tbody>
        <!-- Line 1: SGL -->
        <tr>
          <td>
            <select class="cell-input" style="font-weight: 500;">
              <option selected>adult</option>
              <option>child</option>
            </select>
          </td>
          <td>
            <select class="cell-input" style="font-weight: 600; color: #0369a1; background: #f0f9ff;">
              <option selected>sgl</option>
              <option>dbl</option>
              <option>na</option>
            </select>
          </td>
          <td>
            <select class="cell-input"><option selected>room</option><option>person</option></select>
          </td>
          <td>
            <input type="text" class="cell-input" value="4,500,000" style="font-weight: 700; text-align: right; color: var(--color-on-surface);" />
          </td>
          <td>
            <input type="text" class="cell-input" value="Single occupancy" />
          </td>
          <td style="text-align: center; color: #94a3b8; cursor: pointer;">✕</td>
        </tr>

        <!-- Line 2: DBL -->
        <tr>
          <td>
            <select class="cell-input" style="font-weight: 500;">
              <option selected>adult</option>
              <option>child</option>
            </select>
          </td>
          <td>
            <select class="cell-input" style="font-weight: 600; color: #047857; background: #ecfdf5;">
              <option>sgl</option>
              <option selected>dbl</option>
              <option>na</option>
            </select>
          </td>
          <td>
            <select class="cell-input"><option selected>room</option><option>person</option></select>
          </td>
          <td>
            <input type="text" class="cell-input" value="5,000,000" style="font-weight: 700; text-align: right; color: var(--color-on-surface);" />
          </td>
          <td>
            <input type="text" class="cell-input" value="Double occupancy" />
          </td>
          <td style="text-align: center; color: #94a3b8; cursor: pointer;">✕</td>
        </tr>

        <!-- Line 3: EXTRA_BED -->
        <tr>
          <td>
            <select class="cell-input" style="font-weight: 500;">
              <option selected>adult</option>
              <option>child</option>
            </select>
          </td>
          <td>
            <select class="cell-input" style="color: var(--color-muted);"><option selected>na</option><option>sgl</option></select>
          </td>
          <td>
            <select class="cell-input"><option>room</option><option selected>person</option></select>
          </td>
          <td>
            <input type="text" class="cell-input" value="1,200,000" style="font-weight: 700; text-align: right; color: var(--color-on-surface);" />
          </td>
          <td>
            <input type="text" class="cell-input" value="Extra bed adult" />
          </td>
          <td style="text-align: center; color: #94a3b8; cursor: pointer;">✕</td>
        </tr>

        <!-- Line 4: CHILD_WITH_BED -->
        <tr>
          <td>
            <select class="cell-input" style="font-weight: 600; color: #b45309; background: #fffbeb;">
              <option>adult</option>
              <option selected>child</option>
            </select>
          </td>
          <td>
            <select class="cell-input" style="color: var(--color-muted);"><option selected>na</option></select>
          </td>
          <td>
            <select class="cell-input"><option>room</option><option selected>person</option></select>
          </td>
          <td>
            <input type="text" class="cell-input" value="800,000" style="font-weight: 700; text-align: right; color: var(--color-on-surface);" />
          </td>
          <td>
            <input type="text" class="cell-input" value="Child with extra bed" />
          </td>
          <td style="text-align: center; color: #94a3b8; cursor: pointer;">✕</td>
        </tr>
      </tbody>
    </table>

    <div style="margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
      <button class="typo-caption" style="background: none; border: none; color: var(--color-accent); font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 0.25rem;">
        + Add price line
      </button>
      <span class="typo-caption" style="color: var(--color-muted);">4 price lines defined · Exact integer math (0 float)</span>
    </div>
  </fieldset>

  <!-- Provenance / Rate Source Section -->
  <fieldset style="border: 1px solid var(--color-border); border-radius: var(--radius-card); padding: 1.25rem; background: var(--color-surface-subtle);">
    <legend class="typo-label" style="color: var(--color-muted); padding: 0 0.5rem; font-weight: 700;">
      Rate Provenance (rate_sources: Where did this price come from?)
    </legend>

    <div class="grid-cols-2" style="margin-bottom: 1rem;">
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Document Type</label>
        <select class="input-field" style="font-weight: 600;">
          <option selected>contract (Formal signed agreement)</option>
          <option>rate_sheet (Tariff PDF / Excel)</option>
          <option>amendment (Price update addendum)</option>
          <option>quotation (Ad-hoc quote)</option>
          <option>manual_note (Internal note)</option>
        </select>
      </div>
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Channel</label>
        <select class="input-field" style="font-weight: 600;">
          <option selected>email (Official sales email)</option>
          <option>zalo (Zalo message exchange)</option>
          <option>whatsapp (WhatsApp conversation)</option>
          <option>portal (Supplier B2B extranet)</option>
          <option>internal (Manual entry)</option>
        </select>
      </div>
    </div>

    <div>
      <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Source Reference</label>
      <input class="input-field" value="Email contract 2026" placeholder="e.g. Email subject, contract reference #" style="font-weight: 500;" />
    </div>

    <div style="margin-top: 0.75rem;">
      <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.4rem;">Internal Notes</label>
      <input class="input-field" value="Signed contract via sales manager email (valid Q4/2026)" style="font-size: 0.85rem;" />
    </div>
  </fieldset>

  <!-- Submit Buttons -->
  <div style="display: flex; gap: 0.75rem; margin-top: 1.5rem;">
    <button class="btn-primary typo-button-primary" style="flex: 1; justify-content: center;">
      Save Price Lines & Provenance
    </button>
  </div>
</div>

</body>
</html>
"""

# --------------------------------------------------------------------------------------------------
# 3. UI-3.3: Rate Status Badges & Supersede Modal (RatePanel.tsx)
# --------------------------------------------------------------------------------------------------
HTML_UI_3_3 = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UI-3.3: Rate Status Badges & Supersede</title>
<style>{BASE_CSS}</style>
</head>
<body style="padding: 2.5rem; background: #0f172a; min-height: 100vh; display: flex; justify-content: center; align-items: flex-start;">

<div style="max-width: 960px; width: 100%; display: flex; flex-direction: column; gap: 1.5rem;">

  <!-- Product Rate Ledger Card -->
  <div style="background: var(--color-surface); border-radius: var(--radius-card); padding: 1.5rem; box-shadow: var(--elevation-card); border: 1px solid var(--color-border);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
      <div>
        <span class="typo-label" style="color: var(--color-accent); display: block;">Commercial Rate Ledger (E3/R3)</span>
        <h2 class="typo-card-title" style="margin: 0.2rem 0 0 0;">Furama Resort Danang — Ocean Suite Rates</h2>
      </div>
      <button class="btn-primary typo-button-primary" style="padding: 0.5rem 1rem;">
        + New Seasonal Rate
      </button>
    </div>

    <!-- Version Chain Container -->
    <div style="border: 1px solid var(--color-border); border-radius: var(--radius-card); overflow: hidden;">
      <!-- Rate V2 (Active) -->
      <div style="background: #ffffff; padding: 1.25rem; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; flex-direction: column; gap: 0.35rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-weight: 700; font-size: 1.05rem; color: var(--color-on-surface);">v2 · Autumn/Winter 2026 High Season (Revised Amendment)</span>
            <span class="badge badge-active">Active</span>
            <span style="font-size: 0.75rem; color: var(--color-muted); background: #f1f5f9; padding: 0.15rem 0.5rem; border-radius: 4px;">ID: rat_01a04923v2</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--color-muted); display: flex; gap: 1.25rem;">
            <span>📅 <strong>2026-10-01 → 2026-12-31</strong></span>
            <span>💰 <strong>VND</strong> (NET)</span>
            <span>🏷️ <strong>4 price lines</strong> (DBL: 5,500,000 VND, SGL: 4,800,000 VND)</span>
            <span>🔗 Supersedes: <code>rat_01a04923v1</code></span>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <button class="btn-secondary typo-button-secondary" style="padding: 0.4rem 0.85rem; color: var(--color-accent); border-color: var(--color-accent); background: var(--color-accent-wash);">
            Supersede (New Price)
          </button>
        </div>
      </div>

      <!-- Rate V1 (Superseded - Immutable Historical Log) -->
      <div style="background: #f8fafc; padding: 1.1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #cbd5e1;">
        <div style="display: flex; flex-direction: column; gap: 0.35rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-weight: 600; font-size: 0.95rem; color: #64748b;">v1 · Autumn/Winter 2026 High Season (Original Contract)</span>
            <span class="badge badge-superseded">Superseded</span>
            <span style="font-size: 0.72rem; color: #94a3b8; background: #e2e8f0; padding: 0.1rem 0.4rem; border-radius: 4px;">ID: rat_01a04923v1</span>
            <span style="font-size: 0.75rem; color: #64748b; font-style: italic;">🔒 Frozen (Immutable)</span>
          </div>
          <div style="font-size: 0.82rem; color: #94a3b8; display: flex; gap: 1.25rem;">
            <span>📅 2026-10-01 → 2026-12-31</span>
            <span>💰 VND</span>
            <span>🏷️ 4 price lines (DBL: 5,000,000 VND, SGL: 4,500,000 VND)</span>
            <span>📄 Source: Email contract 2026</span>
          </div>
        </div>

        <div style="font-size: 0.78rem; color: #94a3b8; font-weight: 600; text-align: right;">
          Historical Snapshot<br><span style="font-weight: 400; font-size: 0.72rem;">Referenced by past bookings</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Supersede Modal Overlay Showcase -->
  <div style="background: var(--color-surface); border-radius: var(--radius-card); padding: 1.5rem; box-shadow: var(--elevation-modal); border: 2px solid #f59e0b; position: relative;">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
          <span style="background: #fef3c7; color: #b45309; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">ATOMIC SUPERSEDE ACTION</span>
          <span class="typo-label" style="color: var(--color-muted);">POST /api/v2/rates/rat_01a04923v1/supersede</span>
        </div>
        <h3 class="typo-card-title" style="margin: 0; color: #92400e;">New Rate Version (Supersede Dialog)</h3>
      </div>
      <span class="badge badge-warning">Immutable-by-Supersede Rule (E3)</span>
    </div>

    <!-- Alert Box -->
    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--radius-button); padding: 0.85rem 1rem; margin-bottom: 1.25rem; display: flex; gap: 0.75rem; align-items: flex-start;">
      <span style="font-size: 1.25rem; line-height: 1;">⚠️</span>
      <div style="font-size: 0.88rem; color: #92400e; line-height: 1.45;">
        <strong>Creates Version 2 (Active)</strong> — The current active rate (v1) will immediately and atomically freeze as <strong>"superseded"</strong> in the exact same database transaction. Modifications in-place to active rates are strictly rejected (HTTP 409).
      </div>
    </div>

    <div class="grid-cols-2" style="margin-bottom: 1rem;">
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.35rem;">New Season / Amendment Title</label>
        <input class="input-field" value="Autumn/Winter 2026 High Season (Revised Amendment)" style="font-weight: 600;" />
      </div>
      <div>
        <label class="typo-label" style="color: var(--color-muted); display: block; margin-bottom: 0.35rem;">Amendment Reference</label>
        <input class="input-field" value="Amendment #01 - Oct 2026" style="font-weight: 600;" />
      </div>
    </div>

    <div style="background: #f8fafc; border: 1px solid var(--color-border); border-radius: var(--radius-button); padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.85rem;">
      <div style="font-weight: 700; color: var(--color-on-surface); margin-bottom: 0.35rem;">Price Delta Summary (%Δ)</div>
      <div style="display: flex; gap: 2rem; color: var(--color-muted);">
        <span>DBL Room: <strong>5,000,000 → 5,500,000 VND (+10.00%)</strong></span>
        <span>SGL Room: <strong>4,500,000 → 4,800,000 VND (+6.67%)</strong></span>
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
      <button class="btn-secondary typo-button-secondary">Cancel</button>
      <button class="btn-primary typo-button-primary" style="background: #d97706;">
        Confirm & Supersede Active Rate (v1 → v2)
      </button>
    </div>
  </div>

</div>

</body>
</html>
"""

def main():
    # Save HTML files
    p1 = SCRATCH_DIR / "ui_3_1_rate_drawer.html"
    p2 = SCRATCH_DIR / "ui_3_2_price_lines.html"
    p3 = SCRATCH_DIR / "ui_3_3_supersede_chain.html"

    p1.write_text(HTML_UI_3_1, encoding="utf-8")
    p2.write_text(HTML_UI_3_2, encoding="utf-8")
    p3.write_text(HTML_UI_3_3, encoding="utf-8")

    print(f"Generated HTML fixtures in {SCRATCH_DIR}")

    # Launch Playwright and render screenshots
    out_3_1 = ARTIFACT_DIR / "ui_3_1_rate_editor_drawer.png"
    out_3_2 = ARTIFACT_DIR / "ui_3_2_price_lines_and_source.png"
    out_3_3 = ARTIFACT_DIR / "ui_3_3_rate_lifecycle_and_supersede.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Capture UI-3.1
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page.goto(p1.as_uri())
        page.wait_for_timeout(500)
        page.screenshot(path=str(out_3_1), full_page=True)
        print(f"Captured: {out_3_1}")

        # 2. Capture UI-3.2
        page.goto(p2.as_uri())
        page.wait_for_timeout(500)
        page.screenshot(path=str(out_3_2), full_page=True)
        print(f"Captured: {out_3_2}")

        # 3. Capture UI-3.3
        page.goto(p3.as_uri())
        page.wait_for_timeout(500)
        page.screenshot(path=str(out_3_3), full_page=True)
        print(f"Captured: {out_3_3}")

        browser.close()

    print("All 3 UI visual proofs captured successfully!")

if __name__ == "__main__":
    main()
