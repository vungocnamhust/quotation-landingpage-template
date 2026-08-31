"use client";

import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionPayload, IngestionResolutionAction, IngestionResolutionEntry } from "./types.ts";

const ACTION_LABEL: Record<IngestionResolutionAction, string> = {
  create: "Create",
  update: "Update",
  supersede_rate: "Supersede rate",
  skip_duplicate: "Skip (duplicate)",
  needs_input: "Needs input",
};

const ACTION_STYLE: Record<IngestionResolutionAction, string> = {
  create: "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
  update: "bg-sky-500/10 border-sky-500/30 text-sky-600 dark:text-sky-400",
  supersede_rate: "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400",
  skip_duplicate: "bg-slate-500/10 border-slate-500/30 text-slate-500 dark:text-slate-400",
  needs_input: "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400",
};

function sourceQuoteFor(entry: IngestionResolutionEntry, payload: IngestionPayload): string {
  const [collection, indexText] = entry.entity_ref.replace(/^\//, "").split("/");
  const index = Number(indexText);
  if (entry.entity_type === "supplier") return payload.supplier?.source_quote ?? "";
  if (entry.entity_type === "product" && collection === "products") return payload.products[index]?.source_quote ?? "";
  if (entry.entity_type === "rate" && collection === "rate_groups") return payload.rate_groups[index]?.source_quote ?? "";
  return "";
}

function titleFor(entry: IngestionResolutionEntry, payload: IngestionPayload): string {
  const [collection, indexText] = entry.entity_ref.replace(/^\//, "").split("/");
  const index = Number(indexText);
  if (entry.entity_type === "supplier") return payload.supplier?.name_text ?? "Supplier";
  if (entry.entity_type === "product" && collection === "products") return payload.products[index]?.title_text ?? "Product";
  if (entry.entity_type === "rate" && collection === "rate_groups") return payload.rate_groups[index]?.product_title_text ?? "Rate";
  return entry.entity_ref;
}

interface Props {
  entries: IngestionResolutionEntry[];
  payload: IngestionPayload;
}

export function DiffViewer({ entries, payload }: Props) {
  if (entries.length === 0) return null;

  return (
    <section className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-xs">
      <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Diff Viewer</h2>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr className="border-b border-[var(--color-border-strong)]">
              <th className={cn(getTypographyClassName("label"), "px-3 py-2 text-left text-[var(--color-muted)]")}>
                Original quote
              </th>
              <th className={cn(getTypographyClassName("label"), "px-3 py-2 text-left text-[var(--color-muted)]")}>
                Existing in DB
              </th>
              <th className={cn(getTypographyClassName("label"), "px-3 py-2 text-left text-[var(--color-muted)]")}>
                Will become
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.entity_ref} className="border-b border-[var(--color-border-strong)] align-top last:border-b-0">
                <td className={cn(getTypographyClassName("bodySm"), "px-3 py-3 text-[var(--color-on-surface)]")}>
                  <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{titleFor(entry, payload)}</p>
                  <blockquote className={cn(getTypographyClassName("quote"), "mt-1 border-l-2 border-[var(--color-border-strong)] pl-3")}>
                    “{sourceQuoteFor(entry, payload)}”
                  </blockquote>
                </td>
                <td className={cn(getTypographyClassName("bodySm"), "px-3 py-3 text-[var(--color-on-surface)]")}>
                  {entry.matched_id ? entry.matched_id : <span className="text-[var(--color-muted)]">— none, will be new —</span>}
                </td>
                <td className="px-3 py-3">
                  <span
                    className={cn(
                      getTypographyClassName("label"),
                      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
                      ACTION_STYLE[entry.action],
                    )}
                  >
                    {ACTION_LABEL[entry.action]}
                  </span>
                  <p className={cn(getTypographyClassName("caption"), "mt-1.5 text-[var(--color-muted)]")}>{entry.evidence}</p>
                  {entry.action === "supersede_rate" ? (
                    <p className={cn(getTypographyClassName("caption"), "mt-1 text-amber-600 dark:text-amber-400")}>
                      The current active rate&apos;s price will be frozen (superseded), not overwritten.
                    </p>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
