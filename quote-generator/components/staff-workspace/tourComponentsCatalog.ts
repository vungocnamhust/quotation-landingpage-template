import {
  Building2,
  Palette,
  Car,
  Sparkles,
  Ticket,
  MapPin,
  Handshake,
} from "lucide-react";
import type { ComponentType } from "react";
import type { TravelStyleTagItem } from "../../lib/quotationApi.ts";

export type ComponentCategoryKey =
  | "accommodations"
  | "travel_styles"
  | "cars"
  | "experiences"
  | "tickets"
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

export const CATEGORIES: CategoryMeta[] = [
  {
    key: "accommodations",
    label: "Accommodations",
    description: "Manage hotel & resort profiles, default check-in/out rules, and property media across destinations.",
    icon: Building2,
    emptyTitle: "No accommodations found",
    emptyDescription: "Start by adding your first accommodation profile to the catalog.",
    actionLabel: "Add accommodation",
  },
  {
    key: "travel_styles",
    label: "Travel Styles",
    description: "Manage travel style tags and taxonomy (Group Composition, Tour Type, Purpose & Theme, Interest & Experience).",
    icon: Palette,
    emptyTitle: "No travel styles found",
    emptyDescription: "No travel styles found in the selected category.",
    actionLabel: "Add travel style",
  },
  {
    key: "cars",
    label: "Cars & Transport",
    description: "Product catalog entries in category transportation — vehicles, luxury vans, speedboats, and trains, each a sellable variant of a supplier at a destination (no pricing here — see 15.3).",
    icon: Car,
    emptyTitle: "No transportation products yet",
    emptyDescription: "Start by adding your first transportation product — vehicle, transfer, or boat service.",
    actionLabel: "Add transportation product",
  },
  {
    key: "experiences",
    label: "Experiences",
    description: "Product catalog entries in categories experience and meal — signature activities, workshops, guided tours, and dining, each a sellable variant of a supplier at a destination.",
    icon: Sparkles,
    emptyTitle: "No experience or meal products yet",
    emptyDescription: "Start by adding your first experience or meal product.",
    actionLabel: "Add experience/meal product",
  },
  {
    key: "tickets",
    label: "Tickets & Passes",
    description: "Product catalog entries in categories ticket, flights, and visa — entrance tickets, passes, flights, and visa services, each a sellable variant of a supplier at a destination.",
    icon: Ticket,
    emptyTitle: "No ticket, flight, or visa products yet",
    emptyDescription: "Start by adding your first ticket, flight, or visa product.",
    actionLabel: "Add ticket/flight/visa product",
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

// Flat travel style tag item with localized category titles
export interface FlatTravelStyleTag extends TravelStyleTagItem {
  categoryTitleEn: string;
  categoryTitleVi: string;
}

// Generic catalog item shape for non-DB categories
export interface GenericComponentItem {
  id: string;
  name: string;
  category: string;
  subtitle: string;
  tags: string[];
  status: "Active" | "Draft";
  updatedAt: string;
}

// 15.2 §2.2 — the 3 previously-stub slots map to product catalog categories.
// Mirrors core/rules/catalog_vocab.py CATEGORY. No new ComponentCategoryKey added.
export type ProductComponentSlotKey = "cars" | "experiences" | "tickets";

export const PRODUCT_CATEGORY_BY_SLOT: Record<ProductComponentSlotKey, ("accommodation" | "transportation" | "ticket" | "flights" | "guide" | "guide_expense" | "experience" | "meal" | "visa" | "others")[]> = {
  cars: ["transportation"],
  experiences: ["experience", "meal"],
  tickets: ["ticket", "flights", "visa"],
};

export function isProductComponentSlot(key: ComponentCategoryKey): key is ProductComponentSlotKey {
  return key === "cars" || key === "experiences" || key === "tickets";
}
