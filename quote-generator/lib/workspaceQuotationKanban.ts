export type WorkspaceQuotationViewMode = "grid" | "table" | "kanban";

export type CommercialSummary = {
  currency: string | null;
  groupTotalAmountMinor: number | null;
};

export function normalizeWorkspaceQuotationView(value: string | null): WorkspaceQuotationViewMode {
  return value === "table" || value === "kanban" ? value : "grid";
}

export function formatCommercialTotal(commercial: CommercialSummary | undefined): string | null {
  const amount = commercial?.groupTotalAmountMinor;
  const currency = commercial?.currency;
  if (amount == null || !currency) return null;

  const fractionDigits = currency === "VND" ? 0 : 2;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: fractionDigits,
  }).format(amount / 10 ** fractionDigits);
}
