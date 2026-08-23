/**
 * Pure Domain Rules for Destination Taxonomy, Keyword Alias Matching, and GPS Resolution.
 *
 * Single Source of Truth for quote-generator, strictly synchronized with:
 * - Backend: core/rules/destination_rules.py
 * - Seed: destination_catalog_seed.py
 * - Profiles: destination_profiles.py
 *
 * 0 network calls, 0 database dependencies, 0 React dependencies.
 */

export interface ResolvedDestination {
  slug: string;
  canonicalName: string;
  country: string;
  region: string;
  province: string;
  coordinates: [number, number];
}

/** Normalize and strip Vietnamese / international diacritics */
export function removeDiacritics(text: string): string {
  if (!text) return '';
  return text
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/** Normalize input text for deterministic comparison */
export function normalizeDestinationText(text: string | null | undefined): string {
  if (!text) return '';
  const withoutDiacritics = removeDiacritics(text);
  const cleaned = withoutDiacritics.toLowerCase().replace(/[-_]+/g, ' ');
  return cleaned.split(/\s+/).filter(Boolean).join(' ');
}

/** Supported destination slugs (Vietnam provinces + Indochina / SE Asia gateways) */
export const VALID_DESTINATION_SLUGS: ReadonlySet<string> = new Set([
  // Vietnam
  'an-giang', 'ba-ria-vung-tau', 'bac-lieu', 'bac-kan', 'bac-giang', 'bac-ninh', 'ben-tre',
  'binh-duong', 'binh-dinh', 'binh-phuoc', 'binh-thuan', 'ca-mau', 'cao-bang', 'can-tho',
  'da-nang', 'dak-lak', 'dak-nong', 'dien-bien', 'dong-nai', 'dong-thap', 'gia-lai',
  'ha-giang', 'ha-nam', 'ha-noi', 'ha-tinh', 'hai-duong', 'hai-phong', 'hau-giang',
  'hoa-binh', 'hung-yen', 'khanh-hoa', 'kien-giang', 'kon-tum', 'lai-chau', 'lang-son',
  'lao-cai', 'lam-dong', 'long-an', 'mekong', 'nam-dinh', 'nghe-an', 'ninh-binh', 'ninh-thuan',
  'phu-tho', 'phu-yen', 'quang-binh', 'quang-nam', 'quang-ngai', 'quang-ninh', 'quang-tri',
  'soc-trang', 'son-la', 'tay-ninh', 'thai-binh', 'thai-nguyen', 'thanh-hoa', 'thua-thien-hue',
  'tien-giang', 'ho-chi-minh', 'tra-vinh', 'tuyen-quang', 'vinh-long', 'vinh-phuc', 'yen-bai',
  // Cambodia
  'siem-reap', 'phnom-penh',
  // Laos
  'luang-prabang', 'vientiane',
  // Thailand
  'bangkok', 'chiang-mai', 'phuket',
]);

/** Country to Primary Gateway slug mapping */
export const COUNTRY_GATEWAY_MAP: Readonly<Record<string, string>> = {
  vietnam: 'ha-noi',
  'viet nam': 'ha-noi',
  cambodia: 'siem-reap',
  campuchia: 'siem-reap',
  laos: 'luang-prabang',
  thailand: 'bangkok',
  'thai lan': 'bangkok',
};

/** Comprehensive dictionary mapping local landmarks, city names, diacritics, and aliases to destination slug */
export const DESTINATION_KEYWORD_MAP: Readonly<Record<string, string>> = {
  // ── Vietnam: Northern Gateways & Landmarks ─────────────────────────────────
  'ha noi': 'ha-noi',
  hanoi: 'ha-noi',
  'thu do': 'ha-noi',
  thudo: 'ha-noi',

  'quang ninh': 'quang-ninh',
  'ha long': 'quang-ninh',
  halong: 'quang-ninh',
  'halong bay': 'quang-ninh',
  'ha long bay': 'quang-ninh',
  'vinh ha long': 'quang-ninh',
  'lan ha': 'quang-ninh',
  'lan ha bay': 'quang-ninh',
  'cat ba': 'quang-ninh',
  'bai tu long': 'quang-ninh',

  'lao cai': 'lao-cai',
  laocai: 'lao-cai',
  sapa: 'lao-cai',
  'sa pa': 'lao-cai',
  fansipan: 'lao-cai',
  'phan xi pang': 'lao-cai',
  'bac ha': 'lao-cai',

  'ninh binh': 'ninh-binh',
  'trang an': 'ninh-binh',
  'tam coc': 'ninh-binh',
  'bich dong': 'ninh-binh',
  'hang mua': 'ninh-binh',

  'ha giang': 'ha-giang',
  'dong van': 'ha-giang',
  'meo vac': 'ha-giang',
  'ma pi leng': 'ha-giang',

  'cao bang': 'cao-bang',
  'ban gioc': 'cao-bang',
  'ban gioc waterfall': 'cao-bang',

  'yen bai': 'yen-bai',
  'mu cang chai': 'yen-bai',

  'hai phong': 'hai-phong',
  haiphong: 'hai-phong',
  'dien bien': 'dien-bien',
  'dien bien phu': 'dien-bien',
  'son la': 'son-la',
  'moc chau': 'son-la',
  'lai chau': 'lai-chau',
  'hoa binh': 'hoa-binh',
  'mai chau': 'hoa-binh',
  'lang son': 'lang-son',
  'bac kan': 'bac-kan',
  'ba be': 'bac-kan',

  // ── Vietnam: Central Region & Coast ───────────────────────────────────────
  'da nang': 'da-nang',
  danang: 'da-nang',
  'ba na': 'da-nang',
  'ba na hills': 'da-nang',

  'quang nam': 'quang-nam',
  'hoi an': 'quang-nam',
  hoian: 'quang-nam',
  'pho co hoi an': 'quang-nam',
  'hoi an ancient town': 'quang-nam',
  'my son': 'quang-nam',
  'cu lao cham': 'quang-nam',

  'thua thien hue': 'thua-thien-hue',
  hue: 'thua-thien-hue',
  'co do hue': 'thua-thien-hue',
  'lang co': 'thua-thien-hue',

  'quang binh': 'quang-binh',
  'phong nha': 'quang-binh',
  'ke bang': 'quang-binh',
  'son doong': 'quang-binh',

  'nghe an': 'nghe-an',
  'cua lo': 'nghe-an',
  'thanh hoa': 'thanh-hoa',
  'sam son': 'thanh-hoa',
  'quang tri': 'quang-tri',
  'quang ngai': 'quang-ngai',
  'ly son': 'quang-ngai',

  'binh dinh': 'binh-dinh',
  'quy nhon': 'binh-dinh',
  quynhon: 'binh-dinh',

  'phu yen': 'phu-yen',
  'tuy hoa': 'phu-yen',

  'khanh hoa': 'khanh-hoa',
  'nha trang': 'khanh-hoa',
  nhatrang: 'khanh-hoa',
  'cam ranh': 'khanh-hoa',

  'ninh thuan': 'ninh-thuan',
  'phan rang': 'ninh-thuan',
  'vinh hy': 'ninh-thuan',

  'binh thuan': 'binh-thuan',
  'mui ne': 'binh-thuan',
  muine: 'binh-thuan',
  'phan thiet': 'binh-thuan',

  // ── Vietnam: Central Highlands ────────────────────────────────────────────
  'lam dong': 'lam-dong',
  'da lat': 'lam-dong',
  dalat: 'lam-dong',

  'dak lak': 'dak-lak',
  daklak: 'dak-lak',
  'buon ma thuot': 'dak-lak',
  bmt: 'dak-lak',

  'gia lai': 'gia-lai',
  pleiku: 'gia-lai',
  'kon tum': 'kon-tum',
  kontum: 'kon-tum',
  'dak nong': 'dak-nong',

  // ── Vietnam: Southern Region & Mekong Delta ───────────────────────────────
  'ho chi minh': 'ho-chi-minh',
  hcm: 'ho-chi-minh',
  hcmc: 'ho-chi-minh',
  saigon: 'ho-chi-minh',
  'sai gon': 'ho-chi-minh',
  tphcm: 'ho-chi-minh',
  'tp hcm': 'ho-chi-minh',
  'ho chi minh city': 'ho-chi-minh',
  'cu chi': 'ho-chi-minh',

  'ba ria': 'ba-ria-vung-tau',
  'vung tau': 'ba-ria-vung-tau',
  vungtau: 'ba-ria-vung-tau',
  'con dao': 'ba-ria-vung-tau',

  'kien giang': 'kien-giang',
  'phu quoc': 'kien-giang',
  phuquoc: 'kien-giang',
  'ha tien': 'kien-giang',

  'can tho': 'can-tho',
  cantho: 'can-tho',
  'ben ninh kieu': 'can-tho',
  'cai rang': 'can-tho',

  mekong: 'mekong',
  'mekong delta': 'mekong',
  'dong bang song cuu long': 'mekong',
  'mien tay': 'mekong',
  'tay nam bo': 'mekong',

  'ben tre': 'ben-tre',
  'tien giang': 'tien-giang',
  'my tho': 'tien-giang',
  'dong thap': 'dong-thap',
  'sa dec': 'dong-thap',
  'vinh long': 'vinh-long',
  'an giang': 'an-giang',
  'chau doc': 'an-giang',
  'long xuyen': 'an-giang',
  'soc trang': 'soc-trang',
  'bac lieu': 'bac-lieu',
  'ca mau': 'ca-mau',
  'hau giang': 'hau-giang',
  'tra vinh': 'tra-vinh',
  'tay ninh': 'tay-ninh',
  'binh duong': 'binh-duong',
  'dong nai': 'dong-nai',
  'long an': 'long-an',
  'binh phuoc': 'binh-phuoc',

  // ── Cambodia ─────────────────────────────────────────────────────────────
  'siem reap': 'siem-reap',
  siemreap: 'siem-reap',
  angkor: 'siem-reap',
  'angkor wat': 'siem-reap',
  'angkor thom': 'siem-reap',
  'phnom penh': 'phnom-penh',
  phnompenh: 'phnom-penh',

  // ── Laos ─────────────────────────────────────────────────────────────────
  'luang prabang': 'luang-prabang',
  luangprabang: 'luang-prabang',
  vientiane: 'vientiane',

  // ── Thailand ─────────────────────────────────────────────────────────────
  bangkok: 'bangkok',
  'krung thep': 'bangkok',
  'chiang mai': 'chiang-mai',
  chiangmai: 'chiang-mai',
  phuket: 'phuket',
};

/** Base geographic profiles (canonical name, country, region, province) */
export const DESTINATION_BASE_PROFILES: Readonly<Record<string, { canonicalName: string; country: string; region: string; province: string }>> = {
  // Vietnam
  'ha-noi': { canonicalName: 'Hanoi', country: 'vietnam', region: 'north', province: 'ha-noi' },
  'ninh-binh': { canonicalName: 'Ninh Binh', country: 'vietnam', region: 'north', province: 'ninh-binh' },
  'quang-ninh': { canonicalName: 'Ha Long Bay', country: 'vietnam', region: 'north', province: 'quang-ninh' },
  'lao-cai': { canonicalName: 'Sapa', country: 'vietnam', region: 'north', province: 'lao-cai' },
  'da-nang': { canonicalName: 'Da Nang', country: 'vietnam', region: 'central', province: 'da-nang' },
  'quang-nam': { canonicalName: 'Hoi An', country: 'vietnam', region: 'central', province: 'quang-nam' },
  'thua-thien-hue': { canonicalName: 'Hue', country: 'vietnam', region: 'central', province: 'thua-thien-hue' },
  'khanh-hoa': { canonicalName: 'Nha Trang', country: 'vietnam', region: 'central', province: 'khanh-hoa' },
  'lam-dong': { canonicalName: 'Da Lat', country: 'vietnam', region: 'central-highlands', province: 'lam-dong' },
  'ho-chi-minh': { canonicalName: 'Ho Chi Minh City', country: 'vietnam', region: 'south', province: 'ho-chi-minh' },
  mekong: { canonicalName: 'Mekong Delta', country: 'vietnam', region: 'south', province: 'mekong' },
  'can-tho': { canonicalName: 'Can Tho', country: 'vietnam', region: 'south', province: 'can-tho' },
  'kien-giang': { canonicalName: 'Phu Quoc', country: 'vietnam', region: 'south', province: 'kien-giang' },
  'binh-thuan': { canonicalName: 'Mui Ne', country: 'vietnam', region: 'central', province: 'binh-thuan' },
  'quang-binh': { canonicalName: 'Phong Nha', country: 'vietnam', region: 'north-central', province: 'quang-binh' },
  'ha-giang': { canonicalName: 'Ha Giang', country: 'vietnam', region: 'north', province: 'ha-giang' },
  'cao-bang': { canonicalName: 'Cao Bang', country: 'vietnam', region: 'north', province: 'cao-bang' },
  'yen-bai': { canonicalName: 'Mu Cang Chai', country: 'vietnam', region: 'north', province: 'yen-bai' },
  'hai-phong': { canonicalName: 'Hai Phong', country: 'vietnam', region: 'north', province: 'hai-phong' },
  'binh-dinh': { canonicalName: 'Quy Nhon', country: 'vietnam', region: 'central', province: 'binh-dinh' },
  'phu-yen': { canonicalName: 'Phu Yen', country: 'vietnam', region: 'central', province: 'phu-yen' },
  'dak-lak': { canonicalName: 'Buon Ma Thuot', country: 'vietnam', region: 'central-highlands', province: 'dak-lak' },
  'ba-ria-vung-tau': { canonicalName: 'Vung Tau', country: 'vietnam', region: 'south', province: 'ba-ria-vung-tau' },
  // Cambodia
  'siem-reap': { canonicalName: 'Siem Reap', country: 'cambodia', region: 'northwest', province: 'siem-reap' },
  'phnom-penh': { canonicalName: 'Phnom Penh', country: 'cambodia', region: 'central', province: 'phnom-penh' },
  // Laos
  'luang-prabang': { canonicalName: 'Luang Prabang', country: 'laos', region: 'north', province: 'luang-prabang' },
  vientiane: { canonicalName: 'Vientiane', country: 'laos', region: 'central', province: 'vientiane' },
  // Thailand
  bangkok: { canonicalName: 'Bangkok', country: 'thailand', region: 'central', province: 'bangkok' },
  'chiang-mai': { canonicalName: 'Chiang Mai', country: 'thailand', region: 'north', province: 'chiang-mai' },
  phuket: { canonicalName: 'Phuket', country: 'thailand', region: 'south', province: 'phuket' },
};

/** Exact Baseline GPS Coordinates for each canonical destination slug */
export const BASELINE_DESTINATION_COORDINATES: Readonly<Record<string, [number, number]>> = {
  // Vietnam
  'ha-noi': [21.0285, 105.8542],
  'quang-ninh': [20.9599, 107.0436],
  'lao-cai': [22.3364, 103.8438],
  'da-nang': [16.0544, 108.2022],
  'quang-nam': [15.8801, 108.3380],
  'lam-dong': [11.9404, 108.4583],
  'ho-chi-minh': [10.8231, 106.6297],
  'khanh-hoa': [12.2388, 109.1967],
  'ninh-binh': [20.2539, 105.9750],
  'thua-thien-hue': [16.4637, 107.5909],
  'kien-giang': [10.2899, 103.9840],
  'binh-thuan': [10.9333, 108.1000],
  'can-tho': [10.0401, 105.7882],
  mekong: [10.2435, 106.3756],
  'ha-giang': [22.8233, 104.9836],
  'nghe-an': [18.6736, 105.6811],
  'quang-binh': [17.4833, 106.6000],
  'hai-phong': [20.8449, 106.6881],
  'dak-lak': [12.6667, 108.0500],
  'gia-lai': [13.9833, 108.0000],
  'kon-tum': [14.3500, 108.0000],
  'ba-ria-vung-tau': [10.4114, 107.1363],
  'thanh-hoa': [19.8075, 105.7764],
  'phu-yen': [13.0881, 109.3025],
  'binh-dinh': [13.7753, 109.2294],
  'dien-bien': [21.3833, 103.0167],
  'son-la': [21.3333, 103.9167],
  'lai-chau': [22.4000, 103.4500],
  'yen-bai': [21.7000, 104.8667],
  'hoa-binh': [20.8167, 105.3333],
  'lang-son': [21.8500, 106.7500],
  'dong-nai': [10.9574, 106.8427],
  'binh-duong': [11.0000, 106.6667],
  'tien-giang': [10.3592, 106.3653],
  'dong-thap': [10.4500, 105.6333],
  'vinh-long': [10.2500, 105.9667],
  'an-giang': [10.3833, 105.4333],
  'cao-bang': [22.6667, 106.2500],
  // Cambodia
  'siem-reap': [13.3671, 103.8448],
  'phnom-penh': [11.5564, 104.9282],
  // Laos
  'luang-prabang': [19.8893, 102.1336],
  vientiane: [17.9757, 102.6331],
  // Thailand
  bangkok: [13.7563, 100.5018],
  'chiang-mai': [18.7883, 98.9853],
  phuket: [7.8804, 98.3923],
};

/**
 * Deterministic Destination Slug Matcher (Ported directly from backend match_destination_slug)
 *
 * Resolution Strategy:
 * 1. If already a valid canonical slug (e.g. "ha-noi", "quang-ninh"), return it.
 * 2. Check Country Gateways (e.g. "vietnam" -> "ha-noi", "cambodia" -> "siem-reap").
 * 3. Check Exact match in DESTINATION_KEYWORD_MAP.
 * 4. Longest-match substring scan across DESTINATION_KEYWORD_MAP.
 * 5. Return null if no match found.
 */
export function matchDestinationSlug(location: string | null | undefined): string | null {
  if (!location || typeof location !== 'string') {
    return null;
  }

  const rawClean = location.trim().toLowerCase();
  const normalized = normalizeDestinationText(location);

  // 1. Direct valid slug check
  const slugCandidate = rawClean.replace(/\s+/g, '-');
  if (VALID_DESTINATION_SLUGS.has(slugCandidate)) {
    return slugCandidate;
  }
  if (VALID_DESTINATION_SLUGS.has(rawClean)) {
    return rawClean;
  }

  // 2. Country-level gateway mapping
  if (COUNTRY_GATEWAY_MAP[rawClean]) {
    return COUNTRY_GATEWAY_MAP[rawClean];
  }
  if (COUNTRY_GATEWAY_MAP[normalized]) {
    return COUNTRY_GATEWAY_MAP[normalized];
  }

  // 3. Exact match in keyword map
  if (DESTINATION_KEYWORD_MAP[rawClean]) {
    return DESTINATION_KEYWORD_MAP[rawClean];
  }
  if (DESTINATION_KEYWORD_MAP[normalized]) {
    return DESTINATION_KEYWORD_MAP[normalized];
  }

  // 4. Longest-match substring scan (prioritize specific landmarks over generic words)
  let bestMatch: string | null = null;
  let bestLen = 0;
  for (const [keyword, slug] of Object.entries(DESTINATION_KEYWORD_MAP)) {
    if ((rawClean.includes(keyword) || normalized.includes(keyword)) && keyword.length > bestLen) {
      bestMatch = slug;
      bestLen = keyword.length;
    }
  }

  if (bestMatch) {
    return bestMatch;
  }

  // 5. Check if any country keyword is inside the string
  for (const [countryKw, gatewaySlug] of Object.entries(COUNTRY_GATEWAY_MAP)) {
    if (rawClean.includes(countryKw) || normalized.includes(countryKw)) {
      return gatewaySlug;
    }
  }

  return null;
}

/**
 * Full 3-Layer Destination Resolver:
 * Resolves any raw location string into canonical metadata and verified GPS coordinates.
 */
export function resolveDestination(location: string | null | undefined): ResolvedDestination | null {
  const slug = matchDestinationSlug(location);
  if (!slug) return null;

  const profile = DESTINATION_BASE_PROFILES[slug];
  const coordinates = BASELINE_DESTINATION_COORDINATES[slug];

  if (!profile || !coordinates) {
    return null;
  }

  return {
    slug,
    canonicalName: profile.canonicalName,
    country: profile.country,
    region: profile.region,
    province: profile.province,
    coordinates,
  };
}
