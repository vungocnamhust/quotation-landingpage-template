"use client";

import Link from "next/link";
import { User, Briefcase, ArrowRight } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes";

type Props = {
  items: QuoteRequestItem[];
};

export function WorkspaceRequestTable({ items }: Props) {
  return (
    <div className="overflow-x-auto rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)]">
      <table className="w-full text-left text-[var(--color-on-surface)]">
        <thead className="border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)]">
          <tr>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              ID / Created
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              Role & Requester
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              Company / Market
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              Destination & Dates
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              Party Size
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3")}>
              Status
            </th>
            <th scope="col" className={cn(getTypographyClassName("overline"), "px-4 py-3 text-right")}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)]">
          {items.map((item) => {
            const isTraveller = item.role === "traveller";
            const title = item.customer_name || (isTraveller ? "Anonymous Traveller" : "Anonymous Advisor");
            const destinationsText = item.destinations?.length > 0 ? item.destinations.join(" & ") : "Not specified";
            const datesText = item.raw_dates_text || (item.start_date ? `${item.start_date} ${item.end_date ? `- ${item.end_date}` : ""}` : "Dates flexible");

            const statusLabel =
              item.status === "quotation_created"
                ? "Quotation Created"
                : item.status === "under_review"
                ? "Under Review"
                : item.status === "archived"
                ? "Archived"
                : "New Request";


            const statusClass =
              item.status === "quotation_created"
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : item.status === "under_review"
                ? "bg-amber-50 text-amber-700 border-amber-200"
                : item.status === "archived"
                ? "bg-gray-50 text-gray-600 border-gray-200"
                : "bg-blue-50 text-blue-700 border-blue-200";

            return (
              <tr key={item.id} className="hover:bg-[var(--color-surface-muted)] transition-colors">
                <td className={cn(getTypographyClassName("caption"), "px-4 py-3 whitespace-nowrap text-[var(--color-muted)]")}>
                  <div>{item.id}</div>
                  <div className="text-[var(--color-muted)]">
                    {new Date(item.created_at).toLocaleDateString()}
                  </div>
                </td>

                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        getTypographyClassName("caption"),
                        "flex h-6 w-6 items-center justify-center rounded-full border shrink-0",
                        isTraveller ? "bg-sky-50 text-sky-700 border-sky-200" : "bg-purple-50 text-purple-700 border-purple-200"
                      )}
                    >
                      {isTraveller ? <User size={12} aria-hidden="true" /> : <Briefcase size={12} aria-hidden="true" />}
                    </span>
                    <Link
                      href={`/workspace/requests/${item.id}`}
                      className={cn(
                        getTypographyClassName("bodySm"),
                        "text-[var(--color-on-surface)] hover:text-[var(--color-accent)] transition-colors"
                      )}
                    >
                      {title}
                    </Link>
                  </div>
                </td>

                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                    {item.company_name || "Direct Client"} {item.market ? `(${item.market})` : ""}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <div className={cn(getTypographyClassName("bodySm"), "truncate max-w-[200px]")}>
                    {destinationsText}
                  </div>
                  <div className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] truncate max-w-[200px]")}>
                    {datesText}
                  </div>
                </td>

                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                    {item.adults || 2} Adults {item.children ? `, ${item.children} Kids` : ""}
                  </span>
                </td>

                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={cn(getTypographyClassName("caption"), "rounded-full px-2.5 py-0.5 border", statusClass)}>
                    {statusLabel}
                  </span>
                </td>

                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <Link
                    href={`/workspace/requests/${item.id}`}
                    className={cn(
                      getTypographyClassName("caption"),
                      "inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
                    )}
                  >
                    <span>View Detail</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

