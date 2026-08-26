import { Plus } from "lucide-react";
import WorkspaceQuotationList from "../../components/staff-workspace/WorkspaceQuotationList";
import { WorkspaceNavigationLink } from "../../components/staff-workspace/WorkspaceNavigation";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";

export default function WorkspacePage() {
  return (
    <main className="flex flex-col gap-7">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p
            className={cn(
              getTypographyClassName("overline"),
              "text-[var(--color-accent)]"
            )}
          >
            Travel Designer desk
          </p>
          <h1
            className={cn(
              getTypographyClassName("pageTitle"),
              "mt-2 text-[var(--color-on-surface)]"
            )}
          >
            Keep the journey moving.
          </h1>
          <p
            className={cn(
              getTypographyClassName("bodyLg"),
              "mt-3 text-[var(--color-muted)]"
            )}
          >
            Your recently updated quotations, ready for the next decision.
          </p>
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

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            Continue working
          </h2>
          <WorkspaceNavigationLink
            href="/workspace/quotations"
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "text-[var(--color-on-surface)] transition-colors hover:text-[var(--color-accent)]"
            )}
          >
            View all
          </WorkspaceNavigationLink>
        </div>
        <WorkspaceQuotationList dashboard />
      </section>
    </main>
  );
}
