"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { listTravelStyles, type TravelStyleCategoryGroup } from "../../lib/quotationApi.ts";

export const FALLBACK_TRAVEL_STYLE_TAXONOMY: TravelStyleCategoryGroup[] = [
  {
    category_id: "group_composition",
    title_en: "Group Size",
    title_vi: "Nhóm khách",
    tags: [
      { id: "tag_solo", category: "group_composition", name_en: "Solo Traveler", name_vi: "Du lịch cá nhân", slug: "solo-traveler", display_order: 1 },
      { id: "tag_couple", category: "group_composition", name_en: "Couple / Romantic", name_vi: "Cặp đôi", slug: "couple", display_order: 2 },
      { id: "tag_family", category: "group_composition", name_en: "Family", name_vi: "Gia đình", slug: "family", display_order: 3 },
      { id: "tag_friends", category: "group_composition", name_en: "Friends Group", name_vi: "Nhóm bạn bè", slug: "friends-group", display_order: 4 },
      { id: "tag_corporate", category: "group_composition", name_en: "Corporate Group", name_vi: "Đoàn công ty", slug: "corporate-group", display_order: 5 },
    ],
  },
  {
    category_id: "tour_type",
    title_en: "Tour Type",
    title_vi: "Loại hình tour",
    tags: [
      { id: "tag_private_tour", category: "tour_type", name_en: "Private Tour", name_vi: "Tour riêng cao cấp", slug: "private-tour", display_order: 1 },
      { id: "tag_small_group_tour", category: "tour_type", name_en: "Small Group Tour", name_vi: "Tour ghép đoàn nhỏ", slug: "small-group-tour", display_order: 2 },
      { id: "tag_shared_tour", category: "tour_type", name_en: "Shared Tour", name_vi: "Tour chia sẻ", slug: "shared-tour", display_order: 3 },
      { id: "tag_fit", category: "tour_type", name_en: "FIT / Self-Guided", name_vi: "FIT tự túc", slug: "fit-self-guided", display_order: 4 },
      { id: "tag_tailor_made", category: "tour_type", name_en: "Tailor-Made", name_vi: "Thiết kế riêng", slug: "tailor-made", display_order: 5 },
    ],
  },
  {
    category_id: "purpose",
    title_en: "Purpose",
    title_vi: "Mục đích",
    tags: [
      { id: "tag_honeymoon", category: "purpose", name_en: "Honeymoon", name_vi: "Trăng mật", slug: "honeymoon", display_order: 1 },
      { id: "tag_mice", category: "purpose", name_en: "MICE / Incentive", name_vi: "Hội họp & Khen thưởng", slug: "mice", display_order: 2 },
      { id: "tag_leisure", category: "purpose", name_en: "Leisure & Relaxation", name_vi: "Nghỉ dưỡng", slug: "leisure-relaxation", display_order: 3 },
      { id: "tag_wellness", category: "purpose", name_en: "Wellness & Retreat", name_vi: "Sức khỏe & Thiền", slug: "wellness-retreat", display_order: 4 },
      { id: "tag_celebration", category: "purpose", name_en: "Celebration", name_vi: "Lễ kỷ niệm", slug: "celebration-anniversary", display_order: 5 },
    ],
  },
  {
    category_id: "interest_experience",
    title_en: "Interests & Experience",
    title_vi: "Sở thích & Trải nghiệm",
    tags: [
      { id: "tag_cultural", category: "interest_experience", name_en: "Cultural & Heritage", name_vi: "Văn hóa & Di sản", slug: "cultural-heritage", display_order: 1 },
      { id: "tag_war_history", category: "interest_experience", name_en: "War Heritage & Historical", name_vi: "Di tích lịch sử", slug: "war-heritage-historical", display_order: 2 },
      { id: "tag_ecotourism", category: "interest_experience", name_en: "Ecotourism & Nature", name_vi: "Sinh thái & Tự nhiên", slug: "ecotourism-nature", display_order: 3 },
      { id: "tag_wildlife", category: "interest_experience", name_en: "Wildlife & Birdwatching", name_vi: "Động vật & Xem chim", slug: "wildlife-birdwatching", display_order: 4 },
      { id: "tag_adventure", category: "interest_experience", name_en: "Adventure & Trekking", name_vi: "Thám hiểm & Leo núi", slug: "adventure-trekking", display_order: 5 },
      { id: "tag_culinary", category: "interest_experience", name_en: "Culinary & Gastronomy", name_vi: "Ẩm thực", slug: "culinary-gastronomy", display_order: 6 },
      { id: "tag_photography", category: "interest_experience", name_en: "Photography & Scenic", name_vi: "Nhiếp ảnh", slug: "photography-scenic", display_order: 7 },
      { id: "tag_luxury", category: "interest_experience", name_en: "Luxury & Exclusive", name_vi: "Sang trọng & Độc quyền", slug: "luxury-exclusive", display_order: 8 },
    ],
  },
];

export function useTravelStyles() {
  const { data, error, isLoading } = useSWR(
    "travel-styles",
    listTravelStyles,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
      fallbackData: { categories: FALLBACK_TRAVEL_STYLE_TAXONOMY },
    }
  );

  const categories = useMemo(() => {
    if (data?.categories && data.categories.length > 0) {
      return data.categories;
    }
    return FALLBACK_TRAVEL_STYLE_TAXONOMY;
  }, [data]);

  return {
    categories,
    isLoading,
    error: error ? "Could not load travel style taxonomy." : null,
  };
}
