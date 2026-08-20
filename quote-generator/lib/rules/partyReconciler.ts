/**
 * Pure domain rules for party composition, guest identity, kid ages vector invariance,
 * and dynamic room configuration heuristics (TypeScript).
 *
 * Guarantees closed-loop state invariants:
 * 1. adults >= 1
 * 2. children >= 0
 * 3. length(kidAges) === children (clamped 0..17, default: 6)
 * 4. partyLabel & greetingName auto-inference (multilingual: en, vi, ar)
 * 5. Dynamic room configuration suggestions (DB rules or pure Tier-1 fallback)
 */

export type KidAgeCondition = "ANY" | "ALL_UNDER_12" | "ANY_12_AND_ABOVE" | "NO_KIDS";

export type RoomingSuggestionItem = {
  en: string;
  vi?: string | null;
  ar?: string | null;
  code?: string | null;
};

export type RoomingRule = {
  id: string;
  name: string;
  description?: string | null;
  min_adults: number;
  max_adults?: number | null;
  min_children: number;
  max_children?: number | null;
  min_infants?: number;
  max_infants?: number | null;
  kid_age_condition?: KidAgeCondition;
  suggestions: RoomingSuggestionItem[];
  min_rooms_formula?: string | null;
  priority?: number;
  is_active?: boolean;
};

export type CanonicalParty = {
  // Primary Lead Guest / Client
  customerName: string | null;
  clientName?: string | null;
  role?: "traveller" | "advisor" | string | null;

  // Passenger Composition (Pax Counts)
  adults: number;
  children: number;
  kidAges: number[];
  infants: number;
  infantAges?: number[];

  // Derived / Inferred Party Labels & Greetings
  partyLabel: string | null;
  greetingName: string | null;
  isPartyLabelCustom?: boolean;
  isGreetingNameCustom?: boolean;

  // Rooming & Accommodation Distribution
  roomConfiguration: string | null;
  roomNotes?: string | null;
  minEstimatedRooms?: number;
  roomSuggestions?: string[];

  // Preferences & Demographics
  travelStyle?: string | null;
  market?: string | null;
  nationality?: string | null;
  lang?: "en" | "vi" | "ar" | string;
};

export const DEFAULT_FALLBACK_ROOMING_RULES: RoomingRule[] = [
  {
    id: "rule_solo_traveler",
    name: "Solo Traveler",
    min_adults: 1,
    max_adults: 1,
    min_children: 0,
    max_children: 0,
    min_infants: 0,
    max_infants: 0,
    kid_age_condition: "NO_KIDS",
    suggestions: [
      { en: "1 Single Room", vi: "1 Phòng Đơn (Single Room)", ar: "غرفة مفردة واحدة" },
      { en: "1 Double (Single Occupancy)", vi: "1 Phòng Double (Sử dụng 1 người)", ar: "غرفة مزدوجة (إشغال فردي)" },
    ],
    min_rooms_formula: "1",
    priority: 100,
    is_active: true,
  },
  {
    id: "rule_couple_no_kids",
    name: "Couple / Pair",
    min_adults: 2,
    max_adults: 2,
    min_children: 0,
    max_children: 0,
    min_infants: 0,
    max_infants: 0,
    kid_age_condition: "NO_KIDS",
    suggestions: [
      { en: "1 Double (King Bed)", vi: "1 Phòng Double (Giường King)", ar: "غرفة مزدوجة (سرير كينج)" },
      { en: "1 Twin (2 Separate Beds)", vi: "1 Phòng Twin (2 Giường đơn tách biệt)", ar: "غرفة توأم (سريرين منفصلين)" },
    ],
    min_rooms_formula: "1",
    priority: 90,
    is_active: true,
  },
  {
    id: "rule_family_young_kids",
    name: "Couple with Young Kids",
    min_adults: 2,
    max_adults: 2,
    min_children: 1,
    max_children: 2,
    min_infants: 0,
    max_infants: 2,
    kid_age_condition: "ALL_UNDER_12",
    suggestions: [
      { en: "1 Double Room + Extra Bed", vi: "1 Phòng Double + Kê thêm giường phụ", ar: "غرفة مزدوجة + سرير إضافي" },
      { en: "1 Double + 1 Twin (Connecting)", vi: "1 Double + 1 Twin (Phòng thông nhau)", ar: "غرفة مزدوجة + غرفة توأم متصلة" },
      { en: "1 Family Suite / Villa", vi: "1 Căn Family Suite / Villa", ar: "جناح عائلي / فيلا" },
    ],
    min_rooms_formula: "1",
    priority: 80,
    is_active: true,
  },
  {
    id: "rule_family_teen_kids",
    name: "Couple with Teen Kids",
    min_adults: 2,
    max_adults: 2,
    min_children: 1,
    max_children: 3,
    min_infants: 0,
    max_infants: 2,
    kid_age_condition: "ANY_12_AND_ABOVE",
    suggestions: [
      { en: "1 Double + 1 Twin (Connecting)", vi: "1 Double + 1 Twin (Phòng thông nhau)", ar: "غرفة مزدوجة + غرفة توأم متصلة" },
      { en: "2 Interconnecting Rooms", vi: "2 Phòng thông nhau (Interconnecting)", ar: "غرفتان متصلتان" },
      { en: "1 Family Suite / Villa", vi: "1 Căn Family Suite / Villa", ar: "جناح عائلي / فيلا" },
    ],
    min_rooms_formula: "2",
    priority: 75,
    is_active: true,
  },
  {
    id: "rule_three_adults",
    name: "Three Adults",
    min_adults: 3,
    max_adults: 3,
    min_children: 0,
    max_children: 0,
    min_infants: 0,
    max_infants: 0,
    kid_age_condition: "NO_KIDS",
    suggestions: [
      { en: "1 Double + 1 Single", vi: "1 Phòng Double + 1 Phòng Single", ar: "غرفة مزدوجة + غرفة مفردة" },
      { en: "1 Triple Room / Suite", vi: "1 Phòng Ba người (Triple Room/Suite)", ar: "غرفة ثلاثية / جناح" },
      { en: "3 Single Rooms", vi: "3 Phòng Đơn riêng biệt", ar: "3 غرف مفردة" },
    ],
    min_rooms_formula: "2",
    priority: 70,
    is_active: true,
  },
  {
    id: "rule_quad_adults",
    name: "Adult Group (4+ Adults)",
    min_adults: 4,
    max_adults: null,
    min_children: 0,
    max_children: 0,
    min_infants: 0,
    max_infants: 0,
    kid_age_condition: "NO_KIDS",
    suggestions: [
      { en: "{rooms} Double Rooms", vi: "{rooms} Phòng Double", ar: "{rooms} غرف مزدوجة" },
      { en: "{rooms} Twin Rooms", vi: "{rooms} Phòng Twin", ar: "{rooms} غرف توأم" },
      { en: "Multi-bedroom Private Villa", vi: "Villa riêng nhiều phòng ngủ", ar: "فيلا خاصة متعددة غرف النوم" },
    ],
    min_rooms_formula: "ceil(adults / 2)",
    priority: 60,
    is_active: true,
  },
  {
    id: "rule_large_family_multigen",
    name: "Large Family / Multi-gen Group",
    min_adults: 1,
    max_adults: null,
    min_children: 1,
    max_children: null,
    min_infants: 0,
    max_infants: null,
    kid_age_condition: "ANY",
    suggestions: [
      { en: "{rooms} Rooms (Connecting/Adjoining)", vi: "{rooms} Phòng (Thông nhau / Cạnh nhau)", ar: "{rooms} غرف (متصلة / متجاورة)" },
      { en: "Family Suite / Multi-bedroom Villa", vi: "Family Suite / Villa nhiều phòng ngủ", ar: "جناح عائلي / فيلا متعددة غرف النوم" },
      { en: "{adults} Double + Connecting Kids Room", vi: "{adults} Phòng Double + Phòng Trẻ em thông nhau", ar: "{adults} مزدوجة + غرفة أطفال متصلة" },
    ],
    min_rooms_formula: "ceil(adults / 2) + ceil(children / 2)",
    priority: 10,
    is_active: true,
  },
];

export function normalizeKidAges(
  kidAges: number[] | null | undefined,
  childrenCount: number
): number[] {
  const safeCount = Math.max(0, childrenCount);
  const raw = Array.isArray(kidAges) ? [...kidAges] : [];
  while (raw.length < safeCount) {
    raw.push(6);
  }
  return raw
    .slice(0, safeCount)
    .map((age) => Math.max(0, Math.min(17, isNaN(age) ? 6 : Math.round(age))));
}

export function updateKidAgeVector(
  kidAges: number[] | null | undefined,
  childrenCount: number,
  index: number,
  rawAge: number | string
): number[] {
  const safeCount = Math.max(0, childrenCount);
  if (index < 0 || index >= safeCount) return normalizeKidAges(kidAges, safeCount);

  const numVal = typeof rawAge === "string" ? parseInt(rawAge, 10) : rawAge;
  const clampedAge = Math.max(0, Math.min(17, isNaN(numVal) ? 6 : Math.round(numVal)));

  const current = normalizeKidAges(kidAges, safeCount);
  current[index] = clampedAge;
  return current;
}

export function resolveClientDisplayName(
  role: string | null | undefined,
  customerName: string | null | undefined,
  clientName?: string | null
): string {
  const isAdvisor = (role || "").trim().toLowerCase() === "advisor";
  const cName = (clientName || "").trim();
  const custName = (customerName || "").trim();

  if (isAdvisor && cName) {
    return cName;
  }
  return custName || "Valued Client";
}

export function generatePartyLabel(
  adults: number | null | undefined,
  children: number | null | undefined = 0,
  customerName?: string | null,
  lang: string = "en"
): string {
  const safeAdults = adults && adults > 0 ? adults : 2;
  const safeKids = children && children > 0 ? children : 0;

  let adultStr = `${safeAdults} Adult${safeAdults > 1 ? "s" : ""}`;
  let kidStr = safeKids > 0 ? `${safeKids} Child${safeKids > 1 ? "ren" : ""}` : "";

  if (lang === "vi") {
    adultStr = `${safeAdults} Người lớn`;
    kidStr = safeKids > 0 ? `${safeKids} Trẻ em` : "";
  } else if (lang === "ar") {
    adultStr = `${safeAdults} بالغ${safeAdults > 1 ? "ين" : ""}`;
    kidStr = safeKids > 0 ? `${safeKids} ${safeKids > 1 ? "أطفال" : "طفل"}` : "";
  }

  const partyCounts = [adultStr, kidStr].filter(Boolean).join(", ");
  const name = (customerName || "").trim();

  if (name && partyCounts) {
    if (lang === "vi") {
      return `${name} & Đoàn (${partyCounts})`;
    }
    if (lang === "ar") {
      return `${name} والوفد المرافق (${partyCounts})`;
    }
    return `${name} & Party (${partyCounts})`;
  }
  if (name) {
    return name;
  }
  return partyCounts;
}

export function inferGreetingName(customerName: string | null | undefined, lang: string = "en"): string | null {
  const name = (customerName || "").trim();
  if (!name) return null;

  const nameLower = name.toLowerCase();
  if (lang === "vi") {
    if (nameLower.startsWith("kính gửi") || nameLower.startsWith("thân gửi")) return name;
    return `Kính gửi ${name}`;
  }
  if (lang === "ar") {
    if (nameLower.startsWith("عزيزي") || nameLower.startsWith("السيد")) return name;
    return `عزيزي ${name}`;
  }

  if (nameLower.startsWith("dear ")) return name;
  return `Dear ${name}`;
}

export function calculateMinEstimatedRooms(
  adults: number,
  children: number = 0,
  formula?: string | null
): number {
  const safeAdults = Math.max(1, adults);
  const safeKids = Math.max(0, children);

  if (formula === "1") return 1;
  if (formula === "2") return 2;
  if (formula === "ceil(adults / 2)") return Math.ceil(safeAdults / 2);

  return Math.ceil(safeAdults / 2) + Math.ceil(safeKids / 2);
}

export function formatSuggestionTemplate(
  template: string,
  adults: number,
  children: number,
  rooms: number
): string {
  return template
    .replace(/{adults}/g, String(adults))
    .replace(/{children}/g, String(children))
    .replace(/{rooms}/g, String(rooms));
}

export function generateRoomSuggestions(
  adults: number = 2,
  children: number = 0,
  kidAges: number[] = [],
  lang: string = "en",
  customRules: RoomingRule[] = DEFAULT_FALLBACK_ROOMING_RULES
): { minEstimatedRooms: number; suggestions: string[]; matchedRuleId: string | null } {
  const safeAdults = Math.max(1, adults);
  const safeKids = Math.max(0, children);

  // Normalize kidAges vector
  const safeAges = [...kidAges];
  while (safeAges.length < safeKids) safeAges.push(6);
  const effectiveAges = safeAges.slice(0, safeKids);

  const rulesToEvaluate = customRules && customRules.length > 0 ? customRules : DEFAULT_FALLBACK_ROOMING_RULES;

  for (const rule of rulesToEvaluate) {
    if (rule.is_active === false) continue;

    // Adult bounds
    if (safeAdults < rule.min_adults) continue;
    if (rule.max_adults !== null && rule.max_adults !== undefined && safeAdults > rule.max_adults) continue;

    // Children bounds
    if (safeKids < rule.min_children) continue;
    if (rule.max_children !== null && rule.max_children !== undefined && safeKids > rule.max_children) continue;

    // Kid age condition
    if (rule.kid_age_condition === "NO_KIDS" && safeKids > 0) continue;
    if (rule.kid_age_condition === "ALL_UNDER_12") {
      if (safeKids === 0 || !effectiveAges.every((age) => age < 12)) continue;
    }
    if (rule.kid_age_condition === "ANY_12_AND_ABOVE") {
      if (safeKids === 0 || !effectiveAges.some((age) => age >= 12)) continue;
    }

    const minRooms = calculateMinEstimatedRooms(safeAdults, safeKids, rule.min_rooms_formula);
    const langKey = (lang === "vi" || lang === "ar" ? lang : "en") as keyof RoomingSuggestionItem;

    const suggestions = rule.suggestions.map((s) => {
      const rawText = s[langKey] || s.en || "";
      return formatSuggestionTemplate(rawText, safeAdults, safeKids, minRooms);
    });

    return {
      minEstimatedRooms: minRooms,
      suggestions,
      matchedRuleId: rule.id,
    };
  }

  // Fallback if no rules matched
  const fallbackRooms = Math.ceil(safeAdults / 2) + Math.ceil(safeKids / 2);
  const fallbackText = lang === "vi" ? `${fallbackRooms} Phòng` : `${fallbackRooms} Rooms`;
  return {
    minEstimatedRooms: fallbackRooms,
    suggestions: [fallbackText],
    matchedRuleId: null,
  };
}

export function createDefaultParty(customerName: string = "", lang: string = "en"): CanonicalParty {
  const adults = 2;
  const children = 0;
  const kidAges: number[] = [];
  const roomEval = generateRoomSuggestions(adults, children, kidAges, lang);

  return {
    customerName: customerName || null,
    clientName: null,
    role: "traveller",
    adults,
    children,
    kidAges,
    infants: 0,
    infantAges: [],
    partyLabel: generatePartyLabel(adults, children, customerName, lang),
    greetingName: inferGreetingName(customerName, lang),
    isPartyLabelCustom: false,
    isGreetingNameCustom: false,
    roomConfiguration: null,
    roomNotes: null,
    minEstimatedRooms: roomEval.minEstimatedRooms,
    roomSuggestions: roomEval.suggestions,
    lang,
  };
}

export const partyReconciler = {
  resolveClientDisplayName,
  generatePartyLabel,
  inferGreetingName,
  normalizeKidAges,
  updateKidAgeVector,
  calculateMinEstimatedRooms,
  formatSuggestionTemplate,
  generateRoomSuggestions,
  createDefaultParty,

  /**
   * Set adult count and automatically reconcile partyLabel and room suggestions.
   */
  setAdults(party: CanonicalParty, nextAdults: number, rules?: RoomingRule[]): CanonicalParty {
    const safeAdults = Math.max(1, nextAdults);
    const lang = party.lang || "en";

    const prevAutoLabel = generatePartyLabel(party.adults, party.children, party.customerName, lang);
    const shouldUpdateLabel = !party.partyLabel || !party.isPartyLabelCustom || party.partyLabel === prevAutoLabel;
    const nextPartyLabel = shouldUpdateLabel
      ? generatePartyLabel(safeAdults, party.children, party.customerName, lang)
      : party.partyLabel;

    const roomEval = generateRoomSuggestions(safeAdults, party.children, party.kidAges, lang, rules);

    return {
      ...party,
      adults: safeAdults,
      partyLabel: nextPartyLabel,
      minEstimatedRooms: roomEval.minEstimatedRooms,
      roomSuggestions: roomEval.suggestions,
    };
  },

  /**
   * Set children count and automatically resize kidAges vector (length === children) with default age 6.
   */
  setChildren(party: CanonicalParty, nextChildren: number, rules?: RoomingRule[]): CanonicalParty {
    const safeKids = Math.max(0, nextChildren);
    const lang = party.lang || "en";

    // Resizing kidAges vector
    const nextAges = [...party.kidAges];
    while (nextAges.length < safeKids) {
      nextAges.push(6);
    }
    const finalAges = nextAges.slice(0, safeKids);

    const prevAutoLabel = generatePartyLabel(party.adults, party.children, party.customerName, lang);
    const shouldUpdateLabel = !party.partyLabel || !party.isPartyLabelCustom || party.partyLabel === prevAutoLabel;
    const nextPartyLabel = shouldUpdateLabel
      ? generatePartyLabel(party.adults, safeKids, party.customerName, lang)
      : party.partyLabel;

    const roomEval = generateRoomSuggestions(party.adults, safeKids, finalAges, lang, rules);

    return {
      ...party,
      children: safeKids,
      kidAges: finalAges,
      partyLabel: nextPartyLabel,
      minEstimatedRooms: roomEval.minEstimatedRooms,
      roomSuggestions: roomEval.suggestions,
    };
  },

  /**
   * Set age of child at index (clamped between 0 and 17).
   */
  setKidAge(party: CanonicalParty, index: number, age: number, rules?: RoomingRule[]): CanonicalParty {
    if (index < 0 || index >= party.children) return party;

    const safeAge = Math.max(0, Math.min(17, isNaN(age) ? 6 : Math.round(age)));
    const nextAges = [...party.kidAges];
    while (nextAges.length < party.children) {
      nextAges.push(6);
    }
    nextAges[index] = safeAge;
    const finalAges = nextAges.slice(0, party.children);

    const lang = party.lang || "en";
    const roomEval = generateRoomSuggestions(party.adults, party.children, finalAges, lang, rules);

    return {
      ...party,
      kidAges: finalAges,
      minEstimatedRooms: roomEval.minEstimatedRooms,
      roomSuggestions: roomEval.suggestions,
    };
  },

  /**
   * Set infant count (clamped >= 0).
   */
  setInfants(party: CanonicalParty, nextInfants: number): CanonicalParty {
    const safeInfants = Math.max(0, nextInfants);
    const nextInfantAges = [...(party.infantAges || [])];
    while (nextInfantAges.length < safeInfants) {
      nextInfantAges.push(1);
    }
    return {
      ...party,
      infants: safeInfants,
      infantAges: nextInfantAges.slice(0, safeInfants),
    };
  },

  /**
   * Set customer name and automatically update partyLabel & greetingName if not manually customized.
   */
  setCustomerName(party: CanonicalParty, nextName: string | null): CanonicalParty {
    const name = nextName?.trim() || null;
    const lang = party.lang || "en";

    const prevAutoParty = generatePartyLabel(party.adults, party.children, party.customerName, lang);
    const prevAutoGreeting = inferGreetingName(party.customerName, lang);

    const isPartyDefaultOrBlank = !party.partyLabel || !party.isPartyLabelCustom || party.partyLabel === prevAutoParty;
    const isGreetingDefaultOrBlank = !party.greetingName || !party.isGreetingNameCustom || party.greetingName === prevAutoGreeting;

    const nextPartyLabel = isPartyDefaultOrBlank ? generatePartyLabel(party.adults, party.children, name, lang) : party.partyLabel;
    const nextGreetingName = isGreetingDefaultOrBlank ? inferGreetingName(name, lang) : party.greetingName;

    return {
      ...party,
      customerName: name,
      partyLabel: nextPartyLabel,
      greetingName: nextGreetingName,
    };
  },

  /**
   * Set custom party label.
   */
  setPartyLabel(party: CanonicalParty, label: string | null): CanonicalParty {
    const lang = party.lang || "en";
    const autoLabel = generatePartyLabel(party.adults, party.children, party.customerName, lang);
    const isCustom = Boolean(label && label !== autoLabel);

    return {
      ...party,
      partyLabel: label || null,
      isPartyLabelCustom: isCustom,
    };
  },

  /**
   * Set custom greeting name.
   */
  setGreetingName(party: CanonicalParty, greeting: string | null): CanonicalParty {
    const lang = party.lang || "en";
    const autoGreeting = inferGreetingName(party.customerName, lang);
    const isCustom = Boolean(greeting && greeting !== autoGreeting);

    return {
      ...party,
      greetingName: greeting || null,
      isGreetingNameCustom: isCustom,
    };
  },

  /**
   * Set room configuration.
   */
  setRoomConfiguration(party: CanonicalParty, config: string | null): CanonicalParty {
    return {
      ...party,
      roomConfiguration: config || null,
    };
  },

  /**
   * Set room notes & special requests.
   */
  setRoomNotes(party: CanonicalParty, notes: string | null): CanonicalParty {
    return {
      ...party,
      roomNotes: notes || null,
    };
  },

  /**
   * Perform single-pass reconciliation of all party invariants.
   */
  reconcileParty(party: Partial<CanonicalParty>, rules?: RoomingRule[]): CanonicalParty {
    const safeAdults = Math.max(1, party.adults ?? 2);
    const safeKids = Math.max(0, party.children ?? 0);
    const safeInfants = Math.max(0, party.infants ?? 0);
    const lang = party.lang || "en";

    // Reconcile kidAges array
    const rawAges = Array.isArray(party.kidAges) ? [...party.kidAges] : [];
    while (rawAges.length < safeKids) {
      rawAges.push(6);
    }
    const finalAges = rawAges.slice(0, safeKids).map((age) => Math.max(0, Math.min(17, isNaN(age) ? 6 : Math.round(age))));

    const customerName = party.customerName?.trim() || null;
    const partyLabel = party.partyLabel || generatePartyLabel(safeAdults, safeKids, customerName, lang);
    const greetingName = party.greetingName || inferGreetingName(customerName, lang);

    const roomEval = generateRoomSuggestions(safeAdults, safeKids, finalAges, lang, rules);

    return {
      customerName,
      clientName: party.clientName || null,
      role: party.role || "traveller",
      adults: safeAdults,
      children: safeKids,
      kidAges: finalAges,
      infants: safeInfants,
      infantAges: party.infantAges || [],
      partyLabel,
      greetingName,
      isPartyLabelCustom: party.isPartyLabelCustom ?? false,
      isGreetingNameCustom: party.isGreetingNameCustom ?? false,
      roomConfiguration: party.roomConfiguration || null,
      roomNotes: party.roomNotes || null,
      minEstimatedRooms: roomEval.minEstimatedRooms,
      roomSuggestions: roomEval.suggestions,
      travelStyle: party.travelStyle || null,
      market: party.market || null,
      nationality: party.nationality || null,
      lang,
    };
  },
};
