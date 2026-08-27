import type { DestinationRef } from "./types.ts";

// Hardcoded against destination_catalog_seed.py's `dst_*` convention (15.2b §5.2 nợ ghi nhận —
// migrate to an API-backed "popular" list later; a test guard keeps this in sync meanwhile).
export const POPULAR_DESTINATIONS: DestinationRef[] = [
  { id: "dst_ho-chi-minh", name: "Ho Chi Minh City", slug: "ho-chi-minh" },
  { id: "dst_ha-noi", name: "Hanoi", slug: "ha-noi" },
  { id: "dst_ninh-binh", name: "Ninh Binh", slug: "ninh-binh" },
  { id: "dst_quang-nam", name: "Hoi An", slug: "quang-nam" },
  { id: "dst_quang-ninh", name: "Ha Long Bay", slug: "quang-ninh" },
  { id: "dst_thua-thien-hue", name: "Hue", slug: "thua-thien-hue" },
  { id: "dst_da-nang", name: "Da Nang", slug: "da-nang" },
  { id: "dst_lao-cai", name: "Sapa", slug: "lao-cai" },
  { id: "dst_mekong", name: "Mekong Delta", slug: "mekong" },
  { id: "dst_khanh-hoa", name: "Nha Trang", slug: "khanh-hoa" },
  { id: "dst_siem-reap", name: "Siem Reap", slug: "siem-reap" },
  { id: "dst_phnom-penh", name: "Phnom Penh", slug: "phnom-penh" },
  { id: "dst_luang-prabang", name: "Luang Prabang", slug: "luang-prabang" },
  { id: "dst_vientiane", name: "Vientiane", slug: "vientiane" },
  { id: "dst_bangkok", name: "Bangkok", slug: "bangkok" },
  { id: "dst_chiang-mai", name: "Chiang Mai", slug: "chiang-mai" },
  { id: "dst_phuket", name: "Phuket", slug: "phuket" },
];
