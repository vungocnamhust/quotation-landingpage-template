import { OperationsBoard } from "../../../components/operations/OperationsBoard";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";

export default function OperationsPage() {
  return (
    <main className="flex flex-col gap-6">
      <header>
        <p className={cn(getTypographyClassName("overline"), "text-[var(--color-accent)]")}>Post-deposit operations</p>
        <h1 className={cn(getTypographyClassName("pageTitle"), "mt-2 text-[var(--color-on-surface)]")}>Operations</h1>
        <p className={cn(getTypographyClassName("bodySm"), "mt-1 text-[var(--color-muted)]")}>
          What&apos;s not booked yet, what deadline is next, and what&apos;s about to burn.
        </p>
      </header>
      <OperationsBoard />
    </main>
  );
}
