import type { ProductInput, ProductProfile } from "../../lib/quotationApi.ts";
import {
  DEFAULT_CHARGE_UNIT_BY_CATEGORY,
  type ProductCategory,
} from "./types.ts";

export function createProductDraft(
  category: ProductCategory,
  destinationId = "",
): ProductInput {
  const [unit, timeBasis] = DEFAULT_CHARGE_UNIT_BY_CATEGORY[category];
  return {
    destination_id: destinationId,
    origin_destination_id: null,
    category,
    title: "",
    supplier_id: null,
    property_id: null,
    subcategory: null,
    subcategory_note: null,
    supplier_product_name: null,
    unit,
    time_basis: timeBasis,
    default_min_pax: null,
    default_max_pax: null,
    category_attributes: {},
  };
}

export function productToDraft(product: ProductProfile): ProductInput {
  return {
    destination_id: product.destination_id,
    origin_destination_id: product.origin_destination_id ?? null,
    category: product.category,
    title: product.title,
    supplier_id: product.supplier_id ?? null,
    property_id: product.property_id ?? null,
    subcategory: product.subcategory ?? null,
    subcategory_note: product.subcategory_note ?? null,
    supplier_product_name: product.supplier_product_name ?? null,
    unit: product.unit,
    time_basis: product.time_basis,
    default_min_pax: product.default_min_pax ?? null,
    default_max_pax: product.default_max_pax ?? null,
    category_attributes: product.category_attributes ?? {},
  };
}
