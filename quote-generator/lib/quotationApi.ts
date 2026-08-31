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
  /** Free-form calligraphy characters rendered via the handwriting font (e.g. "Nam H.", "V"). */
  signatureInitial?: string | null;
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
  /** Free-form calligraphy characters for the handwritten signature glyph. */
  signatureInitial?: string | null;
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

export type SupplierType = 'direct' | 'dmc' | 'wholesaler' | 'bedbank' | 'ota' | 'freelancer' | 'gov' | 'other';
export type SupplierPreferredStatus = 'preferred' | 'recommended' | 'standard' | 'backup' | 'do_not_use';
export type SupplierQualityTier = 'ultra_luxury' | 'luxury' | 'premium' | 'standard' | 'value';
export type SupplierPaymentMethod = 'bank_transfer' | 'cash' | 'card' | 'other';

export type SupplierContact = {
  person?: string | null;
  email?: string | null;
  phone?: string | null;
  whatsapp?: string | null;
  zalo?: string | null;
  website?: string | null;
};

export type SupplierPaymentTerms = {
  deposit_percent?: number | null;
  deposit_due_days_after_confirm?: number | null;
  balance_due_days_before_service?: number | null;
  method?: SupplierPaymentMethod | null;
  note?: string | null;
};

export type SupplierCancellationTier = {
  days_before_service_min: number;
  penalty_percent: number;
};

export type SupplierCancellationPolicy = {
  tiers: SupplierCancellationTier[];
  no_show_penalty_percent: number;
  note?: string | null;
};

export type SupplierChildAgeBand = {
  age_min: number;
  age_max: number;
  charge_percent: number;
};

export type SupplierChildPolicy = {
  bands: SupplierChildAgeBand[];
  infant_age_max?: number | null;
  note?: string | null;
};

export type SupplierProfile = {
  id: string;
  name: string;
  legal_name?: string | null;
  supplier_type: SupplierType;
  country?: string | null;
  city?: string | null;
  destination_id?: string | null;
  default_currency: string;
  preferred_status: SupplierPreferredStatus;
  quality_tier?: SupplierQualityTier | null;
  contact_json: SupplierContact;
  payment_terms_json?: SupplierPaymentTerms | null;
  cancellation_policy_json?: SupplierCancellationPolicy | null;
  child_policy_json?: SupplierChildPolicy | null;
  bank_details_ref?: string | null;
  tax_code?: string | null;
  credit_terms_days: number;
  internal_notes?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type SupplierInput = {
  name: string;
  legal_name?: string | null;
  supplier_type: SupplierType;
  country?: string | null;
  city?: string | null;
  destination_id?: string | null;
  default_currency: string;
  preferred_status?: SupplierPreferredStatus;
  quality_tier?: SupplierQualityTier | null;
  contact_json?: SupplierContact;
  payment_terms_json?: SupplierPaymentTerms | null;
  cancellation_policy_json?: SupplierCancellationPolicy | null;
  child_policy_json?: SupplierChildPolicy | null;
  bank_details_ref?: string | null;
  tax_code?: string | null;
  credit_terms_days?: number;
  internal_notes?: string | null;
  is_active?: boolean;
};

export type SupplierListResponse = {
  items: SupplierProfile[];
  total: number;
};

export async function listSuppliers({
  active = 'true',
  search = '',
  supplierType,
  destinationId,
}: {
  active?: 'true' | 'false' | 'all';
  search?: string;
  supplierType?: string;
  destinationId?: string;
} = {}): Promise<SupplierListResponse> {
  const params = new URLSearchParams({ active });
  if (search.trim()) params.set('search', search.trim());
  if (supplierType) params.set('supplier_type', supplierType);
  if (destinationId) params.set('destination_id', destinationId);
  return request<SupplierListResponse>(`/api/v2/suppliers?${params.toString()}`);
}

export async function createSupplier(input: SupplierInput): Promise<SupplierProfile> {
  return request<SupplierProfile>('/api/v2/suppliers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateSupplier(id: string, input: Partial<SupplierInput>): Promise<SupplierProfile> {
  return request<SupplierProfile>(`/api/v2/suppliers/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateSupplierStatus(id: string, isActive: boolean): Promise<SupplierProfile> {
  return request<SupplierProfile>(`/api/v2/suppliers/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isActive }),
  });
}

// Mirrors core/rules/catalog_vocab.py — keep both in sync (15.2).
export type ProductCategory =
  | 'accommodation'
  | 'transportation'
  | 'ticket'
  | 'flights'
  | 'guide'
  | 'guide_expense'
  | 'experience'
  | 'meal'
  | 'visa'
  | 'others';

export type ProductChargeUnit = 'room' | 'person' | 'vehicle' | 'group' | 'ticket' | 'flight_seat' | 'visa_case' | 'set';
export type ProductTimeBasis = 'night' | 'day' | 'trip';
export type ProductCategoryAttributeValue = string | number | boolean;

export type ProductProfile = {
  id: string;
  supplier_id?: string | null;
  property_id?: string | null;
  destination_id: string;
  origin_destination_id?: string | null;
  category: ProductCategory;
  subcategory?: string | null;
  subcategory_note?: string | null;
  supplier_product_name?: string | null;
  title: string;
  unit: ProductChargeUnit;
  time_basis: ProductTimeBasis;
  default_min_pax?: number | null;
  default_max_pax?: number | null;
  category_attributes: Record<string, ProductCategoryAttributeValue>;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ProductInput = {
  supplier_id?: string | null;
  property_id?: string | null;
  destination_id: string;
  origin_destination_id?: string | null;
  category: ProductCategory;
  subcategory?: string | null;
  subcategory_note?: string | null;
  supplier_product_name?: string | null;
  title: string;
  unit?: ProductChargeUnit | null;
  time_basis?: ProductTimeBasis | null;
  default_min_pax?: number | null;
  default_max_pax?: number | null;
  category_attributes?: Record<string, ProductCategoryAttributeValue>;
  is_active?: boolean;
};

export type ProductListResponse = {
  items: ProductProfile[];
  total: number;
};

export async function listProducts({
  active = 'true',
  category,
  destinationId,
  supplierId,
  propertyId,
  search = '',
  limit,
}: {
  active?: 'true' | 'false' | 'all';
  category?: string;
  destinationId?: string;
  supplierId?: string;
  propertyId?: string;
  search?: string;
  limit?: number;
} = {}): Promise<ProductListResponse> {
  const params = new URLSearchParams({ active });
  if (category) params.set('category', category);
  if (destinationId) params.set('destination_id', destinationId);
  if (supplierId) params.set('supplier_id', supplierId);
  if (propertyId) params.set('property_id', propertyId);
  if (search.trim()) params.set('search', search.trim());
  if (limit) params.set('limit', String(limit));
  return request<ProductListResponse>(`/api/v2/products?${params.toString()}`);
}

export async function createProduct(input: ProductInput): Promise<ProductProfile> {
  return request<ProductProfile>('/api/v2/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateProduct(id: string, input: Partial<ProductInput>): Promise<ProductProfile> {
  return request<ProductProfile>(`/api/v2/products/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function updateProductStatus(id: string, isActive: boolean): Promise<ProductProfile> {
  return request<ProductProfile>(`/api/v2/products/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isActive }),
  });
}

// ---------------------------------------------------------------------------
// Rates (15.3) — mirrors core/rules/catalog_vocab.py + schemas/v2/rate.py
// ---------------------------------------------------------------------------

export type RateOccupancyBasis = 'sgl' | 'dbl' | 'twn' | 'trpl' | 'quad' | 'na';
export type RatePriceFor = 'adult' | 'child' | 'infant' | 'room' | 'vehicle' | 'guide' | 'group' | 'unit';
export type RateBasis = 'net' | 'gross_commissionable';
export type RateLifecycleStatus = 'draft' | 'active' | 'superseded' | 'expired';
export type RateReviewStatus = 'needs_review' | 'verified';
export type RateDocumentType = 'rate_sheet' | 'contract' | 'amendment' | 'quotation' | 'promotion' | 'manual_note';
export type RateChannel = 'email' | 'zalo' | 'whatsapp' | 'portal' | 'in_person' | 'internal';

export type RateBlackoutWindow = {
  from: string;
  to: string;
  reason?: string;
};

export type RateSupplement = {
  label: string;
  applies_from: string;
  applies_to: string;
  amount_minor: number;
  price_for: RatePriceFor;
  mandatory: boolean;
  note?: string | null;
};

export type RatePriceLine = {
  id?: number;
  price_for: RatePriceFor;
  occupancy_basis: RateOccupancyBasis;
  unit: ProductChargeUnit;
  tier_min_pax?: number | null;
  tier_max_pax?: number | null;
  amount_minor: number;
  note?: string | null;
  sort_order?: number;
};

export type RateSourceInput = {
  supplier_id: string;
  document_type?: RateDocumentType;
  channel?: RateChannel;
  file_ref?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  received_at?: string | null;
  notes?: string | null;
};

export type RateSource = RateSourceInput & { id: string };

export type RateAggregateInput = {
  product_id?: string;
  currency?: string | null;
  rate_basis: RateBasis;
  commission_pct?: number | null;
  valid_from: string;
  valid_to: string;
  season_name?: string | null;
  blackout_json?: RateBlackoutWindow[];
  min_pax?: number | null;
  max_pax?: number | null;
  tax_included?: boolean;
  tax_pct?: number | null;
  supplements_json?: RateSupplement[];
  inclusions_json?: string[];
  exclusions_json?: string[];
  payment_terms_json?: SupplierPaymentTerms | null;
  cancellation_policy_json?: SupplierCancellationPolicy | null;
  child_policy_json?: SupplierChildPolicy | null;
  source_reference?: string | null;
  source_id?: string | null;
  source?: RateSourceInput | null;
  lines: RatePriceLine[];
};

export type RateProfile = {
  id: string;
  product_id: string;
  currency: string;
  rate_basis: RateBasis;
  commission_pct?: number | null;
  valid_from: string;
  valid_to: string;
  season_name?: string | null;
  blackout_json: RateBlackoutWindow[];
  min_pax?: number | null;
  max_pax?: number | null;
  tax_included: boolean;
  tax_pct?: number | null;
  supplements_json: RateSupplement[];
  inclusions_json: string[];
  exclusions_json: string[];
  payment_terms_json?: SupplierPaymentTerms | null;
  cancellation_policy_json?: SupplierCancellationPolicy | null;
  child_policy_json?: SupplierChildPolicy | null;
  version: number;
  supersedes_rate_id?: string | null;
  lifecycle_status: RateLifecycleStatus;
  review_status: RateReviewStatus;
  validation_flags_json: string[];
  source_id?: string | null;
  source_reference?: string | null;
  created_at: string;
  updated_at: string;
  lines: RatePriceLine[];
  source?: RateSource | null;
  resolved_payment_terms_json?: SupplierPaymentTerms | null;
  resolved_cancellation_policy_json?: SupplierCancellationPolicy | null;
  resolved_child_policy_json?: SupplierChildPolicy | null;
  inherited_from_supplier: Record<string, boolean>;
};

export type RateListResponse = {
  items: RateProfile[];
  total: number;
};

export async function listProductRates(
  productId: string,
  {
    lifecycle = 'active',
    onDate,
    limit,
  }: { lifecycle?: RateLifecycleStatus | 'all'; onDate?: string; limit?: number } = {},
): Promise<RateListResponse> {
  const params = new URLSearchParams({ lifecycle });
  if (onDate) params.set('on_date', onDate);
  if (limit) params.set('limit', String(limit));
  return request<RateListResponse>(`/api/v2/products/${encodeURIComponent(productId)}/rates?${params.toString()}`);
}

export async function createRate(productId: string, input: RateAggregateInput): Promise<RateProfile> {
  return request<RateProfile>(`/api/v2/products/${encodeURIComponent(productId)}/rates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function getRate(rateId: string): Promise<RateProfile> {
  return request<RateProfile>(`/api/v2/rates/${encodeURIComponent(rateId)}`);
}

export async function updateRate(rateId: string, input: RateAggregateInput): Promise<RateProfile> {
  return request<RateProfile>(`/api/v2/rates/${encodeURIComponent(rateId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function activateRate(rateId: string): Promise<RateProfile> {
  return request<RateProfile>(`/api/v2/rates/${encodeURIComponent(rateId)}/activate`, { method: 'POST' });
}

export async function supersedeRate(rateId: string, input: RateAggregateInput): Promise<RateProfile> {
  return request<RateProfile>(`/api/v2/rates/${encodeURIComponent(rateId)}/supersede`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function deleteDraftRate(rateId: string): Promise<void> {
  await request<void>(`/api/v2/rates/${encodeURIComponent(rateId)}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Costing Sheets (15.4) — mirrors schemas/v2/costing.py + core/rules/costing_rules.py.
// Dual-track workbench: a sheet anchors to a quote_request, a quotation, or both
// after attach. Every write carries base_costing_revision (CAS); the server
// response always includes the fresh costing_revision + summary — never
// recompute totals client-side from raw lines (see costingReconciler.ts).
// ---------------------------------------------------------------------------

// Mirror of schemas/v2/costing.py BookingStatus — keep the 7 values in sync (16.3 F-16).
export type BookingStatus =
  | 'quoted'
  | 'on_hold'
  | 'to_request'
  | 'requested'
  | 'confirmed'
  | 'delivered'
  | 'cancelled';
export type ServiceLineSource = 'manual' | 'ai_draft';

// AI Drafter (15.7) flags carried on a line's ai_meta_json — kept here (not in the AI
// section below) so ServiceLineProfile doesn't need a forward reference.
export type ServiceLineAiFlag = 'rate_missing' | 'rate_conflict' | 'has_supplement_in_range' | 'needs_manual';

export type ServiceLineAiMeta = {
  reason: string;
  run_id: string;
  day_number: number | null;
  flags: ServiceLineAiFlag[];
};

export type ProductRef = {
  property_id?: string | null;
  destination_id?: string | null;
  destination_name?: string | null;
  iata_code?: string | null;
};

export type ServiceLineProfile = {
  id: string;
  sheet_id: string;
  day_number: number | null;
  service_date: string | null;
  category: string;
  subcategory: string | null;
  title: string;
  supplier_id: string | null;
  product_id: string | null;
  // Deliberately named `tariff_id` on the wire, not `rate_id` — mirrors the
  // backend's frozen #D0 LLM output contract (schemas/v2/costing.py, 16.3
  // F-27). Don't rename this field; consume it via costingAdapter.ts's
  // `rateId` bridge instead.
  tariff_id: string | null;
  price_line_id: number | null;
  unit: string;
  time_basis: string;
  qty_unit: number;
  qty_time: number;
  unit_cost_minor: number;
  cost_currency: string;
  fx_rate_ppm: number | null;
  sell_override_minor: number | null;
  booking_status: BookingStatus;
  source: ServiceLineSource;
  ai_meta_json: ServiceLineAiMeta | null;
  note: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
  cost_minor: number;
  sell_minor: number;
  product_ref: ProductRef | null;
};

export type ServiceLineWriteInput = {
  base_costing_revision: number;
  day_number?: number | null;
  service_date?: string | null;
  category?: string | null;
  subcategory?: string | null;
  title?: string | null;
  supplier_id?: string | null;
  product_id?: string | null;
  rate_id?: string | null;
  price_line_id?: number | null;
  unit?: string | null;
  time_basis?: string | null;
  qty_unit?: number;
  qty_time?: number;
  unit_cost_minor?: number | null;
  cost_currency?: string | null;
  fx_rate_ppm?: number | null;
  sell_override_minor?: number | null;
  note?: string | null;
  sort_order?: number;
};

export type CostingDayTotal = { day_number: number | null; cost_minor: number; sell_minor: number };
export type CostingCategoryTotal = { category: string; cost_minor: number; sell_minor: number };

export type CostingSummary = {
  cost_total_minor: number;
  sell_total_minor: number;
  margin_minor: number;
  margin_bps: number;
  by_day: CostingDayTotal[];
  by_category: CostingCategoryTotal[];
};

export type CostingSheetProfile = {
  id: string;
  quote_request_id: string | null;
  quotation_id: string | null;
  currency: string;
  markup_rate_bps: number;
  rounding_increment_minor: number;
  costing_revision: number;
  created_at: string;
  updated_at: string;
};

export type CostingApplicationProfile = {
  id: string;
  sheet_id: string;
  quotation_id: string;
  costing_revision_at_apply: number;
  facts_revision_after: number;
  target_option_id: string;
  sell_total_minor: number;
  currency: string;
  cost_total_minor: number;
  margin_bps: number;
  idempotency_key?: string | null;
  created_by?: string | null;
  created_at: string;
};

export type CostingDriftProfile = {
  has_drift: boolean;
  costing_modified_since_apply?: boolean;
  commercial_modified_since_apply?: boolean;
  last_applied_at?: string | null;
  last_applied_costing_revision?: number | null;
  last_applied_facts_revision?: number | null;
  last_applied_sell_total_minor?: number | null;
  last_applied_currency?: string | null;
  target_option_id?: string | null;
  target_option_label?: string | null;
};

export type CostingWorkbenchResponse = {
  sheet: CostingSheetProfile;
  items: ServiceLineProfile[];
  summary: CostingSummary;
  applications?: CostingApplicationProfile[];
  drift?: CostingDriftProfile | null;
};

export type ApplyPricingRequestPayload = {
  base_revision: number;
  base_costing_revision: number;
  target_option_id?: string | null;
  option_label?: string | null;
  lang?: string | null;
};

export type ApplyPricingResponse = {
  application: CostingApplicationProfile;
  facts_revision: number;
  costing_revision: number;
  summary: CostingSummary;
  pricing_options: Array<{
    id: string;
    label?: string;
    currency?: string;
    group_total_amount_minor?: number;
    per_adult_amount_minor?: number;
    per_traveler_amount_minor?: number;
  }>;
  drift?: CostingDriftProfile | null;
};

export async function createCostingSheet(input: {
  request_id?: string;
  quotation_id?: string;
  currency?: string;
}): Promise<CostingSheetProfile> {
  return request<CostingSheetProfile>('/api/v2/costing-sheets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function findCostingSheetByRequest(requestId: string): Promise<CostingSheetProfile | null> {
  const params = new URLSearchParams({ requestId });
  const result = await request<{ sheet: CostingSheetProfile | null }>(`/api/v2/costing-sheets?${params.toString()}`);
  return result.sheet;
}

export async function findCostingSheetByQuotation(quotationId: string): Promise<CostingSheetProfile | null> {
  const params = new URLSearchParams({ quotationId });
  const result = await request<{ sheet: CostingSheetProfile | null }>(`/api/v2/costing-sheets?${params.toString()}`);
  return result.sheet;
}

export async function getCostingWorkbench(sheetId: string): Promise<CostingWorkbenchResponse> {
  return request<CostingWorkbenchResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}`);
}

export async function updateCostingSettings(
  sheetId: string,
  input: { base_costing_revision: number; currency?: string; markup_rate_bps?: number; rounding_increment_minor?: number },
): Promise<CostingWorkbenchResponse> {
  return request<CostingWorkbenchResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function attachCostingSheetToQuotation(
  sheetId: string,
  quotationId: string,
  idempotencyKey: string,
): Promise<CostingWorkbenchResponse> {
  return request<CostingWorkbenchResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/attach-quotation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ quotation_id: quotationId }),
  });
}

export async function createServiceLine(
  sheetId: string,
  input: ServiceLineWriteInput,
  idempotencyKey: string,
): Promise<CostingWorkbenchResponse> {
  return request<CostingWorkbenchResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/lines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(input),
  });
}

export async function updateServiceLine(
  sheetId: string,
  lineId: string,
  input: ServiceLineWriteInput,
): Promise<CostingWorkbenchResponse> {
  return request<CostingWorkbenchResponse>(
    `/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/lines/${encodeURIComponent(lineId)}`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) },
  );
}

export async function deleteServiceLine(
  sheetId: string,
  lineId: string,
  baseCostingRevision: number,
): Promise<CostingWorkbenchResponse> {
  const params = new URLSearchParams({ base_costing_revision: String(baseCostingRevision) });
  return request<CostingWorkbenchResponse>(
    `/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/lines/${encodeURIComponent(lineId)}?${params.toString()}`,
    { method: 'DELETE' },
  );
}

export async function applyCostingPricing(
  sheetId: string,
  input: ApplyPricingRequestPayload,
  idempotencyKey?: string,
): Promise<ApplyPricingResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  return request<ApplyPricingResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/apply-pricing`, {
    method: 'POST',
    headers,
    body: JSON.stringify(input),
  });
}

// ---------------------------------------------------------------------------
// AI Service Drafter (15.7) — mirrors schemas/v2/ai_drafter.py + schemas/trip_profile.py +
// schemas/service_draft.py. TripAnalyst (0 tools, prose -> TripProfile, human-reviewed) then
// ServiceDrafter (per-day catalog agent, zero-money output — no field here ever names an
// amount/price/currency; price resolution is server-side only via core/rules/rate_selection).
// Request bodies alias to camelCase (ConfigDict(populate_by_name=True) on the Pydantic side);
// TripProfile itself has no aliasing, so its fields stay snake_case on the wire either way.
// Response bodies stay snake_case.
// ---------------------------------------------------------------------------

export type TripArchetype =
  | 'solo'
  | 'couple'
  | 'honeymoon'
  | 'family_with_young_kids'
  | 'family_with_teens'
  | 'multi_generation'
  | 'friends_group'
  | 'corporate_incentive';

export type TripPace = 'relaxed' | 'moderate' | 'packed';
export type TripMobility = 'full' | 'limited' | 'wheelchair';
export type TripQualityTier = 'ultra_luxury' | 'luxury' | 'premium' | 'standard' | 'value';

export type PartyComposition = {
  adults: number;
  children: number;
  infants: number;
  child_ages: number[];
};

export type RoomAllocation = {
  room_type: string;
  count: number;
  extra_bed: boolean;
  occupants_note?: string | null;
};

export type TripProfile = {
  archetype: TripArchetype;
  party: PartyComposition;
  room_config: RoomAllocation[];
  mobility: TripMobility;
  pace: TripPace;
  dietary: string[];
  quality_tier: TripQualityTier;
  guide_need: boolean;
  guide_languages: string[];
  // Verbatim excerpts from the customer's prose — never the model's own paraphrase.
  special_flags: string[];
  // Things the model is NOT sure about — render in red; sale confirms before Draft can run.
  confidence_notes: string[];
};

export type ServiceDraftFlag = ServiceLineAiFlag;

export type ServiceDraft = {
  category: string;
  subcategory: string | null;
  product_id: string;
  occupancy_basis: string;
  price_for: string;
  pax_count: number;
  qty_unit: number;
  qty_time: number;
  selection_reason: string;
  flags: ServiceDraftFlag[];
};

export type DayDraftResult = {
  day_number: number;
  services: ServiceDraft[];
  skipped_reasons: string[];
};

/** Day -> destination/date anchor the caller supplies (backend does not rebuild the itinerary — see routers/v2/ai_drafter.py). */
export type DraftDaySpec = {
  dayNumber: number;
  destinationId: string;
  serviceDate: string;
};

export type AiRunStatus = 'succeeded' | 'partial' | 'failed';

export type AiRunSummary = {
  id: string;
  agent_name: string;
  status: AiRunStatus;
  idempotency_key: string;
  stats: Record<string, unknown>;
  created_at: string;
};

export type AiRunListResponse = { runs: AiRunSummary[] };

export type AnalyzeTripResponse = {
  run_id: string;
  trip_profile: TripProfile;
  fallback_used: boolean;
  confidence_notes: string[];
};

export type DraftDayOutcome = {
  day_number: number;
  lines_created: number;
  draft: DayDraftResult | null;
  error: string | null;
};

export type DraftServicesResponse = {
  run_id: string;
  status: AiRunStatus;
  days_done: number[];
  days_failed: number[];
  day_outcomes: DraftDayOutcome[];
  created_line_ids: string[];
  manual_review_count: number;
};

function newAiDrafterIdempotencyKey(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function analyzeTripProfile(
  sheetId: string,
  rawText: string,
  idempotencyKey: string = newAiDrafterIdempotencyKey(),
): Promise<AnalyzeTripResponse> {
  return request<AnalyzeTripResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/ai/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ rawText }),
  });
}

export async function draftServices(
  sheetId: string,
  input: {
    runId: string;
    tripProfile: TripProfile;
    days: DraftDaySpec[];
    dayNumbers?: number[] | null;
    baseCostingRevision: number;
  },
  idempotencyKey: string = newAiDrafterIdempotencyKey(),
): Promise<DraftServicesResponse> {
  return request<DraftServicesResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/ai/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(input),
  });
}

export async function listAiRuns(sheetId: string): Promise<AiRunListResponse> {
  return request<AiRunListResponse>(`/api/v2/costing-sheets/${encodeURIComponent(sheetId)}/ai/runs`);
}

// ---------------------------------------------------------------------------
// Booking & Operations (15.6) — deposit landed, each service_line copies into a
// booking_line that FREEZES pricing/terms forever (T3) plus LIVE ops fields
// (status, deadlines, supplier_ref, voucher). Every write carries
// base_booking_revision (CAS); the server response is always the fresh state —
// never recompute deadlines client-side (they come pre-computed from the
// server's policy JSONB, see core/rules/booking_rules.py).
// ---------------------------------------------------------------------------

export type BookingLineStatus = 'to_request' | 'requested' | 'confirmed' | 'delivered' | 'cancelled';
export type BookingHeaderStatus = 'active' | 'completed' | 'cancelled';
export type BookingLineUrgency = 'overdue' | 'due_soon' | 'ok';

export type SupplierContactProfile = {
  person?: string | null;
  email?: string | null;
  phone?: string | null;
  whatsapp?: string | null;
  zalo?: string | null;
  website?: string | null;
};

export type CancellationTierProfile = { days_before_service_min: number; penalty_percent: number };
export type CancellationPolicyProfile = {
  tiers: CancellationTierProfile[];
  no_show_penalty_percent: number;
  note?: string | null;
};
export type PaymentTermsProfile = {
  deposit_percent?: number | null;
  deposit_due_days_after_confirm?: number | null;
  balance_due_days_before_service?: number | null;
  method?: string | null;
  note?: string | null;
};

export type BookingLineProfile = {
  id: string;
  booking_id: string;
  source_service_line_id: string;
  supplier_id_snapshot: string | null;
  supplier_name_snapshot: string | null;
  supplier_contact_snapshot_json: SupplierContactProfile | null;
  title_snapshot: string;
  category: string;
  service_date: string | null;
  unit: string;
  time_basis: string;
  qty_unit: number;
  qty_time: number;
  unit_cost_minor_snapshot: number;
  cost_currency_snapshot: string;
  fx_rate_ppm_snapshot: number | null;
  sell_minor_snapshot: number;
  payment_terms_snapshot_json: PaymentTermsProfile | null;
  cancellation_policy_snapshot_json: CancellationPolicyProfile | null;
  status: BookingLineStatus;
  request_by_date: string | null;
  penalty_free_until: string | null;
  deposit_due_date: string | null;
  balance_due_date: string | null;
  supplier_ref: string | null;
  voucher_ref: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  cancel_penalty_minor: number | null;
  assignee_email: string | null;
  notes: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
  urgency: BookingLineUrgency | null;
};

export type BookingProfile = {
  id: string;
  quotation_id: string;
  sheet_id: string;
  booking_code: string;
  status: BookingHeaderStatus;
  deposit_received_at: string;
  customer_balance_due_date: string | null;
  party_label_snapshot: string | null;
  travel_start_date: string | null;
  travel_end_date: string | null;
  booking_revision: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type BookingDetailResponse = {
  booking: BookingProfile;
  lines: BookingLineProfile[];
  cash_flow_warnings: string[];
};

export type BookingBoardItem = {
  line: BookingLineProfile;
  booking_id: string;
  booking_code: string;
  booking_revision: number;
  quotation_id: string;
  party_label_snapshot: string | null;
  travel_start_date: string | null;
  travel_end_date: string | null;
  customer_balance_due_date: string | null;
  cash_flow_warning: boolean;
};

export type BookingBoardResponse = { items: BookingBoardItem[] };

export async function createBooking(
  input: { quotation_id: string; deposit_received_at: string; customer_balance_due_date?: string | null },
  idempotencyKey: string,
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>('/api/v2/bookings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(input),
  });
}

export async function listBookingBoard(filters: {
  status?: BookingLineStatus;
  assignee?: string;
  quotationId?: string;
  dueWithinDays?: number;
  overdueOnly?: boolean;
} = {}): Promise<BookingBoardResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.assignee) params.set('assignee', filters.assignee);
  if (filters.quotationId) params.set('quotationId', filters.quotationId);
  if (filters.dueWithinDays != null) params.set('dueWithinDays', String(filters.dueWithinDays));
  if (filters.overdueOnly) params.set('overdueOnly', 'true');
  const query = params.toString();
  return request<BookingBoardResponse>(`/api/v2/bookings${query ? `?${query}` : ''}`);
}

export async function getBooking(bookingId: string): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(`/api/v2/bookings/${encodeURIComponent(bookingId)}`);
}

export async function updateBookingHeader(
  bookingId: string,
  input: { base_booking_revision: number; customer_balance_due_date?: string | null; status?: BookingHeaderStatus; notes?: string | null },
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(`/api/v2/bookings/${encodeURIComponent(bookingId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function transitionBookingLine(
  bookingId: string,
  lineId: string,
  input: { base_booking_revision: number; to: BookingLineStatus; supplier_ref?: string | null; cancel_reason?: string | null },
  idempotencyKey: string,
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(
    `/api/v2/bookings/${encodeURIComponent(bookingId)}/lines/${encodeURIComponent(lineId)}/transition`,
    { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey }, body: JSON.stringify(input) },
  );
}

export async function updateBookingLineOps(
  bookingId: string,
  lineId: string,
  input: { base_booking_revision: number; request_by_date?: string | null; assignee_email?: string | null; notes?: string | null; supplier_ref?: string | null },
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(
    `/api/v2/bookings/${encodeURIComponent(bookingId)}/lines/${encodeURIComponent(lineId)}`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) },
  );
}

export async function addBookingLine(
  bookingId: string,
  input: { base_booking_revision: number; service_line_id: string },
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(`/api/v2/bookings/${encodeURIComponent(bookingId)}/lines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function cancelBooking(
  bookingId: string,
  input: { base_booking_revision: number; reason: string },
): Promise<BookingDetailResponse> {
  return request<BookingDetailResponse>(`/api/v2/bookings/${encodeURIComponent(bookingId)}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
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

// destination_type vocab mirrors core/rules/catalog_vocab.py DESTINATION_TYPE (15.2b).
export type DestinationType = "country" | "region" | "province" | "city" | "sub_zone";

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
  mediaPrefix?: string | null;
  defaultMediaPrefix?: string;
  matchedFrom?: string;
  parentId?: string | null;
  destinationType?: DestinationType;
  countryCode?: string | null;
  iataCode?: string | null;
  timezone?: string;
  mergedIntoId?: string | null;
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
  mediaPrefix?: string | null;
  parentId?: string | null;
  destinationType?: DestinationType;
  countryCode?: string | null;
  iataCode?: string | null;
  timezone?: string;
};

export type DestinationListResponse = {
  items: DestinationProfile[];
};

export async function listDestinationsCatalog({
  active = "true",
  query = "",
  countrySlug,
  types,
  parentId,
  limit = 100,
}: {
  active?: "true" | "false" | "all";
  query?: string;
  countrySlug?: string;
  types?: DestinationType[];
  parentId?: string;
  limit?: number;
} = {}): Promise<DestinationListResponse> {
  const params = new URLSearchParams({ active });
  if (query.trim()) params.set("query", query.trim());
  if (countrySlug) params.set("countrySlug", countrySlug);
  if (types?.length) params.set("types", types.join(","));
  if (parentId) params.set("parentId", parentId);
  if (limit) params.set("limit", String(limit));
  return request<DestinationListResponse>(`/api/v2/destinations?${params.toString()}`);
}

export async function mergeDestination(sourceId: string, targetId: string): Promise<DestinationProfile> {
  return request<DestinationProfile>(`/api/v2/destinations/${encodeURIComponent(sourceId)}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ targetId }),
  });
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

// ---------------------------------------------------------------------------------------------
// Catalog Ingestion (15.8) — Interactive Ingestion Co-Pilot

export type IngestionBatchStatus =
  | "draft"
  | "needs_clarification"
  | "ready"
  | "committed"
  | "rejected"
  | "archived";

export type IngestionSourceChannel = "email" | "zalo" | "whatsapp" | "portal" | "in_person" | "internal";
export type IngestionSourceDocumentType =
  | "rate_sheet"
  | "contract"
  | "amendment"
  | "quotation"
  | "promotion"
  | "manual_note";

export type IngestionClarification = {
  id: string;
  question: string;
  blocking: boolean;
  source_quote?: string | null;
  options?: string[] | null;
  target_path: string;
};

export type IngestionResolutionAction = "create" | "update" | "supersede_rate" | "skip_duplicate" | "needs_input";

export type IngestionResolutionEntry = {
  entity_ref: string;
  entity_type: "supplier" | "product" | "rate";
  action: IngestionResolutionAction;
  matched_id?: string | null;
  evidence: string;
  clarifications: IngestionClarification[];
};

export type IngestionResolution = {
  entries: IngestionResolutionEntry[];
  clarifications: IngestionClarification[];
};

export type IngestionUnresolvedItem = {
  description: string;
  reason?: string | null;
  source_quote?: string | null;
  target_path?: string | null;
};

export type IngestionPriceLineCandidate = {
  price_for_hint?: string | null;
  occupancy_hint?: string | null;
  tier_pax_text?: string | null;
  amount_text: string;
  currency_text?: string | null;
  source_quote: string;
};

export type IngestionRateGroupCandidate = {
  product_title_text: string;
  validity_text: string;
  rate_basis_hint?: string | null;
  price_lines: IngestionPriceLineCandidate[];
  supplements: unknown[];
  blackout_text?: string | null;
  policy_text?: string | null;
  source_quote: string;
};

export type IngestionProductCandidate = {
  title_text: string;
  category_hint?: string | null;
  subcategory_hint?: string | null;
  unit_hint?: string | null;
  time_basis_hint?: string | null;
  destination_text?: string | null;
  source_quote: string;
};

export type IngestionSupplierCandidate = {
  name_text: string;
  type_hint?: string | null;
  destination_text?: string | null;
  contact_text?: string | null;
  source_quote: string;
};

export type IngestionPayload = {
  supplier: IngestionSupplierCandidate | null;
  products: IngestionProductCandidate[];
  rate_groups: IngestionRateGroupCandidate[];
  unresolved: IngestionUnresolvedItem[];
  covers_multiple_suppliers: boolean;
  doc_meta: Record<string, unknown>;
};

export type IngestionBatch = {
  id: string;
  status: IngestionBatchStatus;
  raw_text: string;
  source_channel: string;
  source_document_type: string;
  payload: IngestionPayload;
  parsed: Record<string, unknown>;
  resolution: IngestionResolution | null;
  conversation: Array<Record<string, unknown>>;
  operator_edits: Record<string, unknown>;
  commit_result: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  batch_revision: number;
  created_at: string;
  updated_at: string;
};

export type IngestionBatchSummary = {
  id: string;
  status: IngestionBatchStatus;
  source_channel: string;
  source_document_type: string;
  unresolved_count: number;
  products_count: number;
  rate_groups_count: number;
  created_at: string;
  updated_at: string;
};

export type IngestionBatchListResponse = { items: IngestionBatchSummary[]; total: number };

function newIngestionIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function createIngestionBatch(
  input: { rawText: string; sourceChannel: IngestionSourceChannel; sourceDocumentType: IngestionSourceDocumentType },
  idempotencyKey: string = newIngestionIdempotencyKey(),
): Promise<IngestionBatch> {
  return request<IngestionBatch>("/api/v2/ingestion-batches", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(input),
  });
}

export async function listIngestionBatches(status?: IngestionBatchStatus): Promise<IngestionBatchListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<IngestionBatchListResponse>(`/api/v2/ingestion-batches${query}`);
}

export async function getIngestionBatch(id: string): Promise<IngestionBatch> {
  return request<IngestionBatch>(`/api/v2/ingestion-batches/${encodeURIComponent(id)}`);
}

export async function answerIngestionBatchClarifications(
  id: string,
  answers: Record<string, unknown>,
  baseBatchRevision: number,
): Promise<IngestionBatch> {
  return request<IngestionBatch>(`/api/v2/ingestion-batches/${encodeURIComponent(id)}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, baseBatchRevision }),
  });
}

export async function editIngestionBatch(
  id: string,
  edits: Record<string, unknown>,
  baseBatchRevision: number,
): Promise<IngestionBatch> {
  return request<IngestionBatch>(`/api/v2/ingestion-batches/${encodeURIComponent(id)}/edits`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edits, baseBatchRevision }),
  });
}

export async function commitIngestionBatch(
  id: string,
  baseBatchRevision: number,
  acknowledgeUnresolved = false,
  idempotencyKey: string = newIngestionIdempotencyKey(),
): Promise<IngestionBatch> {
  return request<IngestionBatch>(`/api/v2/ingestion-batches/${encodeURIComponent(id)}/commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ baseBatchRevision, acknowledgeUnresolved }),
  });
}

export async function rejectIngestionBatch(
  id: string,
  baseBatchRevision: number,
  reason?: string,
): Promise<IngestionBatch> {
  return request<IngestionBatch>(`/api/v2/ingestion-batches/${encodeURIComponent(id)}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ baseBatchRevision, reason }),
  });
}



