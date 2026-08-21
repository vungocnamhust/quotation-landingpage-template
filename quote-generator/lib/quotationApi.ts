// Production editor requests stay same-origin behind quote.capellatravel.com.
// Local development opts into a separate API origin through .env.local.
import { quotationFetch } from './apiError.ts';
export const QUOTATION_API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export type TravelDesignerProfile = {
  id: string;
  name: string;
  email: string;
  phone: string;
  imageAssetId?: string | null;
  imageUrl?: string | null;
  imageR2Key?: string | null;
  isActive: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type TravelDesignerListResponse = { items: TravelDesignerProfile[] };

export type AccommodationProfile = {
  id: string;
  destination_id: string;
  destination: string;
  destination_ref: { id: string; name: string; slug: string } | null;
  storage_slug: string;
  asset_prefix: string;
  name: string;
  room_type: string | null;
  intro: string | null;
  phone: string | null;
  display_city: string | null;
  display_date: string | null;
  hotel_asset: string | null;
  room_asset: string | null;
  is_active: boolean;
};

export type AccommodationProfileInput = {
  destinationId: string;
  name: string;
  room_type: string | null;
  intro: string | null;
  phone: string | null;
  display_city: string | null;
  display_date: string | null;
  hotel_asset: string | null;
  room_asset: string | null;
};
export type AccommodationListResponse = { items: AccommodationProfile[] };

export type TravelDesignerInput = {
  name: string;
  email: string;
  phone: string;
  imageAssetId?: string | null;
  imageUrl?: string | null;
  imageR2Key?: string | null;
};

function apiUrl(path: string) {
  return `${QUOTATION_API_BASE}${path}`;
}

function request<T>(path: string, init?: RequestInit) {
  return quotationFetch<T>(apiUrl(path), init, 'The quotation API request could not be completed.');
}

export async function listTravelDesigners({
  active = 'true',
  search = '',
}: {
  active?: 'true' | 'false' | 'all';
  search?: string;
} = {}): Promise<TravelDesignerListResponse> {
  const params = new URLSearchParams({ active });
  if (search.trim()) params.set('search', search.trim());
  return request<TravelDesignerListResponse>(`/api/v2/travel-designers?${params.toString()}`);
}

export async function createTravelDesigner(input: TravelDesignerInput): Promise<TravelDesignerProfile> {
  return request<TravelDesignerProfile>('/api/v2/travel-designers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateTravelDesigner(id: string, input: TravelDesignerInput): Promise<TravelDesignerProfile> {
  return request<TravelDesignerProfile>(`/api/v2/travel-designers/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateTravelDesignerStatus(id: string, isActive: boolean): Promise<TravelDesignerProfile> {
  return request<TravelDesignerProfile>(`/api/v2/travel-designers/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isActive }),
  });
}

export async function setTravelDesignerDefault(brandId: string, designerProfileId: string) {
  return request<{ brandId: string; designer: TravelDesignerProfile }>(`/api/v2/brands/${encodeURIComponent(brandId)}/travel-designer-default`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ designerProfileId }),
  });
}

export async function uploadTravelDesignerPortrait(file: File, travelDesignerId: string): Promise<{ r2Key: string }> {
  const form = new FormData();
  form.append('file', file);
  form.append('kind', 'team');
  form.append('travelDesignerId', travelDesignerId);
  return request<{ r2Key: string }>('/api/v2/media-library/uploads', {
    method: 'POST',
    body: form,
  });
}

export async function assignTravelDesigner({
  quotationId,
  designerProfileId,
  baseRevision,
  lang,
}: {
  quotationId: string;
  designerProfileId: string | null;
  baseRevision: number;
  lang: string;
}) {
  return request<{ currentRevision: number }>(`/api/v2/quotations/${encodeURIComponent(quotationId)}/travel-designer`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ designerProfileId, baseRevision, lang }),
  });
}

export async function listAccommodations({
  active = "true",
  query = "",
  destinationId,
  destination,
}: {
  active?: "true" | "false" | "all";
  query?: string;
  destinationId?: string;
  destination?: string;
} = {}): Promise<AccommodationListResponse> {
  const params = new URLSearchParams({ active });
  if (query.trim()) params.set("query", query.trim());
  if (destinationId) params.set("destinationId", destinationId);
  if (destination && !destinationId) params.set("destination", destination);
  return request<AccommodationListResponse>(`/api/v2/accommodations?${params.toString()}`);
}

export async function createAccommodation(input: AccommodationProfileInput): Promise<AccommodationProfile> {
  return request<AccommodationProfile>("/api/v2/accommodations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
}

export async function updateAccommodation(id: string, input: AccommodationProfileInput): Promise<AccommodationProfile> {
  return request<AccommodationProfile>(`/api/v2/accommodations/${encodeURIComponent(id)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
}

export async function updateAccommodationStatus(id: string, isActive: boolean): Promise<AccommodationProfile> {
  return request<AccommodationProfile>(`/api/v2/accommodations/${encodeURIComponent(id)}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ isActive }) });
}

export async function uploadAccommodationAsset(file: File, accommodationId: string, category: "exteriors" | "interiors"): Promise<{ r2Key: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("kind", "accommodation");
  form.append("accommodationId", accommodationId);
  form.append("accommodationAssetCategory", category);
  return request<{ r2Key: string }>("/api/v2/media-library/uploads", { method: "POST", body: form });
}

export type TravelStyleTagItem = {
  id: string;
  category: string;
  name_en: string;
  name_vi: string;
  slug: string;
  display_order: number;
};

export type TravelStyleCategoryGroup = {
  category_id: string;
  title_en: string;
  title_vi: string;
  tags: TravelStyleTagItem[];
};

export type TravelStyleResponse = {
  categories: TravelStyleCategoryGroup[];
};

export async function listTravelStyles(): Promise<TravelStyleResponse> {
  return request<TravelStyleResponse>("/api/v2/travel-styles");
}

export type PartnerProfile = {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  market?: string | null;
  tier?: string | null;
  default_commission_rate: number;
  preferred_currency: string;
  notes?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type PartnerInput = {
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  market?: string | null;
  tier?: string | null;
  default_commission_rate?: number;
  preferred_currency?: string;
  notes?: string | null;
  is_active?: boolean;
};

export type PartnerListResponse = {
  items: PartnerProfile[];
  total: number;
};

export async function listPartners({
  active = 'true',
  search = '',
}: {
  active?: 'true' | 'false' | 'all';
  search?: string;
} = {}): Promise<PartnerListResponse> {
  const params = new URLSearchParams({ active });
  if (search.trim()) params.set('search', search.trim());
  return request<PartnerListResponse>(`/api/v2/partners?${params.toString()}`);
}

export async function createPartner(input: PartnerInput): Promise<PartnerProfile> {
  return request<PartnerProfile>('/api/v2/partners', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updatePartner(id: string, input: PartnerInput): Promise<PartnerProfile> {
  return request<PartnerProfile>(`/api/v2/partners/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updatePartnerStatus(id: string, isActive: boolean): Promise<PartnerProfile> {
  return request<PartnerProfile>(`/api/v2/partners/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isActive }),
  });
}

export type RoomingHeuristicRuleItem = {
  id: string;
  name: string;
  description?: string | null;
  min_adults: number;
  max_adults?: number | null;
  min_children: number;
  max_children?: number | null;
  min_infants?: number;
  max_infants?: number | null;
  kid_age_condition?: "ANY" | "ALL_UNDER_12" | "ANY_12_AND_ABOVE" | "NO_KIDS";
  suggestions: Array<{
    en: string;
    vi?: string | null;
    ar?: string | null;
    code?: string | null;
  }>;
  min_rooms_formula?: string | null;
  priority?: number;
  is_active?: boolean;
};

export type RoomingHeuristicsListResponse = {
  items: RoomingHeuristicRuleItem[];
  total: number;
};

export async function listRoomingHeuristics(): Promise<RoomingHeuristicsListResponse> {
  return request<RoomingHeuristicsListResponse>('/api/v2/rooming-heuristics');
}

export type DestinationProfile = {
  id: string;
  name: string;
  slug: string;
  countrySlug: string | null;
  regionSlug: string | null;
  provinceSlug: string | null;
  latitude: number | null;
  longitude: number | null;
  isActive: boolean;
  aliases: string[];
  matchedFrom?: string;
};

export type DestinationCatalogInput = {
  canonicalName: string;
  slug: string;
  countrySlug: string | null;
  regionSlug: string | null;
  provinceSlug: string | null;
  latitude: number;
  longitude: number;
  aliases: string[];
};

export type DestinationListResponse = {
  items: DestinationProfile[];
};

export async function listDestinationsCatalog({
  active = "true",
  query = "",
  countrySlug,
  limit = 100,
}: {
  active?: "true" | "false" | "all";
  query?: string;
  countrySlug?: string;
  limit?: number;
} = {}): Promise<DestinationListResponse> {
  const params = new URLSearchParams({ active });
  if (query.trim()) params.set("query", query.trim());
  if (countrySlug) params.set("countrySlug", countrySlug);
  if (limit) params.set("limit", String(limit));
  return request<DestinationListResponse>(`/api/v2/destinations?${params.toString()}`);
}

export async function getDestination(id: string): Promise<DestinationProfile> {
  return request<DestinationProfile>(`/api/v2/destinations/${encodeURIComponent(id)}`);
}

export async function createDestination(input: DestinationCatalogInput): Promise<DestinationProfile> {
  return request<DestinationProfile>("/api/v2/destinations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function updateDestination(id: string, input: DestinationCatalogInput): Promise<DestinationProfile> {
  return request<DestinationProfile>(`/api/v2/destinations/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function updateDestinationStatus(id: string, isActive: boolean): Promise<DestinationProfile> {
  return request<DestinationProfile>(`/api/v2/destinations/${encodeURIComponent(id)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ isActive }),
  });
}



