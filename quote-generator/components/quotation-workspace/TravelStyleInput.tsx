"use client";

import { useEffect, useState } from "react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import { listTravelStyles, type TravelStyleCategoryGroup, type TravelStyleTagItem } from "../../lib/quotationApi";
import { Tag } from "lucide-react";

const FALLBACK_TAXONOMY: TravelStyleCategoryGroup[] = [
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

type TravelStyleInputProps = {
  label?: string;
  value: string | null;
  disabled?: boolean;
  onChange: (value: string | null) => void;
};

export default function TravelStyleInput({
  label = "Travel Style",
  value,
  disabled = false,
  onChange,
}: TravelStyleInputProps) {
  const [categories, setCategories] = useState<TravelStyleCategoryGroup[]>(FALLBACK_TAXONOMY);
  const [activeCategory, setActiveCategory] = useState<string>("group_composition");

  useEffect(() => {
    let unmounted = false;
    listTravelStyles()
      .then((res) => {
        if (!unmounted && res.categories && res.categories.length > 0) {
          setCategories(res.categories);
        }
      })
      .catch(() => {
        // Fallback taxonomy remains active on offline / fallback
      });
    return () => {
      unmounted = true;
    };
  }, []);

  const currentValue = value ?? "";
  const selectedTags = currentValue
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const toggleTag = (tagName: string) => {
    if (disabled) return;
    const exists = selectedTags.some((t) => t.toLowerCase() === tagName.toLowerCase());
    let nextTags: string[];
    if (exists) {
      nextTags = selectedTags.filter((t) => t.toLowerCase() !== tagName.toLowerCase());
    } else {
      nextTags = [...selectedTags, tagName];
    }
    const nextString = nextTags.join(", ");
    onChange(nextString || null);
  };

  const currentCategoryObj = categories.find((c) => c.category_id === activeCategory) || categories[0];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)] flex items-center gap-1.5")}>
          <Tag className="w-3.5 h-3.5 text-[var(--color-accent)]" />
          {label}
        </label>
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Select presets or type freeform text
        </span>
      </div>

      {/* Freeform text input */}
      <input
        type="text"
        disabled={disabled}
        value={currentValue}
        placeholder="e.g. Couple, Private Tour, Cultural & Heritage"
        onChange={(e) => onChange(e.target.value || null)}
        className={cn(
          getTypographyClassName("bodySm"),
          "w-full rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)] transition-all focus:border-[var(--color-accent)] focus:outline-hidden disabled:opacity-50"
        )}
      />

      {/* Preset taxonomy badge selectors */}
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-2.5 flex flex-col gap-2">
        {/* Category Tabs */}
        <div className="flex flex-wrap gap-1 border-b border-[var(--color-border)] pb-2">
          {categories.map((cat) => {
            const isActive = cat.category_id === activeCategory;
            return (
              <button
                key={cat.category_id}
                type="button"
                disabled={disabled}
                onClick={() => setActiveCategory(cat.category_id)}
                className={cn(
                  getTypographyClassName("caption"),
                  "px-2.5 py-1 rounded-full transition-all cursor-pointer",
                  isActive
                    ? "bg-[var(--color-accent)] text-white shadow-2xs"
                    : "bg-[var(--color-surface)] text-[var(--color-muted)] hover:text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)]"
                )}
              >
                {cat.title_en}
              </button>
            );
          })}
        </div>

        {/* Tag pills for active category */}
        {currentCategoryObj ? (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {currentCategoryObj.tags.map((tag: TravelStyleTagItem) => {
              const isSelected = selectedTags.some((t) => t.toLowerCase() === tag.name_en.toLowerCase());
              return (
                <button
                  key={tag.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => toggleTag(tag.name_en)}
                  className={cn(
                    getTypographyClassName("caption"),
                    "px-2.5 py-1 rounded-[var(--radius-button)] border transition-all flex items-center gap-1 cursor-pointer",
                    isSelected
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-wash)]"
                  )}
                >
                  <span>{isSelected ? "✓" : "+"}</span>
                  <span>{tag.name_en}</span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}
