"use client";

import { useDeferredValue, useMemo, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import {
  Building2,
  Palette,
  Car,
  Sparkles,
  Ticket,
  MapPin,
  Plus,
  Calendar,
  Phone,
  CheckCircle2,
  XCircle,
  Tag,
  Hash,
} from "lucide-react";

import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import {
  createAccommodation,
  listAccommodations,
  listTravelStyles,
  updateAccommodation,
  updateAccommodationStatus,
  uploadAccommodationAsset,
  type AccommodationProfile,
  type AccommodationProfileInput,
  type TravelStyleTagItem,
} from "../../lib/quotationApi";
import AccommodationProfileForm from "../quotation-workspace/AccommodationProfileForm";
import type { DestinationRef } from "../quotation-workspace/DestinationInputs";
import { DataViewContainer } from "../ui/data-view/DataViewContainer";
import type { ColumnDef } from "../ui/data-view/DataTable";

export type ComponentCategoryKey =
  | "accommodations"
  | "travel_styles"
  | "cars"
  | "experiences"
  | "tickets"
  | "destinations";

interface CategoryMeta {
  key: ComponentCategoryKey;
  label: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const CATEGORIES: CategoryMeta[] = [
  {
    key: "accommodations",
    label: "Accommodations",
    description: "Manage hotel & resort profiles, default check-in/out rules, and property media across destinations.",
    icon: Building2,
  },
  {
    key: "travel_styles",
    label: "Travel Styles",
    description: "Manage travel style tags and taxonomy (Group Composition, Tour Type, Purpose & Theme, Interest & Experience).",
    icon: Palette,
  },
  {
    key: "cars",
    label: "Cars & Transport",
    description: "Manage vehicle inventory, capacity, private transfers, luxury vans, speedboats, and trains.",
    icon: Car,
  },
  {
    key: "experiences",
    label: "Experiences",
    description: "Curate signature activities, local workshops, guided tours, and dining experiences.",
    icon: Sparkles,
  },
  {
    key: "tickets",
    label: "Tickets & Passes",
    description: "Catalog entry tickets, cable car passes, museum fees, and special event permits.",
    icon: Ticket,
  },
  {
    key: "destinations",
    label: "Destinations",
    description: "Maintain primary travel destinations, cities, highlight points, and regional cover imagery.",
    icon: MapPin,
  },
];

// Flat travel style tag item with category title
export interface FlatTravelStyleTag extends TravelStyleTagItem {
  categoryTitleEn: string;
  categoryTitleVi: string;
}

// Blank input helper for Accommodations
const blankAccommodationInput = (): AccommodationProfileInput => ({
  destinationId: "",
  name: "",
  room_type: null,
  check_in: null,
  check_out: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

function profileInput(profile: AccommodationProfile): AccommodationProfileInput {
  return {
    destinationId: profile.destination_id,
    name: profile.name,
    room_type: profile.room_type,
    check_in: profile.check_in,
    check_out: profile.check_out,
    intro: profile.intro,
    phone: profile.phone,
    display_city: profile.display_city,
    display_date: profile.display_date,
    hotel_asset: profile.hotel_asset,
    room_asset: profile.room_asset,
  };
}

// Mock item shape for generic categories (Cars, Experiences, Tickets, Destinations)
interface GenericComponentItem {
  id: string;
  name: string;
  category: string;
  subtitle: string;
  tags: string[];
  status: "Active" | "Draft";
  updatedAt: string;
}

const MOCK_CATALOG_DATA: Record<Exclude<ComponentCategoryKey, "accommodations" | "travel_styles">, GenericComponentItem[]> = {
  cars: [
    { id: "car-1", name: "Sedan Premium (Mercedes E-Class)", category: "Vehicle", subtitle: "Capacity: 2 Passengers + 2 Bags · English Driver", tags: ["Private", "Luxury"], status: "Active", updatedAt: "2026-08-11" },
    { id: "car-2", name: "Luxury Van (Limousine DCar 9s)", category: "Vehicle", subtitle: "Capacity: 6 Passengers + 6 Bags · Reclining Seats", tags: ["Group", "VIP"], status: "Active", updatedAt: "2026-08-09" },
    { id: "car-3", name: "Halong Speedboat Express", category: "Boat", subtitle: "Capacity: 12 Passengers · Tuan Chau Pier Transfer", tags: ["Marine", "Express"], status: "Active", updatedAt: "2026-08-04" },
    { id: "car-4", name: "Coaster Coach (29 Seats)", category: "Bus", subtitle: "Capacity: 20 Passengers + Luggage · Chilled Water", tags: ["MICE", "Tour Group"], status: "Active", updatedAt: "2026-07-28" },
  ],
  experiences: [
    { id: "exp-1", name: "Hanoi Street Food Discovery", category: "Activity", subtitle: "3.5 Hours · Old Quarter Hidden Gems & Egg Coffee", tags: ["Culinary", "Guided"], status: "Active", updatedAt: "2026-08-11" },
    { id: "exp-2", name: "Private Sunset Kayaking in Lan Ha Bay", category: "Activity", subtitle: "2 Hours · Quiet lagoons & limestone karsts", tags: ["Adventure", "Scenic"], status: "Active", updatedAt: "2026-08-07" },
    { id: "exp-3", name: "Lantern Making Workshop Hoi An", category: "Workshop", subtitle: "1.5 Hours · Master craftsman guided souvenir", tags: ["Craft", "Family"], status: "Active", updatedAt: "2026-08-03" },
    { id: "exp-4", name: "Helicopter Aerial Tour of Halong Bay", category: "Excursion", subtitle: "15 Mins · Panoramic flight from Tuan Chau", tags: ["Exotic", "VIP"], status: "Active", updatedAt: "2026-07-29" },
  ],
  tickets: [
    { id: "tkt-1", name: "Fansipan Legend Cable Car Roundtrip", category: "Pass", subtitle: "Sapa Summit Access & Monorail Ticket", tags: ["Sapa", "Mountain"], status: "Active", updatedAt: "2026-08-09" },
    { id: "tkt-2", name: "Hoi An Ancient Town Cultural Pass", category: "Permit", subtitle: "Access to 5 heritage sites in Old Town", tags: ["Heritage", "Culture"], status: "Active", updatedAt: "2026-08-06" },
    { id: "tkt-3", name: "Imperial Citadel Hue Entrance Ticket", category: "Entrance", subtitle: "Forbidden Purple City access", tags: ["History", "UNESCO"], status: "Active", updatedAt: "2026-08-02" },
  ],
  destinations: [
    { id: "dest-1", name: "Hanoi", category: "City", subtitle: "Capital City · Heritage, Gastronomy & Old Quarter", tags: ["North", "Urban"], status: "Active", updatedAt: "2026-08-12" },
    { id: "dest-2", name: "Halong Bay & Lan Ha Bay", category: "Coastal", subtitle: "UNESCO Seascape · Luxury Overnight Cruises", tags: ["North", "Bay"], status: "Active", updatedAt: "2026-08-10" },
    { id: "dest-3", name: "Hoi An & Danang", category: "Central Coast", subtitle: "Ancient Town, Beaches & Marble Mountains", tags: ["Central", "Beach"], status: "Active", updatedAt: "2026-08-08" },
    { id: "dest-4", name: "Saigon & Mekong Delta", category: "South Region", subtitle: "Dynamic Metropolis, Floating Markets & Cu Chi Tunnels", tags: ["South", "Delta"], status: "Active", updatedAt: "2026-08-05" },
  ],
};

export default function TourComponentsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Active Category selection
  const activeCategoryParam = (searchParams.get("category") as ComponentCategoryKey) || "accommodations";
  const [activeCategory, setActiveCategory] = useState<ComponentCategoryKey>(activeCategoryParam);

  const currentCategoryMeta = useMemo(
    () => CATEGORIES.find((c) => c.key === activeCategory) ?? CATEGORIES[0],
    [activeCategory]
  );

  // Search & Filter state
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "true" | "false">("all");
  const [travelStyleGroupFilter, setTravelStyleGroupFilter] = useState<string>("all");

  const deferredSearch = useDeferredValue(search);

  // Accommodations specific drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<AccommodationProfile | null>(null);
  const [draft, setDraft] = useState<AccommodationProfileInput>(blankAccommodationInput);
  const [destinationRef, setDestinationRef] = useState<DestinationRef | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  // Fetch accommodations via SWR if category is accommodations
  const accommodationQueryKey = ["accommodations", activeFilter, deferredSearch];
  const {
    data: profileResponse,
    error: accommodationError,
    isLoading: isAccommodationLoading,
    mutate: mutateProfiles,
  } = useSWR(
    activeCategory === "accommodations" ? accommodationQueryKey : null,
    ([, active, query]) =>
      listAccommodations({ active: active as "true" | "false" | "all", query })
  );

  const accommodationItems = useMemo(
    () => profileResponse?.items ?? [],
    [profileResponse]
  );

  // Fetch travel styles via SWR if category is travel_styles
  const {
    data: travelStyleResponse,
    error: travelStyleError,
    isLoading: isTravelStyleLoading,
  } = useSWR(
    activeCategory === "travel_styles" ? ["travel-styles"] : null,
    listTravelStyles
  );

  // Flatten & filter real database Travel Styles
  const travelStyleItems = useMemo(() => {
    if (activeCategory !== "travel_styles" || !travelStyleResponse?.categories) {
      return [];
    }

    const flatList: FlatTravelStyleTag[] = [];
    for (const catGroup of travelStyleResponse.categories) {
      for (const tag of catGroup.tags) {
        flatList.push({
          ...tag,
          categoryTitleEn: catGroup.title_en,
          categoryTitleVi: catGroup.title_vi,
        });
      }
    }

    let filtered = flatList;

    // Filter by group taxonomy if selected
    if (travelStyleGroupFilter !== "all") {
      filtered = filtered.filter((item) => item.category === travelStyleGroupFilter);
    }

    // Filter by search query
    if (deferredSearch.trim()) {
      const lower = deferredSearch.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.name_en.toLowerCase().includes(lower) ||
          item.name_vi.toLowerCase().includes(lower) ||
          item.slug.toLowerCase().includes(lower) ||
          item.categoryTitleEn.toLowerCase().includes(lower)
      );
    }

    return filtered;
  }, [activeCategory, travelStyleResponse, travelStyleGroupFilter, deferredSearch]);

  // Filter generic catalog items (Cars, Experiences, Tickets, Destinations)
  const genericItems = useMemo(() => {
    if (activeCategory === "accommodations" || activeCategory === "travel_styles") return [];
    const list = MOCK_CATALOG_DATA[activeCategory] ?? [];
    if (!deferredSearch.trim()) return list;
    const lower = deferredSearch.toLowerCase();
    return list.filter(
      (item) =>
        item.name.toLowerCase().includes(lower) ||
        item.subtitle.toLowerCase().includes(lower) ||
        item.tags.some((t) => t.toLowerCase().includes(lower))
    );
  }, [activeCategory, deferredSearch]);

  const handleCategoryChange = (key: ComponentCategoryKey) => {
    setActiveCategory(key);
    setSearch("");
    setTravelStyleGroupFilter("all");
    router.replace(`/workspace/components?category=${key}`, { scroll: false });
  };

  // Accommodation drawer handlers
  const openCreateAccommodation = () => {
    setEditing(null);
    setDraft(blankAccommodationInput());
    setDestinationRef(null);
    setMessage("");
    setIsDrawerOpen(true);
  };

  const openEditAccommodation = (profile: AccommodationProfile) => {
    setEditing(profile);
    setDraft(profileInput(profile));
    setDestinationRef(profile.destination_ref);
    setMessage("");
    setIsDrawerOpen(true);
  };

  const saveAccommodation = async () => {
    if (!destinationRef || !draft.name.trim()) {
      setMessage("Destination and accommodation name are required.");
      return;
    }
    setPending(true);
    try {
      const input = { ...draft, destinationId: destinationRef.id };
      if (editing) {
        await updateAccommodation(editing.id, input);
      } else {
        await createAccommodation(input);
      }
      await mutateProfiles();
      setIsDrawerOpen(false);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Accommodation could not be saved."
      );
    } finally {
      setPending(false);
    }
  };

  const uploadAsset = async (target: "hotel_asset" | "room_asset", file: File) => {
    if (!editing) return;
    setPending(true);
    try {
      const uploaded = await uploadAccommodationAsset(
        file,
        editing.id,
        target === "hotel_asset" ? "exteriors" : "interiors"
      );
      setDraft((current) => ({ ...current, [target]: uploaded.r2Key }));
      setMessage("Asset uploaded. Save profile to confirm modifications.");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Asset upload failed."
      );
    } finally {
      setPending(false);
    }
  };

  const toggleAccommodationStatus = useCallback(
    async (profile: AccommodationProfile) => {
      setPending(true);
      try {
        await updateAccommodationStatus(profile.id, !profile.is_active);
        await mutateProfiles();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Status update failed.");
      } finally {
        setPending(false);
      }
    },
    [mutateProfiles]
  );

  // Accommodation Table Columns Definition
  const accommodationColumns: ColumnDef<AccommodationProfile>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Accommodation Name & Destination",
        render: (profile) => (
          <div className="flex flex-col gap-1">
            <h4
              className={cn(
                getTypographyClassName("cardTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {profile.name}
            </h4>
            <p
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1 text-[var(--color-muted)]"
              )}
            >
              <MapPin size={13} className="shrink-0 text-[var(--color-accent)]" />
              <span>{profile.display_city || profile.destination}</span>
            </p>
          </div>
        ),
      },
      {
        key: "room_type",
        header: "Room Type & Rules",
        render: (profile) => (
          <div className="flex flex-col gap-1">
            <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
              {profile.room_type || "Standard Room"}
            </span>
            <div
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1 text-[var(--color-muted)]"
              )}
            >
              <Calendar size={12} className="shrink-0" />
              <span>
                In: {profile.check_in || "N/A"} · Out: {profile.check_out || "N/A"}
              </span>
            </div>
          </div>
        ),
      },
      {
        key: "contact",
        header: "Phone / Contact",
        render: (profile) =>
          profile.phone ? (
            <p
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1.5 text-[var(--color-muted)]"
              )}
            >
              <Phone size={13} className="shrink-0" />
              <span>{profile.phone}</span>
            </p>
          ) : (
            <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              —
            </span>
          ),
      },
      {
        key: "status",
        header: "Status",
        render: (profile) => (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 inline-self-start",
              profile.is_active
                ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
            )}
          >
            {profile.is_active ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
            <span>{profile.is_active ? "Active" : "Inactive"}</span>
          </span>
        ),
      },
      {
        key: "actions",
        header: "Actions",
        headerClassName: "text-right",
        cellClassName: "text-right",
        render: (profile) => (
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => openEditAccommodation(profile)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)]"
              )}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => void toggleAccommodationStatus(profile)}
              className={cn(
                getTypographyClassName("caption"),
                "rounded-[var(--radius-button)] px-2.5 py-1 transition-all",
                profile.is_active
                  ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                  : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
              )}
            >
              {profile.is_active ? "Deactivate" : "Activate"}
            </button>
          </div>
        ),
      },
    ],
    [toggleAccommodationStatus]
  );

  // Travel Style Table Columns Definition
  const travelStyleColumns: ColumnDef<FlatTravelStyleTag>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Tag Name (EN / VI)",
        render: (tag) => (
          <div className="flex flex-col gap-0.5">
            <h4
              className={cn(
                getTypographyClassName("cardTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {tag.name_en}
            </h4>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              {tag.name_vi}
            </p>
          </div>
        ),
      },
      {
        key: "category",
        header: "Category Group",
        render: (tag) => (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_20%,transparent)]"
            )}
          >
            <Palette size={12} />
            <span>{tag.categoryTitleEn}</span>
          </span>
        ),
      },
      {
        key: "slug",
        header: "Slug ID",
        render: (tag) => (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "font-mono rounded bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] border border-[var(--color-border)]"
            )}
          >
            {tag.slug}
          </span>
        ),
      },
      {
        key: "display_order",
        header: "Order",
        render: (tag) => (
          <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
            #{tag.display_order}
          </span>
        ),
      },
      {
        key: "status",
        header: "Status",
        render: () => (
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 inline-self-start bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
            )}
          >
            <CheckCircle2 size={12} />
            <span>Active</span>
          </span>
        ),
      },
    ],
    []
  );

  // Generic Catalog Table Columns Definition
  const genericColumns: ColumnDef<GenericComponentItem>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Item Name & Subtitle",
        render: (item) => (
          <div className="flex flex-col gap-1">
            <h4
              className={cn(
                getTypographyClassName("cardTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {item.name}
            </h4>
            <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
              {item.subtitle}
            </p>
          </div>
        ),
      },
      {
        key: "category",
        header: "Category",
        render: (item) => (
          <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
            {item.category}
          </span>
        ),
      },
      {
        key: "tags",
        header: "Tags",
        render: (item) => (
          <div className="flex flex-wrap items-center gap-1.5">
            {item.tags.map((tag) => (
              <span
                key={tag}
                className={cn(
                  getTypographyClassName("caption"),
                  "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)]"
                )}
              >
                <Tag size={11} />
                <span>{tag}</span>
              </span>
            ))}
          </div>
        ),
      },
      {
        key: "updatedAt",
        header: "Updated",
        render: (item) => (
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {item.updatedAt}
          </span>
        ),
      },
      {
        key: "actions",
        header: "Actions",
        headerClassName: "text-right",
        cellClassName: "text-right",
        render: () => (
          <button
            type="button"
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)]"
            )}
          >
            Manage
          </button>
        ),
      },
    ],
    []
  );

  return (
    <main className="flex flex-col gap-6">
      {/* Header section */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]"
            )}
          >
            Catalog management
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-1 text-[var(--color-on-surface)]"
            )}
          >
            Tour Components
          </h1>
          <p
            className={cn(
              getTypographyClassName("bodyLg"),
              "mt-1 text-[var(--color-muted)]"
            )}
          >
            {currentCategoryMeta.description}
          </p>
        </div>
      </header>

      {/* Sub-category Pills Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => handleCategoryChange(cat.key)}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex shrink-0 items-center gap-2 rounded-[var(--radius-button)] px-4 py-2.5 transition-all",
                isActive
                  ? "border border-[var(--color-border-strong)] bg-[var(--color-accent)] text-white shadow-xs"
                  : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]"
              )}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Render Data View Container for Accommodations */}
      {activeCategory === "accommodations" ? (
        <DataViewContainer<AccommodationProfile>
          items={accommodationItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search accommodations…"
          filters={[
            { label: "All", value: "all" },
            { label: "Active", value: "true" },
            { label: "Inactive", value: "false" },
          ]}
          activeFilter={activeFilter}
          onFilterChange={(val) => setActiveFilter(val as "all" | "true" | "false")}
          isLoading={isAccommodationLoading}
          error={accommodationError}
          emptyTitle="No accommodations found"
          emptyDescription={
            search
              ? "No accommodations match your search query."
              : "Start by adding your first accommodation profile to the catalog."
          }
          emptyIcon={<Building2 size={40} className="mb-3 text-[var(--color-muted)]" />}
          actionButton={
            <button
              type="button"
              onClick={openCreateAccommodation}
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)]"
              )}
            >
              <Plus size={18} />
              <span>Add accommodation</span>
            </button>
          }
          gridItemRenderer={(profile) => (
            <article
              key={profile.id}
              className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3
                      className={cn(
                        getTypographyClassName("cardTitle"),
                        "truncate text-[var(--color-on-surface)]"
                      )}
                    >
                      {profile.name}
                    </h3>
                    <p
                      className={cn(
                        getTypographyClassName("caption"),
                        "mt-0.5 flex items-center gap-1.5 text-[var(--color-muted)]"
                      )}
                    >
                      <MapPin size={14} className="shrink-0" />
                      <span className="truncate">
                        {profile.display_city || profile.destination}
                      </span>
                    </p>
                  </div>
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0",
                      profile.is_active
                        ? "bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                        : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] border border-[var(--color-border)]"
                    )}
                  >
                    {profile.is_active ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                    <span>{profile.is_active ? "Active" : "Inactive"}</span>
                  </span>
                </div>

                <div
                  className={cn(
                    getTypographyClassName("caption"),
                    "mt-4 flex flex-col gap-1.5 text-[var(--color-muted)]"
                  )}
                >
                  {profile.room_type ? (
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--color-on-surface)]">Room type:</span>
                      <span className="truncate">{profile.room_type}</span>
                    </div>
                  ) : null}

                  {profile.check_in || profile.check_out ? (
                    <div className="flex items-center gap-1.5">
                      <Calendar size={13} className="shrink-0" />
                      <span>
                        In: {profile.check_in || "N/A"} · Out: {profile.check_out || "N/A"}
                      </span>
                    </div>
                  ) : null}

                  {profile.phone ? (
                    <div className="flex items-center gap-1.5">
                      <Phone size={13} className="shrink-0" />
                      <span>{profile.phone}</span>
                    </div>
                  ) : null}

                  {profile.intro ? (
                    <p
                      className={cn(
                        getTypographyClassName("caption"),
                        "mt-2 line-clamp-2 text-[var(--color-muted)]"
                      )}
                    >
                      “{profile.intro}”
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
                <button
                  type="button"
                  onClick={() => openEditAccommodation(profile)}
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-surface-hover)]"
                  )}
                >
                  Edit
                </button>

                <button
                  type="button"
                  onClick={() => void toggleAccommodationStatus(profile)}
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-[var(--radius-button)] px-3 py-1.5 transition-all",
                    profile.is_active
                      ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                      : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                  )}
                >
                  {profile.is_active ? "Deactivate" : "Activate"}
                </button>
              </div>
            </article>
          )}
          tableColumns={accommodationColumns}
        />
      ) : activeCategory === "travel_styles" ? (
        /* Render Data View Container for Real Database Travel Styles */
        <DataViewContainer<FlatTravelStyleTag>
          items={travelStyleItems}
          keyExtractor={(tag) => tag.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search travel styles by name, slug or group…"
          filters={[
            { label: "All Groups", value: "all" },
            { label: "Group Composition", value: "group_composition" },
            { label: "Tour Type", value: "tour_type" },
            { label: "Purpose & Theme", value: "purpose" },
            { label: "Interest & Experience", value: "interest_experience" },
          ]}
          activeFilter={travelStyleGroupFilter}
          onFilterChange={setTravelStyleGroupFilter}
          isLoading={isTravelStyleLoading}
          error={travelStyleError}
          emptyTitle="No travel styles found"
          emptyDescription={
            search
              ? "No travel style tags match your search query."
              : "No travel styles found in the selected category."
          }
          emptyIcon={<Palette size={40} className="mb-3 text-[var(--color-muted)]" />}
          gridItemRenderer={(tag) => (
            <article
              key={tag.id}
              className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3
                      className={cn(
                        getTypographyClassName("cardTitle"),
                        "truncate text-[var(--color-on-surface)]"
                      )}
                    >
                      {tag.name_en}
                    </h3>
                    <p
                      className={cn(
                        getTypographyClassName("bodySm"),
                        "mt-0.5 text-[var(--color-muted)]"
                      )}
                    >
                      {tag.name_vi}
                    </p>
                  </div>
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                    )}
                  >
                    <CheckCircle2 size={12} />
                    <span>Active</span>
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)]"
                    )}
                  >
                    <Palette size={12} />
                    <span>{tag.categoryTitleEn}</span>
                  </span>

                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "inline-flex items-center gap-1 font-mono rounded bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] border border-[var(--color-border)]"
                    )}
                  >
                    <Hash size={11} />
                    <span>{tag.slug}</span>
                  </span>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
                <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  Order: #{tag.display_order}
                </span>
                <span className={cn(getTypographyClassName("caption"), "font-mono text-[var(--color-muted)]")}>
                  {tag.id}
                </span>
              </div>
            </article>
          )}
          tableColumns={travelStyleColumns}
        />
      ) : (
        /* Render Data View Container for Generic Component Categories */
        <DataViewContainer<GenericComponentItem>
          items={genericItems}
          keyExtractor={(item) => item.id}
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder={`Search ${currentCategoryMeta.label.toLowerCase()}…`}
          emptyTitle={`No ${currentCategoryMeta.label.toLowerCase()} found`}
          emptyDescription="No catalog items match your search query."
          emptyIcon={
            <currentCategoryMeta.icon size={40} className="mb-3 text-[var(--color-muted)]" />
          }
          actionButton={
            <button
              type="button"
              className={cn(
                getTypographyClassName("buttonPrimary"),
                "flex items-center justify-center gap-2 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)]"
              )}
            >
              <Plus size={18} />
              <span>Add {currentCategoryMeta.label.slice(0, -1)}</span>
            </button>
          }
          gridItemRenderer={(item) => (
            <article
              key={item.id}
              className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3
                      className={cn(
                        getTypographyClassName("cardTitle"),
                        "truncate text-[var(--color-on-surface)]"
                      )}
                    >
                      {item.name}
                    </h3>
                    <p
                      className={cn(
                        getTypographyClassName("caption"),
                        "mt-0.5 text-[var(--color-muted)]"
                      )}
                    >
                      {item.subtitle}
                    </p>
                  </div>
                  <span
                    className={cn(
                      getTypographyClassName("caption"),
                      "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
                    )}
                  >
                    <CheckCircle2 size={12} />
                    <span>{item.status}</span>
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-1.5">
                  {item.tags.map((tag) => (
                    <span
                      key={tag}
                      className={cn(
                        getTypographyClassName("caption"),
                        "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)]"
                      )}
                    >
                      <Tag size={11} />
                      <span>{tag}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
                <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                  Updated: {item.updatedAt}
                </span>
                <button
                  type="button"
                  className={cn(
                    getTypographyClassName("buttonSecondary"),
                    "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)]"
                  )}
                >
                  Manage
                </button>
              </div>
            </article>
          )}
          tableColumns={genericColumns}
        />
      )}

      {/* Accommodations Drawer Modal */}
      {isDrawerOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Accommodation profile"
          className="fixed inset-0 z-50 flex justify-end bg-[color-mix(in_srgb,var(--color-contrast)_35%,transparent)]"
        >
          <section className="h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--color-border-strong)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2
                  className={cn(
                    getTypographyClassName("cardTitle"),
                    "text-[var(--color-on-surface)]"
                  )}
                >
                  {editing ? "Edit Accommodation" : "Add Accommodation"}
                </h2>
                <p
                  className={cn(
                    getTypographyClassName("bodySm"),
                    "mt-1 text-[var(--color-muted)]"
                  )}
                >
                  Configure hotel details and media assets for use across quotations.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsDrawerOpen(false)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 py-2 text-[var(--color-on-surface)] transition-all hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]"
                )}
              >
                Close
              </button>
            </div>

            <AccommodationProfileForm
              draft={draft}
              destinationRef={destinationRef}
              profileId={editing?.id ?? null}
              onChange={setDraft}
              onDestinationChange={setDestinationRef}
              onUpload={(target, file) => void uploadAsset(target, file)}
            />

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsDrawerOpen(false)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 py-2.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)]"
                )}
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={pending}
                onClick={() => void saveAccommodation()}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 py-2.5 text-white shadow-md transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:opacity-50"
                )}
              >
                {pending ? "Saving…" : "Save Accommodation"}
              </button>
            </div>

            {message ? (
              <p
                aria-live="polite"
                className={cn(
                  getTypographyClassName("bodySm"),
                  "mt-3 text-[var(--color-accent)]"
                )}
              >
                {message}
              </p>
            ) : null}
          </section>
        </div>
      ) : null}
    </main>
  );
}
