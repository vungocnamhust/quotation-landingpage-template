import { Suspense } from "react";
import { getTypographyClassName } from "../../../../config/typography";
import { cn } from "../../../../utils/cn";
import NewQuotationClient from "../../../../components/quotation-workspace/NewQuotationClient";

export default function WorkspaceNewQuotationPage() {
  return (
    <Suspense
      fallback={
        <div className={cn(getTypographyClassName("bodySm"), "p-8 text-[var(--color-muted)]")}>
          Loading quotation workspace…
        </div>
      }
    >
      <NewQuotationClient personalWorkspace />
    </Suspense>
  );
}
