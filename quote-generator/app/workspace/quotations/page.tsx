import { Plus } from "lucide-react";
import WorkspaceQuotationList from "../../../components/staff-workspace/WorkspaceQuotationList";
import { WorkspaceNavigationLink } from "../../../components/staff-workspace/WorkspaceNavigation";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

export default function QuotationsPage() {
  return (
    <main className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]"
            )}
          >
            Personal portfolio
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-2 text-[var(--color-on-surface)]"
            )}
          >
            My quotations
          </h1>
        </div>
        <WorkspaceNavigationLink
          href="/workspace/quotations/new"
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-5 py-3 text-[var(--color-accent)] shadow-xs transition-all hover:bg-[var(--color-surface-hover)]"
          )}
        >
          <Plus size={16} aria-hidden="true" />
          <span>New quotation</span>
        </WorkspaceNavigationLink>
      </header>
      <WorkspaceQuotationList />
    </main>
  );
}
