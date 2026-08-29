/**
 * Pure domain rules for Review & Workflow reconciliation (Layer 1).
 *
 * Encapsulates JSON pointer parsing, error code translation,
 * and canonical blocker aggregation with zero React dependencies.
 */

import type {
  ContentBlocker,
  ContentReadiness,
  ReviewResponse,
  WorkflowResponse,
} from '../../components/quotation-workspace/useQuotationWorkspace.ts';

// Plan 16.2 F-18: blocker ids must survive the server reordering its list
// between polls. A positional `content-blocker-${idx}` id makes React
// misattribute identity across reorders the same way `key={index}` would —
// this hashes the blocker's own content instead, so identity only changes
// when what it describes actually changes.
function hashBlockerContent(...parts: string[]): string {
  const input = parts.join(' ');
  let hash = 5381;
  for (let i = 0; i < input.length; i += 1) {
    hash = ((hash << 5) + hash + input.charCodeAt(i)) | 0;
  }
  return (hash >>> 0).toString(36);
}

export type BlockerCategory = 'facts' | 'content' | 'design' | 'publish';
export type BlockerStage = 'facts' | 'content' | 'design' | 'publish' | 'review';

export type TargetHandoff = {
  stage: BlockerStage;
  section?: string;
  fieldId?: string;
  index?: number;
  source?: string;
  focus?: {
    kind: 'day' | 'hotel' | 'pricingOption' | 'bookingTerm' | 'routeSegment';
    index: number;
    id?: string;
  };
};

export type CanonicalBlockerItem = {
  id: string;
  category: BlockerCategory;
  title: string;
  description: string;
  ctaLabel: string;
  isAdvisory?: boolean;
  targetHandoff: TargetHandoff;
  rawError?: string;
};

export type ParsedJsonPointer = {
  domain: string;
  collection?: string;
  index?: number;
  field?: string;
  raw: string;
};

const ITINERARY_DAY_REGEX = /^\/itinerary\/days\/(\d+)(?:\/(description|title))?$/;
const HOTEL_STAY_REGEX = /^\/stays\/hotels\/(\d+)$/;

/**
 * Pure function: Parse standard JSON pointers (e.g. /itinerary/days/0/description).
 */
export function parseJsonPointer(pointer: string): ParsedJsonPointer {
  if (!pointer || typeof pointer !== 'string') {
    return { domain: 'unknown', raw: pointer ?? '' };
  }

  const clean = pointer.startsWith('/') ? pointer.slice(1) : pointer;
  const segments = clean.split('/');

  const itineraryMatch = pointer.match(ITINERARY_DAY_REGEX);
  if (itineraryMatch) {
    const idx = parseInt(itineraryMatch[1], 10);
    return {
      domain: 'itinerary',
      collection: 'days',
      index: idx,
      field: itineraryMatch[2],
      raw: pointer,
    };
  }

  const hotelMatch = pointer.match(HOTEL_STAY_REGEX);
  if (hotelMatch) {
    const idx = parseInt(hotelMatch[1], 10);
    return {
      domain: 'stays',
      collection: 'hotels',
      index: idx,
      raw: pointer,
    };
  }

  return {
    domain: segments[0] || 'unknown',
    collection: segments.length > 1 && !isNaN(Number(segments[1])) ? undefined : segments[1],
    index: segments.length > 1 && !isNaN(Number(segments[1])) ? Number(segments[1]) : undefined,
    field: segments.length > 2 ? segments[2] : segments[1],
    raw: pointer,
  };
}

/**
 * Pure function: Map a backend presentation / PDF layout error string into a CanonicalBlockerItem.
 */
export function mapPresentationErrorToBlocker(
  error: string,
  index: number,
  lang: string = 'en'
): CanonicalBlockerItem {
  const isVi = lang === 'vi';
  const parsed = parseJsonPointer(error);

  if (parsed.domain === 'itinerary' && parsed.index !== undefined) {
    const dayNumber = parsed.index + 1;
    if (parsed.field === 'description') {
      return {
        id: `design-error-${hashBlockerContent(error)}`,
        category: 'design',
        title: isVi
          ? `Nội dung Ngày ${dayNumber} quá dài (vượt quá 1,150 ký tự)`
          : `Day ${dayNumber} description too long (exceeds 1,150 characters)`,
        description: isVi
          ? `Văn bản mô tả của Ngày ${dayNumber} vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn nội dung trên Design Canvas.`
          : `Narrative text for Day ${dayNumber} exceeds A4 PDF printable boundaries. Please shorten the copy on Design Canvas.`,
        ctaLabel: isVi ? `Sửa nội dung Ngày ${dayNumber} trên Design Canvas` : `Edit Day ${dayNumber} on Design Canvas`,
        targetHandoff: {
          stage: 'design',
          section: `itinerary:day:${dayNumber}`,
          index: parsed.index,
          source: `/itinerary/days/${parsed.index}/description/0`,
          focus: { kind: 'day', index: parsed.index },
        },
        rawError: error,
      };
    }

    if (parsed.field === 'title') {
      return {
        id: `design-error-${hashBlockerContent(error)}`,
        category: 'design',
        title: isVi
          ? `Tiêu đề Ngày ${dayNumber} quá dài (vượt quá 170 ký tự)`
          : `Day ${dayNumber} title too long (exceeds 170 characters)`,
        description: isVi
          ? `Tiêu đề Ngày ${dayNumber} vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn tiêu đề trên Design Canvas.`
          : `Day ${dayNumber} title exceeds A4 PDF printable space. Please shorten the title on Design Canvas.`,
        ctaLabel: isVi ? `Sửa tiêu đề Ngày ${dayNumber} trên Design Canvas` : `Edit Day ${dayNumber} Title on Design Canvas`,
        targetHandoff: {
          stage: 'design',
          section: `itinerary:day:${dayNumber}`,
          index: parsed.index,
          source: `/itinerary/days/${parsed.index}/title`,
          focus: { kind: 'day', index: parsed.index },
        },
        rawError: error,
      };
    }

    return {
      id: `design-error-${hashBlockerContent(error)}`,
      category: 'design',
      title: isVi ? `Lỗi dữ liệu Ngày ${dayNumber}` : `Day ${dayNumber} Layout Error`,
      description: isVi
        ? `Nội dung Ngày ${dayNumber} không hợp lệ cho bố cục trang in PDF.`
        : `Content on Day ${dayNumber} does not fit A4 PDF printable layout.`,
      ctaLabel: isVi ? `Sửa nội dung Ngày ${dayNumber} trên Design Canvas` : `Edit Day ${dayNumber} on Design Canvas`,
      targetHandoff: {
        stage: 'design',
        section: `itinerary:day:${dayNumber}`,
        index: parsed.index,
        source: `/itinerary/days/${parsed.index}/description/0`,
        focus: { kind: 'day', index: parsed.index },
      },
      rawError: error,
    };
  }

  if (parsed.domain === 'stays' && parsed.index !== undefined) {
    const hotelNumber = parsed.index + 1;
    return {
      id: `design-error-${hashBlockerContent(error)}`,
      category: 'design',
      title: isVi
        ? `Thông tin Khách sạn ${hotelNumber} quá dài (vượt quá 2,100 ký tự)`
        : `Hotel ${hotelNumber} copy too long (exceeds 2,100 characters)`,
      description: isVi
        ? `Văn bản giới thiệu khách sạn vượt quá giới hạn trang in A4 PDF. Vui lòng rút gọn thông tin khách sạn trên Design Canvas.`
        : `Hotel information exceeds A4 PDF printable page budget. Please shorten the description on Design Canvas.`,
      ctaLabel: isVi ? `Sửa thông tin Khách sạn trên Design Canvas` : `Edit Hotel on Design Canvas`,
      targetHandoff: {
        stage: 'design',
        section: 'hotel_plan',
        index: parsed.index,
        source: `/stays/hotels/${parsed.index}`,
        focus: { kind: 'hotel', index: parsed.index },
      },
      rawError: error,
    };
  }

  return {
    id: `design-error-${hashBlockerContent(error)}`,
    category: 'design',
    title: isVi ? 'Lỗi cấu hình hiển thị' : 'Presentation & Layout Check Failed',
    description: error,
    ctaLabel: isVi ? 'Kiểm tra Design' : 'Inspect Design',
    targetHandoff: {
      stage: 'design',
    },
    rawError: error,
  };
}

/**
 * Pure function: Map missing fact inputs to Facts stage section deep links.
 */
export function mapMissingFactInput(missingInput: string): TargetHandoff {
  if (missingInput.startsWith('customer_facts')) {
    return { stage: 'facts', section: 'travellers' };
  }
  if (missingInput.startsWith('trip_facts')) {
    return { stage: 'facts', section: 'trip' };
  }
  if (missingInput.startsWith('pricing_facts') || missingInput.startsWith('commercial')) {
    return { stage: 'facts', section: 'commercial' };
  }
  if (missingInput.startsWith('service_facts')) {
    return { stage: 'facts', section: 'services' };
  }
  if (missingInput.startsWith('brand_id') || missingInput.startsWith('seller')) {
    return { stage: 'facts', section: 'seller' };
  }
  return { stage: 'facts' };
}

/**
 * Pure function: Convert complete ReviewResponse, WorkflowResponse, and publication job info
 * into an aggregated, deduplicated list of CanonicalBlockerItems.
 */
export function fromReviewResponse(
  reviewData?: ReviewResponse | null,
  workflowData?: WorkflowResponse | null,
  publicationJob?: { id: string; status: string; lastError: string | null } | null,
  lang: string = 'en'
): CanonicalBlockerItem[] {
  const isVi = lang === 'vi';
  const missingInputs = reviewData?.missingInputs ?? workflowData?.facts.missingInputs ?? [];
  const blockingDrafts = reviewData?.blockingDrafts ?? workflowData?.content.blockingDrafts ?? [];
  const contentReadiness = reviewData?.contentReadiness ?? [];
  // `contentBlockers` is the compatibility flattening of `contentReadiness`.
  // Never render both representations for one review response.
  const contentBlockers = contentReadiness.length > 0
    ? []
    : reviewData?.contentBlockers ?? workflowData?.content.contentBlockers ?? [];
  const presentationErrors = reviewData?.presentationErrors ?? workflowData?.design.presentationErrors ?? [];

  const list: CanonicalBlockerItem[] = [];

  // 1. Facts Blockers
  if (missingInputs.length > 0) {
    const firstHandoff = mapMissingFactInput(missingInputs[0]);
    list.push({
      id: 'facts-missing',
      category: 'facts',
      title: isVi ? 'Thiếu thông tin bắt buộc trong Facts' : 'Missing Required Facts',
      description: isVi
        ? `Báo giá đang thiếu ${missingInputs.length} thông tin bắt buộc: ${missingInputs.join(', ')}.`
        : `The quotation is missing ${missingInputs.length} required fact(s): ${missingInputs.join(', ')}.`,
      ctaLabel: isVi ? 'Cập nhật thông tin khách' : 'Update Customer Facts',
      targetHandoff: firstHandoff,
    });
  }

  // 2. Content Advisory Drafts
  if (blockingDrafts.length > 0) {
    list.push({
      id: 'content-drafts',
      category: 'content',
      title: isVi ? 'Bản nháp nội dung chưa duyệt' : 'Unreviewed Content Drafts',
      description: isVi
        ? `Có ${blockingDrafts.length} bản nháp nội dung cần xem xét: ${blockingDrafts.join(', ')}.`
        : `There are ${blockingDrafts.length} content candidate(s) available for review: ${blockingDrafts.join(', ')}.`,
      ctaLabel: isVi ? 'Xem bản nháp Content' : 'Review Content Candidates',
      isAdvisory: true,
      targetHandoff: { stage: 'content' },
    });
  }

  // 3. Content Blockers
  contentBlockers.forEach((blocker: ContentBlocker) => {
    list.push({
      id: `content-blocker-${hashBlockerContent(blocker.sectionId, blocker.path, blocker.message)}`,
      category: 'content',
      title: isVi ? `Nội dung chưa hoàn thiện tại ${blocker.sectionId}` : `Content Blocker in ${blocker.sectionId}`,
      description: blocker.message,
      ctaLabel: isVi ? `Sửa phần ${blocker.sectionId}` : `Edit ${blocker.sectionId}`,
      targetHandoff: {
        stage: 'content',
        section: blocker.sectionId,
      },
    });
  });

  // 4. Content Readiness Issues
  contentReadiness.forEach((item: ContentReadiness) => {
    if (item.status) {
      list.push({
        id: `content-readiness-${hashBlockerContent(item.sectionId, item.label, item.status)}`,
        category: 'content',
        title: item.label,
        description: item.missing.map((m) => m.message).join('. ') || (isVi ? 'Nội dung chưa đầy đủ.' : 'Content incomplete.'),
        ctaLabel: item.targetStage === 'facts' ? (isVi ? 'Vào Facts' : 'Go to Facts') : (isVi ? 'Vào Content' : 'Go to Content'),
        targetHandoff: {
          stage: item.targetStage === 'facts' ? 'facts' : 'content',
          section: item.sectionId,
        },
      });
    }
  });

  // 5. Design / PDF Layout Blockers
  presentationErrors.forEach((error: string, idx: number) => {
    list.push(mapPresentationErrorToBlocker(error, idx, lang));
  });

  // 6. Asset Readiness Blockers
  const assetReadiness = reviewData?.assetReadiness;
  if (assetReadiness && !assetReadiness.ready && assetReadiness.missing && assetReadiness.missing.length > 0) {
    list.push({
      id: 'asset-missing',
      category: 'design',
      title: isVi
        ? `Thiếu ${assetReadiness.missing.length} hình ảnh tư liệu trên R2`
        : `Missing ${assetReadiness.missing.length} media asset(s) on R2`,
      description: isVi
        ? `Báo giá tham chiếu các hình ảnh chưa có trên thư viện R2: ${assetReadiness.missing.join(', ')}.`
        : `Quotation references assets not present in R2 catalogue: ${assetReadiness.missing.join(', ')}.`,
      ctaLabel: isVi ? 'Chọn ảnh Hero trên Design Canvas' : 'Choose Hero image on Design Canvas',
      targetHandoff: {
        stage: 'design',
        section: 'hero',
        source: '/hero/bannerImage',
        fieldId: 'hero.bannerImage',
      },
    });
  }

  // 7. Publication Job Blockers
  if (publicationJob?.status === 'failed') {
    list.push({
      id: 'publish-failed',
      category: 'publish',
      title: isVi ? 'Tác vụ xuất bản PDF thất bại' : 'PDF Publication Job Failed',
      description: publicationJob.lastError || (isVi ? 'Tác vụ render PDF nền bị lỗi.' : 'Background PDF rendering job failed.'),
      ctaLabel: isVi ? 'Kiểm tra cấu hình xuất bản' : 'Check Target Settings',
      targetHandoff: { stage: 'publish' },
    });
  }

  return list;
}

/**
 * Pure function: Group blockers by stage category.
 */
export function groupBlockersByCategory(
  items: CanonicalBlockerItem[]
): Record<BlockerCategory, CanonicalBlockerItem[]> {
  const groups: Record<BlockerCategory, CanonicalBlockerItem[]> = {
    facts: [],
    content: [],
    design: [],
    publish: [],
  };

  for (const item of items) {
    if (groups[item.category]) {
      groups[item.category].push(item);
    }
  }

  return groups;
}

/**
 * Pure function: Determine whether workflow has cleared all hard publication blockers.
 */
export function isWorkflowReady(items: CanonicalBlockerItem[]): boolean {
  return items.every((item) => item.isAdvisory === true);
}

export const workflowReconciler = {
  parseJsonPointer,
  mapPresentationErrorToBlocker,
  mapMissingFactInput,
  fromReviewResponse,
  groupBlockersByCategory,
  isWorkflowReady,
};
