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
    description: "Manage vehicle inventory, capacity, private transfers, luxury vans, speedboats, and trains.",
    icon: Car,
    emptyTitle: "No transport inventory yet",
    emptyDescription: "Start by cataloging your first vehicle, luxury van, transfer, or boat service.",
    actionLabel: "Add transport",
  },
  {
    key: "experiences",
    label: "Experiences",
    description: "Curate signature activities, local workshops, guided tours, and dining experiences.",
    icon: Sparkles,
    emptyTitle: "No curated experiences yet",
    emptyDescription: "Start by adding signature experiences, guided tours, and workshops.",
    actionLabel: "Add experience",
  },
  {
    key: "tickets",
    label: "Tickets & Passes",
    description: "Catalog entry tickets, cable car passes, museum fees, and special event permits.",
    icon: Ticket,
    emptyTitle: "No tickets or passes cataloged",
    emptyDescription: "Add entrance tickets, attraction passes, or permit entries to the catalog.",
    actionLabel: "Add ticket",
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
