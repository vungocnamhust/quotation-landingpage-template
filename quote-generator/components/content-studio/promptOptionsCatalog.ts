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
    description: '3–4 star international · Heritage & premium',
    detailText: 'Brand Voice: Capella speaks to discerning travellers who appreciate quality without ostentation. Heritage properties, thoughtful curation, and a tone that is polished but never stiff. Warmth lives in the details.',
  },
  {
    id: 'selvara',
    category: 'brands',
    label: 'Selvara Journeys',
    description: '4–5 star international · Luxury slow travel & cultural depth',
    detailText: 'Brand Voice: Selvara writes like a travel essayist, not a catalogue. Every destination is a chapter, every hotel a character, every ritual worth a paragraph. Speak in layers — cultural context, sensory detail, local nuance — for guests who read before they book.',
  },
  {
    id: 'vietnam_safar',
    category: 'brands',
    label: 'Vietnam Safar',
    description: 'Simple, relaxed & straight to the point',
    detailText: 'Brand Voice: Built for Arabic-speaking travellers who value clarity and ease. No flourish, no filler — just warm, direct communication that feels like a trusted friend planning the trip for you. Keep it light, keep it real.',
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

import contentBudgetsData from '../../config/contentBudgets.json' with { type: 'json' };

const dayDescBudget = contentBudgetsData?.budgets?.itinerary_day?.description;
const dayDescTarget = dayDescBudget?.targetWords ?? '~120 words';
const dayDescMax = dayDescBudget?.pdfCeilingChars ?? 1150;
const dayDescBuffer = dayDescBudget?.bufferChars ?? 350;

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
    description: `2-paragraph guided tour (${dayDescTarget})`,
    detailText: `Rule Text: ${dayDescTarget} (600–800 chars) split into Morning & Afternoon paragraphs. Leaves ~${dayDescBuffer}-char buffer under PDF A4 ceiling (${dayDescMax} chars). Bold key attractions (e.g. **Temple of Literature**).`,
  },
  {
    id: 'GR-CITY-INTRO',
    category: 'ground_rules',
    label: '[GR-CITY-INTRO] City Intro Entry',
    description: `City overview for open days (${dayDescTarget})`,
    detailText: `Rule Text: When entry specifies only a destination, write a full-day city overview & orientation (${dayDescTarget}).`,
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
    detailText: `Rule Text: ${dayDescTarget} description explicitly stating a free day at leisure (no service arranged), followed by curated recommendations.`,
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
