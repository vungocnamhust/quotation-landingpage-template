"use client";

import { useState } from "react";
import { AlertTriangle, Plus } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { useToast } from "../../staff-workspace/ToastProvider.tsx";
import { RateEditorDrawer, type RateDrawerMode } from "./RateEditorDrawer.tsx";
import { useProductRates } from "./useProductRates.ts";
import { LIFECYCLE_STATUS_LABEL, type RateLifecycleStatus, type RateProfile } from "./types.ts";

type Props = {
  productId: string;
  productCategory?: string;
  defaultCurrency?: string | null;
};

function StatusBadge({ status }: { status: RateLifecycleStatus }) {
  const palette: Record<RateLifecycleStatus, string> = {
    draft: "bg-slate-100 text-slate-700",
    active: "bg-emerald-100 text-emerald-700",
    superseded: "bg-slate-100 text-slate-400",
    expired: "bg-rose-100 text-rose-700",
  };
  return (
    <span className={cn(getTypographyClassName("caption"), "rounded-full px-2 py-0.5", palette[status])}>
      {LIFECYCLE_STATUS_LABEL[status]}
    </span>
  );
}

function groupByVersionChain(rates: RateProfile[]): RateProfile[][] {
  const byId = new Map(rates.map((rate) => [rate.id, rate]));
  const roots = rates.filter((rate) => !rate.supersedes_rate_id || !byId.has(rate.supersedes_rate_id));
  return roots
    .map((root) => {
      const chain: RateProfile[] = [root];
      let current = root;
      // walk forward: find the rate that supersedes `current`
      // (small N per product; linear scan is fine)
      for (;;) {
        const next = rates.find((r) => r.supersedes_rate_id === current.id);
        if (!next) break;
        chain.push(next);
        current = next;
      }
      return chain.reverse();
    })
    .sort((a, b) => (b[0]?.valid_from ?? "").localeCompare(a[0]?.valid_from ?? ""));
}

export function RatePanel({ productId, productCategory, defaultCurrency }: Props) {
  const { toast } = useToast();
  const { rates, isLoading, mutate, activate, deleteDraft } = useProductRates(productId, "all");
  const [drawerMode, setDrawerMode] = useState<RateDrawerMode>(null);
  const [editingRate, setEditingRate] = useState<RateProfile | null>(null);

  const chains = groupByVersionChain(rates);

  const openCreate = () => {
    setEditingRate(null);
    setDrawerMode("create");
  };
  const openEdit = (rate: RateProfile) => {
    setEditingRate(rate);
    setDrawerMode("edit");
  };
  const openSupersede = (rate: RateProfile) => {
    setEditingRate(rate);
    setDrawerMode("supersede");
  };

  const handleActivate = async (rate: RateProfile) => {
    try {
      await activate(rate.id);
      await mutate();
      toast("Rate activated.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not activate rate.", "error");
    }
  };

  const handleDelete = async (rate: RateProfile) => {
    try {
      await deleteDraft(rate.id);
      await mutate();
      toast("Draft rate deleted.", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not delete draft.", "error");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>Rates</h3>
        <button
          type="button"
          onClick={openCreate}
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "flex items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3 py-1.5 text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] cursor-pointer"
          )}
        >
          <Plus size={14} aria-hidden="true" />
          <span>New rate</span>
        </button>
      </div>

      {isLoading ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Loading rates…</p>
      ) : chains.length === 0 ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          No rates yet — add the first seasonal price.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {chains.map((chain) => (
            <div
              key={chain[0].id}
              className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-3"
            >
              {chain.map((rate) => (
                <div key={rate.id} className="flex items-center justify-between gap-3 py-1">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
                        v{rate.version} · {rate.season_name || `${rate.valid_from} → ${rate.valid_to}`}
                      </span>
                      <StatusBadge status={rate.lifecycle_status} />
                      {rate.validation_flags_json.includes("OVERLAP_ACTIVE_RATE") ? (
                        <span
                          className={cn(
                            getTypographyClassName("caption"),
                            "flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-amber-700"
                          )}
                        >
                          <AlertTriangle size={12} aria-hidden="true" />
                          Overlaps another active rate
                        </span>
                      ) : null}
                    </div>
                    <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
                      {rate.valid_from} → {rate.valid_to} · {rate.currency} · {rate.lines.length} line(s)
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {rate.lifecycle_status === "draft" ? (
                      <>
                        <button
                          type="button"
                          onClick={() => openEdit(rate)}
                          className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)] hover:underline cursor-pointer")}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleActivate(rate)}
                          className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)] hover:underline cursor-pointer")}
                        >
                          Activate
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(rate)}
                          className={cn(getTypographyClassName("caption"), "text-rose-600 hover:underline cursor-pointer")}
                        >
                          Delete
                        </button>
                      </>
                    ) : null}
                    {rate.lifecycle_status === "active" ? (
                      <button
                        type="button"
                        onClick={() => openSupersede(rate)}
                        className={cn(getTypographyClassName("caption"), "text-[var(--color-accent)] hover:underline cursor-pointer")}
                      >
                        Supersede (new price)
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <RateEditorDrawer
        mode={drawerMode}
        productId={productId}
        productCategory={productCategory}
        defaultCurrency={defaultCurrency}
        editingRate={editingRate}
        onClose={() => setDrawerMode(null)}
        onSaved={() => void mutate()}
      />
    </div>
  );
}

export default RatePanel;
