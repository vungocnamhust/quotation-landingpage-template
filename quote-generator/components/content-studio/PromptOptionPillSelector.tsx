'use client';

import { useState } from 'react';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';
import { Info, Tag, Check, Plus, Shield, Sparkles, Building, FileText, Database, Pin } from 'lucide-react';
import type { ContentFactInput } from '../quotation-workspace/useQuotationWorkspace';

export type PromptCategoryKey = 'brands' | 'modes' | 'ground_rules' | 'facts' | 'constraints';

export type PromptOptionItem = {
  id: string;
  category: PromptCategoryKey;
  label: string;
  description: string;
  detailText: string;
  isDefault?: boolean;
  factValue?: unknown;
  rawValue?: unknown;
};

export const BRAND_OPTIONS: PromptOptionItem[] = [
  {
    id: 'capella_travel',
    category: 'brands',
    label: 'Capella Travel',
    description: 'Polished urban luxury & bespoke hospitality',
    detailText: 'Brand Voice: Cosmopolitan, refined, high-touch luxury service. Emphasizes curated urban elegance and personalized itineraries.',
  },
  {
    id: 'selvara',
    category: 'brands',
    label: 'Selvara Journeys',
    description: 'Sanctuary, nature, tranquility & wellness',
    detailText: 'Brand Voice: Quiet luxury, immersive nature, wellness & eco-mindful retreats. Focuses on peaceful luxury and eco-harmony.',
  },
  {
    id: 'vietnam_safar',
    category: 'brands',
    label: 'Vietnam Safar',
    description: 'Authentic heritage, immersive exploration',
    detailText: 'Brand Voice: Authentic local heritage, vivid cultural storytelling, active discovery. Warm and deeply rooted in local traditions.',
  },
];

export const MODE_OPTIONS: PromptOptionItem[] = [
  {
    id: 'storytelling',
    category: 'modes',
    label: 'Storytelling Mode',
    description: 'Evocative sensory cadence supported by facts',
    detailText: 'Style Rule: Use rich sensory detail, evocative pacing, and emotional resonance. Ideal for leisure, honeymoon, and scenic journeys.',
  },
  {
    id: 'detailed',
    category: 'modes',
    label: 'Detailed Mode',
    description: 'Restrained, precise & sequence-focused',
    detailText: 'Style Rule: Prefer exact chronological sequence, clear logistics, and concise factual reporting without fluff.',
  },
];

export const GROUND_RULE_OPTIONS: PromptOptionItem[] = [
  {
    id: 'GR-7030',
    category: 'ground_rules',
    label: '[GR-7030] 70/30 Protocol',
    description: '70% structured discovery, 30% open buffer',
    detailText: 'Rule Text: Balance 70% guided sights and top-tier local eats with 30% spontaneous detours and relaxing unscripted buffer.',
  },
  {
    id: 'GR-DAY-NAMING',
    category: 'ground_rules',
    label: '[GR-DAY-NAMING] Day Title Formula',
    description: 'Structured day title format',
    detailText: 'Rule Text: Receive a brief, structured title following [Adjective] + [City] or [Pace] + [Place] + [Highlights].',
  },
  {
    id: 'GR-TOUR-FULLDAY',
    category: 'ground_rules',
    label: '[GR-TOUR-FULLDAY] Full-Day Excursion',
    description: '2-paragraph guided tour (~120 words)',
    detailText: 'Rule Text: ~120 words split into Morning & Afternoon paragraphs. Highlight key attractions in bold (e.g. **Temple of Literature**).',
  },
  {
    id: 'GR-CITY-INTRO',
    category: 'ground_rules',
    label: '[GR-CITY-INTRO] City Intro Entry',
    description: 'City overview for open days (~120 words)',
    detailText: 'Rule Text: When entry specifies only a destination, write a full-day city overview & orientation (~120 words).',
  },
  {
    id: 'GR-ACCOMMODATION',
    category: 'ground_rules',
    label: '[GR-ACCOMMODATION] Hotel Highlights',
    description: 'Overnight stay feature summary (~30 words)',
    detailText: 'Rule Text: Add a ~30-word description highlighting key amenities, style, and setting whenever accommodation is listed.',
  },
  {
    id: 'GR-FREE-HALF-DAY',
    category: 'ground_rules',
    label: '[GR-FREE-HALF-DAY] Free Half Day',
    description: 'Exactly 2 sentences for unguided time',
    detailText: 'Rule Text: Kept to exactly 2 sentences, explicitly stating that morning or afternoon is at leisure with no service arranged.',
  },
  {
    id: 'GR-FREE-FULL-DAY',
    category: 'ground_rules',
    label: '[GR-FREE-FULL-DAY] Full Free Day',
    description: 'Full day at leisure with recommendations',
    detailText: 'Rule Text: ~120-word description explicitly stating a free day at leisure (no service arranged), followed by curated recommendations.',
  },
];

export const CONSTRAINT_OPTIONS: PromptOptionItem[] = [
  {
    id: 'schema_validation',
    category: 'constraints',
    label: 'Schema Validation',
    description: 'Strict JSON schema compliance',
    detailText: 'Constraint: Output must strictly conform to expected response JSON schema with no extra fields.',
  },
  {
    id: 'no_price_hallucination',
    category: 'constraints',
    label: 'No Price Hallucination',
    description: 'Rely solely on verified pricing facts',
    detailText: 'Constraint: Never invent or estimate price figures not explicitly passed in input facts.',
  },
  {
    id: 'brand_safety',
    category: 'constraints',
    label: 'Brand Safety Policy',
    description: 'Adhere to brand vocabulary & avoid list',
    detailText: 'Constraint: Strictly use preferred vocabulary and avoid words specified in brand policy.',
  },
];

function readFact(value: Record<string, unknown> | undefined, path: Array<string | number>): unknown {
  let current: unknown = value;
  for (const part of path) {
    current = current && typeof current === 'object' ? (current as Record<string | number, unknown>)[part] : undefined;
  }
  return current;
}

function factKeyLabel(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/^./, (char) => char.toUpperCase());
}

function formatFactPillSummary(value: unknown): string {
  if (value === undefined || value === null || value === '') return 'Not provided';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    if (!value.length) return 'Not provided';
    if (value.every((i) => typeof i === 'string' || typeof i === 'number')) return value.join(', ');
    const dayNames = value
      .map((item) => {
        if (item && typeof item === 'object') {
          const rec = item as Record<string, unknown>;
          return rec.destination || rec.title || (rec.day_number ? `Day ${String(rec.day_number)}` : undefined);
        }
        return undefined;
      })
      .filter(Boolean);
    if (dayNames.length) {
      const summaryList = dayNames.slice(0, 3).join(', ');
      const extra = dayNames.length > 3 ? ` +${dayNames.length - 3} more` : '';
      return `${value.length} Days (${summaryList}${extra})`;
    }
    return `${value.length} items`;
  }
  if (typeof value === 'object') {
    const rec = value as Record<string, unknown>;
    const summaryParts: string[] = [];
    if (rec.adults) summaryParts.push(`${String(rec.adults)} Adults`);
    if (rec.travel_style) summaryParts.push(String(rec.travel_style));
    if (rec.destinations && Array.isArray(rec.destinations)) summaryParts.push(rec.destinations.join(', '));
    if (summaryParts.length) return summaryParts.join(' · ');
    return 'Detailed Facts Object';
  }
  return String(value);
}

function RichFactDetailViewer({ rawValue }: { rawValue: unknown }) {
  if (rawValue === undefined || rawValue === null || rawValue === '') {
    return <p className={cn(getTypographyClassName('caption'), 'mt-1 text-[var(--color-muted)]')}>No fact data provided for this input.</p>;
  }

  // Handle Array of Objects (e.g. Itinerary Days or Component Items)
  if (Array.isArray(rawValue) && rawValue.length > 0 && typeof rawValue[0] === 'object' && rawValue[0] !== null) {
    return (
      <div className="mt-2 grid max-h-64 min-w-0 w-full gap-2 overflow-y-auto pr-1">
        {rawValue.map((item, idx) => {
          const rec = item as Record<string, unknown>;
          const dayNum = rec.day_number ?? idx + 1;
          const dest = String(rec.destination || rec.title || `Day ${dayNum}`);
          const summary = rec.summary || rec.description;
          const hotel = rec.hotel || rec.accommodation;
          const acts = Array.isArray(rec.activities) ? rec.activities : Array.isArray(rec.highlights) ? rec.highlights : null;

          return (
            <div key={idx} className="min-w-0 w-full rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-2.5 overflow-hidden">
              <div className="flex min-w-0 items-center justify-between gap-2 border-b border-[var(--color-border)] pb-1">
                <span className={cn(getTypographyClassName('caption'), 'min-w-0 flex-1 truncate text-[var(--color-accent)]')}>
                  🗓️ Day {String(dayNum)}: {dest}
                </span>
                {hotel ? (
                  <span className={cn(getTypographyClassName('caption'), 'shrink-0 text-[var(--color-muted)] max-w-[45%] truncate text-right')}>
                    🏨 {String(hotel)}
                  </span>
                ) : null}
              </div>

              {summary ? (
                <p className={cn(getTypographyClassName('bodySm'), 'mt-1 break-words text-[var(--color-on-surface)]')}>
                  {String(summary)}
                </p>
              ) : null}

              {acts && acts.length > 0 ? (
                <div className="mt-1.5 flex flex-wrap gap-1 min-w-0">
                  {acts.map((act, aIdx) => (
                    <span key={aIdx} className={cn(getTypographyClassName('caption'), 'min-w-0 max-w-full truncate rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 text-[var(--color-muted)]')}>
                      • {String(act)}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    );
  }

  // Handle Object (e.g. Trip Facts, Customer Facts)
  if (typeof rawValue === 'object' && rawValue !== null) {
    return (
      <dl className="mt-2 grid min-w-0 w-full gap-1.5 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-2.5 overflow-hidden">
        {Object.entries(rawValue as Record<string, unknown>).map(([key, item]) => (
          <div key={key} className="flex min-w-0 items-center justify-between gap-2 border-b border-[var(--color-border)]/50 pb-1">
            <dt className={cn(getTypographyClassName('caption'), 'shrink-0 text-[var(--color-muted)]')}>{factKeyLabel(key)}:</dt>
            <dd className={cn(getTypographyClassName('caption'), 'min-w-0 flex-1 text-right break-words text-[var(--color-on-surface)]')}>{formatFactPillSummary(item)}</dd>
          </div>
        ))}
      </dl>
    );
  }

  // Handle Array of Primitives
  if (Array.isArray(rawValue)) {
    return (
      <ul className="mt-2 grid min-w-0 w-full gap-1">
        {rawValue.map((item, idx) => (
          <li key={idx} className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-on-surface)]')}>
            • {String(item)}
          </li>
        ))}
      </ul>
    );
  }

  // Handle Primitive String / Number
  return (
    <p className={cn(getTypographyClassName('bodySm'), 'mt-1.5 break-words text-[var(--color-on-surface)] font-mono bg-[var(--color-surface-muted)] p-2 rounded border border-[var(--color-border)]')}>
      &quot;{String(rawValue)}&quot;
    </p>
  );
}

type Props = {
  defaultBrandId?: string;
  selectedBrandId: string;
  onBrandChange: (brandId: string) => void;
  selectedMode: string;
  onModeChange: (mode: string) => void;
  selectedRuleIds: string[];
  onToggleRule: (ruleId: string) => void;
  selectedConstraintIds: string[];
  onToggleConstraint: (constraintId: string) => void;
  factInputs?: ContentFactInput[];
  facts?: Record<string, unknown>;
  disabledFactIds?: string[];
  onToggleFact?: (factId: string) => void;
  disabled?: boolean;
};

export function PromptOptionPillSelector({
  defaultBrandId = 'capella_travel',
  selectedBrandId,
  onBrandChange,
  selectedMode,
  onModeChange,
  selectedRuleIds,
  onToggleRule,
  selectedConstraintIds,
  onToggleConstraint,
  factInputs = [],
  facts,
  disabledFactIds = [],
  onToggleFact,
  disabled = false,
}: Props) {
  const [activeCategory, setActiveCategory] = useState<PromptCategoryKey>('brands');
  const [hoveredOption, setHoveredOption] = useState<PromptOptionItem | null>(null);
  const [pinnedOptionId, setPinnedOptionId] = useState<string | null>(null);
  const [isInspectorHovered, setIsInspectorHovered] = useState<boolean>(false);

  const categories: Array<{ key: PromptCategoryKey; label: string; icon: React.ReactNode }> = [
    { key: 'brands', label: 'Brand Voice', icon: <Building className="w-3.5 h-3.5 text-[var(--color-accent)]" /> },
    { key: 'modes', label: 'Writing Mode', icon: <Sparkles className="w-3.5 h-3.5 text-[var(--color-accent)]" /> },
    { key: 'ground_rules', label: 'Ground Rules', icon: <FileText className="w-3.5 h-3.5 text-[var(--color-accent)]" /> },
    { key: 'facts', label: `Facts Used (${factInputs.length})`, icon: <Database className="w-3.5 h-3.5 text-[var(--color-accent)]" /> },
    { key: 'constraints', label: 'Constraints', icon: <Shield className="w-3.5 h-3.5 text-[var(--color-accent)]" /> },
  ];

  const getFactOptions = (): PromptOptionItem[] => {
    return factInputs.map((input) => {
      const rawVal = readFact(facts, input.path);
      const nights = input.id === 'duration' ? readFact(facts, ['trip_facts', 'duration_nights']) : undefined;
      const formatted = typeof rawVal === 'number' && typeof nights === 'number' ? `${rawVal} days / ${nights} nights` : formatFactPillSummary(rawVal);

      return {
        id: input.id,
        category: 'facts',
        label: input.label,
        description: `Path: ${input.path.join('.')}`,
        detailText: `Injected Fact (${input.required ? 'Required' : 'Optional'})`,
        factValue: formatted,
        rawValue: rawVal,
      };
    });
  };

  const getCategoryOptions = (cat: PromptCategoryKey): PromptOptionItem[] => {
    switch (cat) {
      case 'brands':
        return BRAND_OPTIONS.map((b) => ({ ...b, isDefault: b.id === defaultBrandId }));
      case 'modes':
        return MODE_OPTIONS;
      case 'ground_rules':
        return GROUND_RULE_OPTIONS;
      case 'facts':
        return getFactOptions();
      case 'constraints':
        return CONSTRAINT_OPTIONS;
      default:
        return [];
    }
  };

  const currentOptions = getCategoryOptions(activeCategory);

  // Derived effective active inspected option
  const activeInspectedOption =
    hoveredOption ||
    (pinnedOptionId ? currentOptions.find((opt) => opt.id === pinnedOptionId) : null) ||
    (isInspectorHovered && currentOptions.length > 0 ? currentOptions[0] : null);

  const isOptionSelected = (opt: PromptOptionItem): boolean => {
    if (opt.category === 'brands') return selectedBrandId === opt.id;
    if (opt.category === 'modes') return selectedMode === opt.id;
    if (opt.category === 'ground_rules') return selectedRuleIds.includes(opt.id);
    if (opt.category === 'facts') return !disabledFactIds.includes(opt.id);
    if (opt.category === 'constraints') return selectedConstraintIds.includes(opt.id);
    return false;
  };

  const handleOptionClick = (opt: PromptOptionItem) => {
    if (disabled) return;
    setPinnedOptionId((curr) => (curr === opt.id ? null : opt.id));
    if (opt.category === 'brands') onBrandChange(opt.id);
    else if (opt.category === 'modes') onModeChange(opt.id);
    else if (opt.category === 'ground_rules') onToggleRule(opt.id);
    else if (opt.category === 'facts' && onToggleFact) onToggleFact(opt.id);
    else if (opt.category === 'constraints') onToggleConstraint(opt.id);
  };

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 min-w-0 w-full overflow-hidden">
      {/* Category Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2.5 min-w-0 w-full">
        <div className="flex flex-wrap gap-1 min-w-0">
          {categories.map((cat) => {
            const isActive = cat.key === activeCategory;
            return (
              <button
                key={cat.key}
                type="button"
                disabled={disabled}
                onClick={() => {
                  setActiveCategory(cat.key);
                  setPinnedOptionId(null);
                }}
                className={cn(
                  getTypographyClassName('caption'),
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all cursor-pointer min-w-0',
                  isActive
                    ? 'bg-[var(--color-accent)] text-white shadow-2xs'
                    : 'bg-[var(--color-surface)] text-[var(--color-muted)] hover:text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] border border-[var(--color-border)]'
                )}
              >
                {cat.icon}
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)] flex items-center gap-1 shrink-0')}>
          <Info className="w-3 h-3 text-[var(--color-accent)]" />
          Click pill to lock view
        </span>
      </div>

      {/* Option Pill Badges */}
      <div className="flex flex-wrap gap-2 pt-1 min-h-[3rem] min-w-0 w-full">
        {currentOptions.length === 0 ? (
          <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)] py-2')}>No facts or options for this section.</span>
        ) : (
          currentOptions.map((opt) => {
            const selected = isOptionSelected(opt);
            const isPinned = pinnedOptionId === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => handleOptionClick(opt)}
                onMouseEnter={() => setHoveredOption(opt)}
                onMouseLeave={() => setHoveredOption(null)}
                className={cn(
                  getTypographyClassName('caption'),
                  'group relative flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-button)] border transition-all cursor-pointer min-w-0 max-w-full',
                  selected
                    ? 'border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs'
                    : 'border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-wash)]',
                  isPinned && 'ring-2 ring-[var(--color-accent)] ring-offset-1'
                )}
              >
                <span
                  className={cn(
                    'flex h-4 w-4 shrink-0 items-center justify-center rounded-full transition-colors',
                    getTypographyClassName('caption'),
                    selected ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-border)] text-[var(--color-muted)] group-hover:bg-[var(--color-accent)] group-hover:text-white'
                  )}
                >
                  {selected ? <Check className="w-2.5 h-2.5" /> : <Plus className="w-2.5 h-2.5" />}
                </span>
                <span className="truncate min-w-0">{opt.label}</span>
                {opt.factValue !== undefined ? (
                  <span className={cn(getTypographyClassName('caption'), 'max-w-[10rem] truncate opacity-85 font-mono')}>
                    : {String(opt.factValue)}
                  </span>
                ) : null}
                {opt.isDefault ? (
                  <span className={cn(getTypographyClassName('caption'), 'ml-1 rounded bg-[var(--color-accent)]/10 px-1.5 py-0.5 text-[var(--color-accent)] shrink-0')}>
                    Default
                  </span>
                ) : null}
              </button>
            );
          })
        )}
      </div>

      {/* Hover / Pinned Active Detail Inspector Card */}
      {activeInspectedOption ? (
        <div
          onMouseEnter={() => setIsInspectorHovered(true)}
          onMouseLeave={() => setIsInspectorHovered(false)}
          className="mt-1 min-w-0 w-full rounded-[var(--radius-button)] border border-[var(--color-accent)]/40 bg-[var(--color-surface)] p-3 shadow-xs transition-all overflow-hidden"
        >
          <div className="flex min-w-0 items-center justify-between gap-2 border-b border-[var(--color-border)] pb-1.5">
            <span className={cn(getTypographyClassName('label'), 'min-w-0 flex-1 truncate text-[var(--color-accent)] flex items-center gap-1.5')}>
              <Tag className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{activeInspectedOption.label}</span>
              {activeInspectedOption.isDefault ? <span className="shrink-0 text-[var(--color-muted)]">(Default)</span> : null}
            </span>
            <div className="flex shrink-0 items-center gap-1.5 text-right">
              <span className={cn(getTypographyClassName('caption'), isOptionSelected(activeInspectedOption) ? 'text-[var(--color-accent)]' : 'text-[var(--color-muted)]')}>
                {isOptionSelected(activeInspectedOption) ? '✓ Included' : '+ Add'}
              </span>
              {pinnedOptionId === activeInspectedOption.id ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPinnedOptionId(null);
                  }}
                  className={cn(getTypographyClassName('caption'), 'ml-1 flex items-center gap-0.5 rounded bg-[var(--color-accent-wash)] px-1.5 py-0.5 text-[var(--color-accent)] hover:bg-[var(--color-accent)] hover:text-white cursor-pointer transition-all')}
                  title="Unpin detail view"
                >
                  <Pin className="w-2.5 h-2.5" />
                  <span>Pinned</span>
                </button>
              ) : null}
            </div>
          </div>

          {activeInspectedOption.category === 'facts' ? (
            <RichFactDetailViewer rawValue={activeInspectedOption.rawValue} />
          ) : (
            <p className={cn(getTypographyClassName('bodySm'), 'mt-1.5 break-words text-[var(--color-on-surface)]')}>
              {activeInspectedOption.detailText}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
