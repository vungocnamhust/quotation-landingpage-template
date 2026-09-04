/**
 * Centralized Costing Glossary Dictionary
 * Single Source of Truth for domain concepts used throughout Costing Workbench.
 */

export type CostingConceptKey =
  | "CURRENCY"
  | "MARKUP_BPS"
  | "ROUND_UP_TO"
  | "COST"
  | "SELL"
  | "MARGIN"
  | "AI_DRAFTER"
  | "SOURCE_MODE"
  | "DAY_NUMBER"
  | "QTY_UNIT"
  | "QTY_TIME"
  | "SERVICE_DATE"
  | "PRODUCT_SELECT"
  | "SELL_OVERRIDE"
  | "SERVICE_NOTE"
  | "CREATE_QUOTATION_CTA"
  | "ADD_LINE";

export interface CostingGlossaryEntry {
  key: CostingConceptKey;
  title: string;
  description: string;
  example?: string;
}

export const ALL_COSTING_CONCEPT_KEYS: readonly CostingConceptKey[] = [
  "CURRENCY",
  "MARKUP_BPS",
  "ROUND_UP_TO",
  "COST",
  "SELL",
  "MARGIN",
  "AI_DRAFTER",
  "SOURCE_MODE",
  "DAY_NUMBER",
  "QTY_UNIT",
  "QTY_TIME",
  "SERVICE_DATE",
  "PRODUCT_SELECT",
  "SELL_OVERRIDE",
  "SERVICE_NOTE",
  "CREATE_QUOTATION_CTA",
  "ADD_LINE",
] as const;

export const COSTING_GLOSSARY: Record<CostingConceptKey, CostingGlossaryEntry> = {
  CURRENCY: {
    key: "CURRENCY",
    title: "Tiền tệ cơ sở (Base Currency)",
    description:
      "Đồng tiền thanh toán chuẩn cho dự toán (VND, USD, EUR, GBP, AUD). Tỷ giá FX sẽ tự động quy đổi mọi chi phí của nhà cung cấp về đồng tiền cơ sở này. Lưu ý: Tiền tệ sẽ bị khóa sau khi dự toán đã có dòng dịch vụ.",
    example: "VND, USD, EUR (FX quy đổi tự động)",
  },
  MARKUP_BPS: {
    key: "MARKUP_BPS",
    title: "Tỷ lệ Markup (BPS)",
    description:
      "Tỷ lệ lợi nhuận mục tiêu tính theo Basis Points (1% = 100 BPS). Hệ thống tính giá bán = Chi phí / (1 - Markup) hoặc Chi phí × (1 + Markup).",
    example: "1500 BPS = 15%, 2000 BPS = 20%",
  },
  ROUND_UP_TO: {
    key: "ROUND_UP_TO",
    title: "Làm tròn giá bán (Round up to)",
    description:
      "Bước làm tròn lên (Ceil) cho tổng giá bán khách hàng (đơn vị minor) để tạo mức giá thanh toán chẵn, đẹp mắt.",
    example: "10000 → 2.451.200 làm tròn lên 2.460.000 VND",
  },
  COST: {
    key: "COST",
    title: "Tổng chi phí ròng (Net Cost)",
    description:
      "Tổng chi phí net phải trả cho các nhà cung cấp: tổng(Đơn giá net × Số lượng đơn vị × Thời lượng/Lần) quy đổi về tiền tệ cơ sở.",
    example: "sum(Unit Cost × Qty Unit × Qty Time)",
  },
  SELL: {
    key: "SELL",
    title: "Tổng giá bán đề xuất (Gross Sell)",
    description:
      "Tổng giá bán khách hàng sau khi cộng Markup BPS, áp dụng bước làm tròn hoặc giá ghi đè thủ công.",
    example: "Cost + Markup BPS (đã làm tròn) hoặc Sell Override",
  },
  MARGIN: {
    key: "MARGIN",
    title: "Lợi nhuận gộp & Tỷ suất (Margin)",
    description:
      "Lợi nhuận gộp và tỷ suất lợi nhuận: Số tiền lãi = (Giá bán - Chi phí) và Tỷ lệ lãi = (Giá bán - Chi phí) / Giá bán × 100%.",
    example: "(Sell - Cost) và (Sell - Cost) / Sell × 100%",
  },
  AI_DRAFTER: {
    key: "AI_DRAFTER",
    title: "Trợ lý AI dự thảo dịch vụ (AI Drafter)",
    description:
      "Trợ lý AI phân tích ngày và điểm đến trong hành trình để tự động tạo danh sách dịch vụ đề xuất (khách sạn, xe, tour) khớp từ danh mục đối tác.",
    example: "Phân tích điểm đến → Gợi ý dịch vụ từ catalog",
  },
  SOURCE_MODE: {
    key: "SOURCE_MODE",
    title: "Chế độ nguồn dịch vụ (Catalog vs Manual)",
    description:
      "Chọn từ danh mục giá đối tác đã ký kết (Pick from catalog) hoặc tự nhập tay các chi phí phát sinh ngoài hợp đồng (Type manually như tip, vé cầu đường, phụ phí).",
    example: "Catalog: Giá hợp đồng; Manual: Chi phí phát sinh",
  },
  DAY_NUMBER: {
    key: "DAY_NUMBER",
    title: "Ngày hành trình (Day #)",
    description:
      "Gán dịch vụ vào ngày cụ thể trong hành trình (Ngày 1, 2...). Để trống đối với các dịch vụ bao quát toàn tour như bảo hiểm, SIM du lịch, phí visa.",
    example: "1, 2... hoặc để trống cho toàn chuyến",
  },
  QTY_UNIT: {
    key: "QTY_UNIT",
    title: "Số lượng đơn vị (Qty Unit)",
    description:
      "Số lượng đơn vị dịch vụ sử dụng (số khách pax, số phòng khách sạn, số xe vận chuyển, số vé tham quan).",
    example: "2 khách, 1 phòng đôi, 1 xe 16 chỗ",
  },
  QTY_TIME: {
    key: "QTY_TIME",
    title: "Thời lượng / Chu kỳ (Qty Time)",
    description:
      "Thời lượng hoặc số chu kỳ sử dụng dịch vụ (số đêm lưu trú khách sạn, số ngày thuê xe, số lượt dịch vụ).",
    example: "3 đêm khách sạn, 2 ngày thuê xe",
  },
  SERVICE_DATE: {
    key: "SERVICE_DATE",
    title: "Ngày sử dụng dịch vụ (Service Date)",
    description:
      "Ngày cụ thể diễn ra dịch vụ (dd/mm/yyyy). Dùng để đối soát với nhà cung cấp và áp dụng bảng giá theo mùa/thời điểm hiệu lực.",
    example: "dd/mm/yyyy (đối soát & tra cứu giá mùa)",
  },
  PRODUCT_SELECT: {
    key: "PRODUCT_SELECT",
    title: "Chọn sản phẩm danh mục (Product Select)",
    description:
      "Tìm kiếm và chọn sản phẩm từ catalog đối tác để tự động nạp bảng giá net, điều kiện áp dụng và thông tin nhà cung cấp.",
    example: "Tìm kiếm sản phẩm → Tự điền giá net & nhà cung cấp",
  },
  SELL_OVERRIDE: {
    key: "SELL_OVERRIDE",
    title: "Đè giá bán thủ công (Sell Override)",
    description:
      "Ghi đè giá bán khách theo số tiền trực tiếp (minor units), bỏ qua công thức tính markup tự động (dùng cho dịch vụ phi lợi nhuận, thu hộ).",
    example: "Bỏ trống để tính tự động, hoặc nhập giá bán cố định",
  },
  SERVICE_NOTE: {
    key: "SERVICE_NOTE",
    title: "Ghi chú dịch vụ (Service Note)",
    description:
      "Ghi chú nghiệp vụ nội bộ điều hành (ví dụ: yêu cầu phòng tầng cao view biển, trẻ em dưới 6 tuổi miễn phí, ăn sáng bao gồm).",
    example: "Tầng cao view biển, trẻ em miễn phí",
  },
  CREATE_QUOTATION_CTA: {
    key: "CREATE_QUOTATION_CTA",
    title: "Tạo báo giá từ dự toán (Create Quotation)",
    description:
      "Chuyển tiếp toàn bộ cấu trúc dữ liệu dự toán (chi phí, dịch vụ, giá bán) sang bước khởi tạo báo giá chính thức trong Quotation Intake & Facts mà không cần nhập lại dữ liệu.",
    example: "Dự toán → Quotation Intake & Facts",
  },
  ADD_LINE: {
    key: "ADD_LINE",
    title: "Thêm dòng dịch vụ (Add Line)",
    description:
      "Lưu dòng dịch vụ hiện tại vào bảng dự toán và tự động cập nhật lại tổng chi phí, giá bán và biên lợi nhuận.",
    example: "Ghi nhận dòng dịch vụ vào Costing Sheet",
  },
};

/**
 * Retrieve glossary entry with safe fallback.
 */
export function getCostingGlossary(key: CostingConceptKey | string): CostingGlossaryEntry {
  const entry = COSTING_GLOSSARY[key as CostingConceptKey];
  if (entry) return entry;
  return {
    key: key as CostingConceptKey,
    title: String(key),
    description: `Khái niệm dự toán: ${key}`,
  };
}

export interface ResolveTooltipContentInput {
  conceptKey?: CostingConceptKey | string;
  title?: string;
  content?: string;
  text?: string;
  example?: string;
}

export interface ResolvedTooltipContent {
  title: string;
  content: string;
  example?: string;
}

/**
 * Resolves title, content, and example by prioritizing explicit custom props
 * with automatic fallback to the Centralized Costing Glossary.
 */
export function resolveTooltipContent(input: ResolveTooltipContentInput): ResolvedTooltipContent {
  const glossary = input.conceptKey ? getCostingGlossary(input.conceptKey) : null;
  const title = input.title ?? glossary?.title ?? "";
  const content = input.content ?? input.text ?? glossary?.description ?? "";
  const example = input.example ?? glossary?.example;
  return { title, content, example };
}
