import { FinanceApWorkspace } from "../../../../components/finance-ap/FinanceApWorkspace";
import { getTypographyClassName } from "../../../../config/typography";
import { cn } from "../../../../utils/cn";

export default function FinanceApPage() {
  return (
    <main className="flex flex-col gap-6">
      <header>
        <p className={cn(getTypographyClassName("overline"), "text-[var(--color-accent)]")}>Finance</p>
        <h1 className={cn(getTypographyClassName("pageTitle"), "mt-2 text-[var(--color-on-surface)]")}>AP Reconciliation</h1>
        <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
          Match supplier invoices to confirmed vouchers, approve, and record payments.
        </p>
      </header>
      <FinanceApWorkspace />
    </main>
  );
}
