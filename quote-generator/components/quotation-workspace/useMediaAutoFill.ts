"use client";

import { useState, useTransition } from "react";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import type { MediaWorkspace } from "./MediaSlotRenderer.tsx";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

export type MediaAutoFillResult = {
  ok: boolean;
  applied: boolean;
  dryRun?: boolean;
  appliedCount: number;
  hasChanges: boolean;
  message?: string;
  rationale?: Array<{ fieldId: string; candidateCount: number; reason: string }>;
  currentRevision?: number;
};

export function useMediaAutoFill(workspace: MediaWorkspace) {
  const { toast } = useToast();
  const [message, setMessage] = useState<string>("");
  const [pending, startTransition] = useTransition();
  const [lastResult, setLastResult] = useState<MediaAutoFillResult | null>(null);

  const generate = (dryRun = false) =>
    startTransition(async () => {
      const { quotationId, lang, currentRevision, onSaved } = workspace;
      if (!quotationId || !lang || currentRevision === undefined) {
        const err = "Quotation workspace is not ready for media auto-fill.";
        setMessage(err);
        toast(err, "error");
        return;
      }

      try {
        const response = await quotationFetch<MediaAutoFillResult>(
          `${API_BASE}/api/v2/quotations/${quotationId}/facts/media-defaults?lang=${encodeURIComponent(lang)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ baseRevision: currentRevision, dryRun }),
          },
          "Missing media could not be generated."
        );

        setLastResult(response);

        if (response.hasChanges && response.applied) {
          const count = response.appliedCount ?? response.rationale?.length ?? 0;
          const msg = `✨ Successfully auto-assigned ${count} brochure ${count === 1 ? "photo" : "photos"} from R2.`;
          setMessage(msg);
          toast(msg, "success");
          if (onSaved) {
            await onSaved();
          }
        } else if (response.hasChanges && response.dryRun) {
          const count = response.appliedCount ?? response.rationale?.length ?? 0;
          const msg = `Found ${count} matching default photos ready to assign.`;
          setMessage(msg);
          toast(msg, "info");
        } else {
          const msg = response.message || "No new matching photos found in R2 catalogue.";
          setMessage(msg);
          toast(msg, "info");
        }
      } catch (error) {
        const err = apiErrorMessage(error);
        setMessage(err);
        toast(err, "error");
      }
    });

  return {
    generate,
    pending,
    message,
    lastResult,
  };
}
