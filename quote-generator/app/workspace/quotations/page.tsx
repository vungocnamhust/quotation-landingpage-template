import Link from "next/link";
import WorkspaceQuotationList from "../../../components/staff-workspace/WorkspaceQuotationList";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

export default function QuotationsPage() {
  return <main className="flex flex-col gap-6"><header className="flex flex-wrap items-end justify-between gap-4"><div><p className={cn(getTypographyClassName("overline"), "text-[var(--color-accent)]")}>Personal portfolio</p><h1 className={cn(getTypographyClassName("pageTitle"), "mt-2 text-[var(--color-on-surface)]")}>My quotations</h1></div><Link href="/workspace/quotations/new" className={cn(getTypographyClassName("buttonPrimary"), "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-5 py-3 text-[var(--color-accent)] shadow-xs transition-all hover:bg-[var(--color-surface-hover)]")}>New quotation</Link></header><WorkspaceQuotationList /></main>;
}
