'use client';

import { useBrand } from '../context/BrandContext.tsx';
import { BRANDS_DATA, type BrandKey } from '../data/brandsData.ts';
import { getBrandTypographyConfig } from '../config/typography.ts';

export default function BrandSpecModal() {
  const {
    currentBrand,
    currentBrandKey,
    resolvedViewMode,
    themeId,
    setBrand,
    isInspectingTokens,
    setIsInspectingTokens,
  } = useBrand();

  if (!isInspectingTokens) {
    return null;
  }

  const typographySpec = getBrandTypographyConfig(currentBrandKey);
  const brandKeys: BrandKey[] = ['vietnam-safar', 'capella-travel', 'selvara'];
  const palette = currentBrand.themeTokens.palette;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4 backdrop-blur-lg">
      <div className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-[var(--frame-radius)] border border-[var(--border-color)] bg-[var(--surface-canvas)] p-6 text-[var(--text-primary)] shadow-[var(--shadow-custom)] sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4 border-b border-[var(--border-color)] pb-4">
          <div className="grid gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="brand-badge typo-overline px-3 py-1">Theme Spec</span>
              <span className="typo-caption text-[var(--text-muted)]">
                `{themeId}` · {resolvedViewMode}
              </span>
            </div>
            <h2 className="typo-section-title">{currentBrand.name}</h2>
            <p className="typo-body-sm text-[var(--text-muted)]">{currentBrand.description}</p>
          </div>
          <button
            type="button"
            onClick={() => setIsInspectingTokens(false)}
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-[var(--border-color)]"
          >
            ✕
          </button>
        </div>

        <div className="mb-8 grid gap-2 rounded-2xl border border-[var(--border-color)] bg-black/5 p-2 md:grid-cols-3">
          {brandKeys.map((key) => {
            const active = key === currentBrandKey;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setBrand(key)}
                className={`typo-button-secondary rounded-xl px-3 py-3 transition-all ${
                  active
                    ? 'bg-[var(--accent-primary)] text-white'
                    : 'text-[var(--text-muted)] hover:bg-white/60 hover:text-[var(--text-primary)]'
                }`}
              >
                {BRANDS_DATA[key].name}
              </button>
            );
          })}
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="brand-card p-5">
            <h3 className="typo-label mb-3 text-[var(--text-accent)]">Surface Tokens</h3>
            <div className="grid gap-3">
              {[
                ['Canvas', palette.canvas],
                ['Paper', palette.paper],
                ['Accent', palette.accent],
                ['Accent Alternative', palette.accentAlt],
                ['Contrast', palette.contrast],
                ['Focus', palette.focus],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center gap-3 rounded-xl bg-black/5 p-3">
                  <div
                    className="h-9 w-9 rounded-lg border border-white/30"
                    style={{ backgroundColor: value }}
                  />
                  <div className="grid gap-0.5">
                    <span className="typo-caption">{label}</span>
                    <code className="typo-caption text-[var(--text-muted)]">{value}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="brand-card p-5">
            <h3 className="typo-label mb-3 text-[var(--text-accent)]">Typography Roles</h3>
            <div className="grid gap-3">
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-accent)]">Heading</span>
                <div className="typo-body-sm">{typographySpec.fonts.heading.label}</div>
              </div>
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-accent)]">Body</span>
                <div className="typo-body-sm">{typographySpec.fonts.body.label}</div>
              </div>
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-accent)]">Accent</span>
                <div className="typo-body-sm">{typographySpec.fonts.accent.label}</div>
              </div>
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-accent)]">Style note</span>
                <div className="typo-body-sm">{currentBrand.typography.styleNote}</div>
              </div>
            </div>
          </div>

          <div className="brand-card p-5">
            <h3 className="typo-label mb-3 text-[var(--text-accent)]">Brand Direction</h3>
            <div className="grid gap-4">
              <div>
                <span className="typo-caption text-[var(--text-muted)]">Mood</span>
                <p className="typo-body-sm mt-1">{currentBrand.mood}</p>
              </div>
              <div>
                <span className="typo-caption text-[var(--text-muted)]">Tone of voice</span>
                <p className="typo-body-sm mt-1">{currentBrand.toneOfVoice}</p>
              </div>
              <div>
                <span className="typo-caption text-[var(--text-muted)]">Audience</span>
                <p className="typo-body-sm mt-1">{currentBrand.targetAudience}</p>
              </div>
            </div>
          </div>

          <div className="brand-card p-5">
            <h3 className="typo-label mb-3 text-[var(--text-accent)]">Runtime Contract</h3>
            <div className="grid gap-3">
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-muted)]">Theme</span>
                <p className="typo-body-sm mt-1">{themeId}</p>
              </div>
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-muted)]">View mode</span>
                <p className="typo-body-sm mt-1">{resolvedViewMode}</p>
              </div>
              <div className="rounded-xl bg-black/5 p-3">
                <span className="typo-caption text-[var(--text-muted)]">Contact</span>
                <p className="typo-body-sm mt-1">
                  {currentBrand.contact.email} · {currentBrand.contact.phone}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 border-t border-[var(--border-color)] pt-4">
          <button
            type="button"
            onClick={() => setIsInspectingTokens(false)}
            className="brand-btn-primary typo-button-primary px-5 py-3"
          >
            Close Theme Spec
          </button>
        </div>
      </div>
    </div>
  );
}
