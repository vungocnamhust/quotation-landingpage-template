import {
  Building2,
  Car,
  Sparkles,
  Ticket,
  UtensilsCrossed,
  BadgeCheck,
  UsersRound,
  MapPin,
  Handshake,
} from "lucide-react";
import type { ComponentType } from "react";
import type { ProductCategory } from "../../lib/quotationApi.ts";

export type ComponentCategoryKey =
  | "hotels"
  | "cars"
  | "guides"
  | "activities"
  | "dining"
  | "visa"
  | "destinations"
  | "suppliers";

export interface CategoryMeta {
  key: ComponentCategoryKey;
  label: string;
  description: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  emptyTitle: string;
  emptyDescription: string;
  actionLabel: string;
}

export const CATEGORIES: readonly CategoryMeta[] = [
  {
    key: "hotels",
    label: "Hotels & Stays",
    description: "Sellable room and stay products. Property imagery and editorial profiles are managed in Content Studio.",
    icon: Building2,
    emptyTitle: "No hotel or stay products yet",
    emptyDescription: "Start by adding a sellable room, resort, villa, or other stay product.",
    actionLabel: "Add hotel or stay product",
  },
  {
    key: "cars",
    label: "Cars & Transport",
    description: "Sellable transportation and flight products, including vehicles, boats, trains, and air services.",
    icon: Car,
    emptyTitle: "No transport products yet",
    emptyDescription: "Start by adding a transportation or flight product.",
    actionLabel: "Add transport product",
  },
  {
    key: "guides",
    label: "Tour Guides",
    description: "Sellable guide services and guide-related operating expenses.",
    icon: UsersRound,
    emptyTitle: "No guide products yet",
    emptyDescription: "Start by adding a guide service or guide expense product.",
    actionLabel: "Add guide product",
  },
  {
    key: "activities",
    label: "Activities & Tickets",
    description: "Sellable experiences, attractions, admission tickets, and passes.",
    icon: Ticket,
    emptyTitle: "No activity or ticket products yet",
    emptyDescription: "Start by adding an experience or ticket product.",
    actionLabel: "Add activity or ticket product",
  },
  {
    key: "dining",
    label: "Dining & Meals",
    description: "Sellable dining, restaurant, and meal services.",
    icon: UtensilsCrossed,
    emptyTitle: "No dining products yet",
    emptyDescription: "Start by adding a meal or dining product.",
    actionLabel: "Add dining product",
  },
  {
    key: "visa",
    label: "Visa & Ancillaries",
    description: "Sellable visa, fast-track, SIM, gifting, and ancillary services.",
    icon: BadgeCheck,
    emptyTitle: "No visa or ancillary products yet",
    emptyDescription: "Start by adding a visa or ancillary product.",
    actionLabel: "Add visa or ancillary product",
  },
  {
    key: "destinations",
    label: "Destinations",
    description: "Maintain primary travel destinations, cities, highlight points, and regional cover imagery.",
    icon: MapPin,
    emptyTitle: "No custom destinations configured",
    emptyDescription: "Add regional destinations, arrival hubs, and points of interest.",
    actionLabel: "Add destination",
  },
  {
    key: "suppliers",
    label: "Suppliers",
    description: "Manage the creditor-side registry — DMCs, hotels, wholesalers, and other vendors we pay for services.",
    icon: Handshake,
    emptyTitle: "No suppliers found",
    emptyDescription: "Start by registering your first supplier — hotel, DMC, wholesaler, or freelance vendor.",
    actionLabel: "Add supplier",
  },
];

export type ProductComponentSlotKey = Extract<
  ComponentCategoryKey,
  "hotels" | "cars" | "guides" | "activities" | "dining" | "visa"
>;

// Mirrors core/rules/catalog_vocab.py CATEGORY. Every backend product category
// belongs to exactly one commercial catalog tab; the first category is its create preset.
export const PRODUCT_CATEGORY_BY_SLOT: Record<ProductComponentSlotKey, readonly ProductCategory[]> = {
  hotels: ["accommodation"],
  cars: ["transportation", "flights"],
  guides: ["guide", "guide_expense"],
  activities: ["experience", "ticket"],
  dining: ["meal"],
  visa: ["visa", "others"],
};

export function isProductComponentSlot(key: ComponentCategoryKey): key is ProductComponentSlotKey {
  return key in PRODUCT_CATEGORY_BY_SLOT;
}
