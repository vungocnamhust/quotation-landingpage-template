// Mirrors core/rules/catalog_vocab.py — keep both files' vocab in sync (15.2).
import type {
  ProductCategory,
  ProductCategoryAttributeValue,
  ProductChargeUnit,
  ProductInput,
  ProductProfile,
  ProductTimeBasis,
} from "../../lib/quotationApi.ts";

export type {
  ProductCategory,
  ProductCategoryAttributeValue,
  ProductChargeUnit,
  ProductInput,
  ProductProfile,
  ProductTimeBasis,
};

export const CATEGORY_OPTIONS: ProductCategory[] = [
  "accommodation",
  "transportation",
  "ticket",
  "flights",
  "guide",
  "guide_expense",
  "experience",
  "meal",
  "visa",
  "others",
];

export const DEFAULT_CHARGE_UNIT_BY_CATEGORY: Record<ProductCategory, [ProductChargeUnit, ProductTimeBasis]> = {
  accommodation: ["room", "night"],
  transportation: ["vehicle", "day"],
  ticket: ["person", "trip"],
  flights: ["person", "trip"],
  guide: ["group", "day"],
  guide_expense: ["group", "day"],
  experience: ["person", "trip"],
  meal: ["person", "trip"],
  visa: ["person", "trip"],
  others: ["set", "trip"],
};

export const SUBCATEGORY_BY_CATEGORY: Record<ProductCategory, { value: string; label: string }[]> = {
  accommodation: [
    { value: "hotel", label: "Hotel" },
    { value: "resort", label: "Resort" },
    { value: "boutique_hotel", label: "Boutique Hotel" },
    { value: "villa", label: "Villa" },
    { value: "overnight_cruise", label: "Overnight Cruise" },
    { value: "overnight_train", label: "Overnight Train" },
    { value: "lodge", label: "Lodge" },
    { value: "homestay", label: "Homestay" },
    { value: "other_overnight_accommodation", label: "Other Overnight Accommodation" },
  ],
  transportation: [
    { value: "car_4_seat", label: "4-seat Car" },
    { value: "car_7_seat", label: "7-seat Car" },
    { value: "limousine_van_9_seat", label: "9-seat Limousine Van" },
    { value: "van_16_seat", label: "16-seat Van" },
    { value: "bus_29_seat", label: "29-seat Bus" },
    { value: "bus_35_seat", label: "35-seat Bus" },
    { value: "bus_45_seat", label: "45-seat Bus" },
    { value: "train", label: "Train" },
    { value: "ferry_boat", label: "Ferry / Boat" },
    { value: "speedboat", label: "Speedboat" },
    { value: "other_transportation", label: "Other Transportation" },
  ],
  ticket: [
    { value: "park", label: "Park" },
    { value: "national_park", label: "National Park" },
    { value: "attraction", label: "Attraction" },
    { value: "museum", label: "Museum" },
    { value: "heritage_site", label: "Heritage Site" },
    { value: "cable_car", label: "Cable Car" },
    { value: "boat_ticket", label: "Boat Ticket" },
    { value: "entrance_ticket", label: "Entrance Ticket" },
    { value: "show", label: "Show" },
    { value: "performance", label: "Performance" },
    { value: "other_admission", label: "Other Admission" },
  ],
  flights: [
    { value: "domestic_flight", label: "Domestic Flight" },
    { value: "regional_flight", label: "Regional Flight" },
    { value: "international_flight", label: "International Flight" },
    { value: "charter_flight", label: "Charter Flight" },
    { value: "seaplane", label: "Seaplane" },
    { value: "helicopter", label: "Helicopter" },
    { value: "other_flights", label: "Other Flights" },
  ],
  guide: [
    { value: "local_guide", label: "Local Guide" },
    { value: "full_trip_guide", label: "Full-trip Guide" },
    { value: "tour_escort", label: "Tour Escort" },
    { value: "specialist_guide", label: "Specialist Guide" },
    { value: "language_specific_guide", label: "Language-specific Guide" },
    { value: "other_guide", label: "Other Guide" },
  ],
  guide_expense: [
    { value: "guide_accommodation", label: "Guide Accommodation" },
    { value: "guide_meals", label: "Guide Meals" },
    { value: "guide_transportation", label: "Guide Transportation" },
    { value: "guide_flight", label: "Guide Flight" },
    { value: "guide_train", label: "Guide Train" },
    { value: "guide_entrance_fee", label: "Guide Entrance Fee" },
    { value: "guide_allowance", label: "Guide Allowance" },
    { value: "other_guide_expense", label: "Other Guide Expense" },
  ],
  experience: [
    { value: "workshop", label: "Workshop" },
    { value: "jeep_tour", label: "Jeep Tour" },
    { value: "vespa_tour", label: "Vespa Tour" },
    { value: "cycling", label: "Cycling" },
    { value: "cooking_class", label: "Cooking Class" },
    { value: "food_tour", label: "Food Tour" },
    { value: "art_craft_experience", label: "Art / Craft Experience" },
    { value: "wellness", label: "Wellness" },
    { value: "cultural_experience", label: "Cultural Experience" },
    { value: "private_access", label: "Private Access" },
    { value: "expert_meeting", label: "Expert Meeting" },
    { value: "photography", label: "Photography" },
    { value: "boat_experience", label: "Boat Experience" },
    { value: "adventure_activity", label: "Adventure Activity" },
    { value: "other_experience", label: "Other Experience" },
  ],
  meal: [
    { value: "breakfast", label: "Breakfast" },
    { value: "lunch", label: "Lunch" },
    { value: "dinner", label: "Dinner" },
    { value: "set_menu", label: "Set Menu" },
    { value: "fine_dining", label: "Fine Dining" },
    { value: "street_food", label: "Street Food" },
    { value: "halal_meal", label: "Halal Meal" },
    { value: "vegetarian_meal", label: "Vegetarian Meal" },
    { value: "special_event_dinner", label: "Special Event Dinner" },
    { value: "drinks_package", label: "Drinks Package" },
    { value: "other_fnb", label: "Other F&B" },
  ],
  visa: [
    { value: "standard_visa", label: "Standard Visa" },
    { value: "e_visa", label: "E-visa" },
    { value: "urgent_visa", label: "Urgent Visa" },
    { value: "visa_on_arrival_support", label: "Visa on Arrival Support" },
    { value: "visa_processing_service", label: "Visa Processing Service" },
    { value: "special_nationality_visa", label: "Special-Nationality Visa" },
    { value: "other_visa", label: "Other Visa" },
  ],
  others: [
    { value: "airport_fast_track", label: "Airport Fast Track" },
    { value: "meet_and_assist", label: "Meet & Assist" },
    { value: "vip_airport_service", label: "VIP Airport Service" },
    { value: "sim", label: "SIM" },
    { value: "esim", label: "eSIM" },
    { value: "souvenir", label: "Souvenir" },
    { value: "welcome_gift", label: "Welcome Gift" },
    { value: "porterage", label: "Porterage" },
    { value: "lounge", label: "Lounge" },
    { value: "photographer", label: "Photographer" },
    { value: "security", label: "Security" },
    { value: "concierge", label: "Concierge" },
    { value: "other_ancillary_service", label: "Other Ancillary Service" },
  ],
};

// Phụ lục A — suggested keys per category (gợi ý UI, không ép cứng).
export const SUGGESTED_ATTRIBUTE_KEYS_BY_CATEGORY: Record<ProductCategory, string[]> = {
  accommodation: ["room_type", "meal_plan", "view", "bed_config"],
  transportation: ["vehicle_type", "seat_capacity", "has_driver"],
  ticket: ["admission_type", "skip_line"],
  flights: ["cabin_class", "route"],
  guide: ["language", "specialty"],
  guide_expense: ["expense_type"],
  experience: ["duration_hours", "group_max", "physical_level"],
  meal: ["meal_type", "cuisine"],
  visa: ["visa_type", "processing_days"],
  others: [],
};

export function isOtherSubcategory(subcategory: string | null | undefined): boolean {
  return !!subcategory && subcategory.startsWith("other_");
}

export type ProductSelectSize = "sm" | "md" | "lg";
export type ProductSelectVariant = "default" | "compact" | "inline";

export interface ProductSelectProps {
  value?: string | null;
  onChange?: (productId: string | null, product?: ProductProfile | null) => void;
  category?: ProductCategory | ProductCategory[];
  destinationId?: string;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  size?: ProductSelectSize;
  variant?: ProductSelectVariant;
  allowManage?: boolean;
  className?: string;
  error?: string | null;
  helperText?: string;
  id?: string;
  "aria-label"?: string;
}
