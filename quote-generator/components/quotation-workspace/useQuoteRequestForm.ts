"use client";

import { useCallback, useState } from "react";
import { apiErrorMessage, quotationFetch } from "../../lib/apiError";
import {
  formStateToRequestPayload,
  getInitialQuoteRequestFormState,
  mapRequestToFormState,
  type QuoteRequestFormState,
} from "../../lib/quoteRequestPayload";
import type { BasicDayItem } from "./BasicItineraryDayGrid";
import type { QuoteRequestItem, QuoteRequestRole } from "./factsTypes";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

export type UseQuoteRequestFormOptions = {
  initialRequest?: QuoteRequestItem | null;
  initialRole?: QuoteRequestRole;
  onSuccess?: (saved: QuoteRequestItem) => void;
};

export function useQuoteRequestForm({
  initialRequest,
  initialRole = "traveller",
  onSuccess,
}: UseQuoteRequestFormOptions = {}) {
  const [formState, setFormState] = useState<QuoteRequestFormState>(() =>
    initialRequest
      ? mapRequestToFormState(initialRequest)
      : getInitialQuoteRequestFormState(initialRole)
  );

  const [itineraryDays, setItineraryDays] = useState<BasicDayItem[]>(() => {
    if (!initialRequest) return [];
    const rawItinerary = (initialRequest.payload_json || {}).itinerary_days;
    return Array.isArray(rawItinerary) ? (rawItinerary as BasicDayItem[]) : [];
  });

  const [changeSummary, setChangeSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const setField = useCallback(
    <K extends keyof QuoteRequestFormState>(key: K, value: QuoteRequestFormState[K]) => {
      setFormState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const setRole = useCallback((role: QuoteRequestRole) => {
    setFormState((prev) => ({ ...prev, role }));
  }, []);

  const resetForm = useCallback(() => {
    if (initialRequest) {
      setFormState(mapRequestToFormState(initialRequest));
      const rawItinerary = (initialRequest.payload_json || {}).itinerary_days;
      setItineraryDays(Array.isArray(rawItinerary) ? (rawItinerary as BasicDayItem[]) : []);
    } else {
      setFormState(getInitialQuoteRequestFormState(initialRole));
      setItineraryDays([]);
    }
    setChangeSummary("");
    setErrorMsg(null);
  }, [initialRequest, initialRole]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent): Promise<QuoteRequestItem | null> => {
      if (e) {
        e.preventDefault();
      }
      setSubmitting(true);
      setErrorMsg(null);

      const payload = formStateToRequestPayload(formState, itineraryDays, changeSummary);
      const isEdit = Boolean(initialRequest?.id);
      const endpoint = isEdit
        ? `${API_BASE}/api/v2/workspace/requests/${encodeURIComponent(initialRequest!.id)}`
        : `${API_BASE}/api/v2/workspace/requests`;
      const method = isEdit ? "PUT" : "POST";
      const fallbackError = isEdit
        ? "Could not save changes to request."
        : "Could not create quote request.";

      try {
        const saved = await quotationFetch<QuoteRequestItem>(
          endpoint,
          {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          },
          fallbackError
        );

        if (saved) {
          onSuccess?.(saved);
          return saved;
        }
        return null;
      } catch (err: unknown) {
        setErrorMsg(apiErrorMessage(err));
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [changeSummary, formState, initialRequest, itineraryDays, onSuccess]
  );

  return {
    formState,
    setFormState,
    setField,
    setRole,
    itineraryDays,
    setItineraryDays,
    changeSummary,
    setChangeSummary,
    submitting,
    errorMsg,
    setErrorMsg,
    handleSubmit,
    resetForm,
    isEdit: Boolean(initialRequest?.id),
    currentRevision: initialRequest?.current_revision || 1,
    nextRevision: (initialRequest?.current_revision || 1) + 1,
  };
}
