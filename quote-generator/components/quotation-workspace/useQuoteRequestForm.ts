"use client";

import { useCallback, useState } from "react";
import { quotationFetch } from "../../lib/apiError.ts";
import {
  formStateToRequestPayload,
  getInitialQuoteRequestFormState,
  mapRequestToFormState,
  type QuoteRequestFormState,
} from "../../lib/quoteRequestPayload.ts";
import { tripAdapter } from "../../lib/rules/tripAdapter.ts";
import { tripReconciler, type CanonicalDay } from "../../lib/rules/tripReconciler.ts";
import { evaluateQuoteRequestReadiness } from "../../lib/rules/validationGates.ts";
import { toastAdapter } from "../../lib/rules/toastAdapter.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import type { BasicDayItem } from "./BasicItineraryDayGrid.tsx";
import type { DestinationRef, QuoteRequestItem, QuoteRequestRole } from "./factsTypes.ts";

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";

export type UseQuoteRequestFormOptions = {
  initialRequest?: QuoteRequestItem | null;
  initialRole?: QuoteRequestRole;
  onSuccess?: (saved: QuoteRequestItem) => void;
};

function getRequestPayload(request?: QuoteRequestItem | null): Record<string, unknown> {
  if (!request?.payload_json) return {};
  if (typeof request.payload_json === "string") {
    try {
      return JSON.parse(request.payload_json) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return request.payload_json as Record<string, unknown>;
}

export function useQuoteRequestForm({
  initialRequest,
  initialRole = "traveller",
  onSuccess,
}: UseQuoteRequestFormOptions = {}) {
  const { toast } = useToast();
  const [formState, setRawFormState] = useState<QuoteRequestFormState>(() =>
    initialRequest
      ? mapRequestToFormState(initialRequest)
      : getInitialQuoteRequestFormState(initialRole)
  );

  const [itineraryDays, setItineraryDays] = useState<BasicDayItem[]>(() => {
    if (!initialRequest) return [];
    const payload = getRequestPayload(initialRequest);
    const rawItinerary = payload.itinerary_days;
    return Array.isArray(rawItinerary) ? (rawItinerary as BasicDayItem[]) : [];
  });

  const [changeSummary, setChangeSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const setFormState = useCallback(
    (action: ((prev: QuoteRequestFormState) => QuoteRequestFormState) | QuoteRequestFormState) => {
      setRawFormState((prev) => {
        const next = typeof action === "function" ? action(prev) : action;
        const arrivalChanged = next.arrival_date !== prev.arrival_date;
        const departureChanged = next.departure_date !== prev.departure_date;

        if (arrivalChanged || departureChanged) {
          let canonical = tripAdapter.fromQuoteRequest(prev, itineraryDays);
          if (arrivalChanged) {
            canonical = tripReconciler.setStartDate(canonical, next.arrival_date || null);
          }
          if (departureChanged) {
            canonical = tripReconciler.setEndDate(canonical, next.departure_date || null);
          }
          const synced = tripAdapter.syncToQuoteRequest(canonical, next);
          setItineraryDays(synced.itineraryDays);
          return synced.formState;
        }

        return next;
      });
    },
    [itineraryDays]
  );

  const setField = useCallback(
    <K extends keyof QuoteRequestFormState>(key: K, value: QuoteRequestFormState[K]) => {
      setFormState((prev) => ({ ...prev, [key]: value }));
    },
    [setFormState]
  );

  const addItineraryDay = useCallback(
    (defaultPayload?: Partial<BasicDayItem>) => {
      const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
      const reconciled = tripReconciler.addDay(
        canonical,
        defaultPayload as Partial<CanonicalDay> | undefined
      );
      const synced = tripAdapter.syncToQuoteRequest(reconciled, formState);
      setRawFormState(synced.formState);
      setItineraryDays(synced.itineraryDays);
    },
    [formState, itineraryDays]
  );

  const removeItineraryDay = useCallback(
    (index: number) => {
      const removedDay = itineraryDays[index];
      const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
      const reconciled = tripReconciler.removeDay(canonical, index);
      const synced = tripAdapter.syncToQuoteRequest(reconciled, formState);
      setRawFormState(synced.formState);
      setItineraryDays(synced.itineraryDays);

      if (removedDay) {
        toast(
          `Removed Day ${index + 1}${removedDay.destination ? ` (${removedDay.destination})` : ""}`,
          "info"
        );
      }
    },
    [formState, itineraryDays, toast]
  );

  const updateItineraryDay = useCallback(
    (index: number, patch: Partial<BasicDayItem>) => {
      const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
      const reconciled = tripReconciler.updateDay(
        canonical,
        index,
        patch as Partial<CanonicalDay>
      );
      const synced = tripAdapter.syncToQuoteRequest(reconciled, formState);
      setRawFormState(synced.formState);
      setItineraryDays(synced.itineraryDays);
    },
    [formState, itineraryDays]
  );

  const applyRouteSequence = useCallback(
    (destinations: Array<string | DestinationRef>) => {
      const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
      const reconciled = tripReconciler.applyRouteSequence(canonical, destinations);
      const synced = tripAdapter.syncToQuoteRequest(reconciled, formState);
      setRawFormState(synced.formState);
      setItineraryDays(synced.itineraryDays);
      toast(
        `Applied route sequence (${synced.itineraryDays.length} day${synced.itineraryDays.length > 1 ? "s" : ""} generated).`,
        "info"
      );
    },
    [formState, itineraryDays, toast]
  );

  const setRole = useCallback((role: QuoteRequestRole) => {
    setRawFormState((prev) => ({ ...prev, role }));
  }, []);

  const resetForm = useCallback(() => {
    if (initialRequest) {
      setRawFormState(mapRequestToFormState(initialRequest));
      const payload = getRequestPayload(initialRequest);
      const rawItinerary = payload.itinerary_days;
      setItineraryDays(Array.isArray(rawItinerary) ? (rawItinerary as BasicDayItem[]) : []);
    } else {
      setRawFormState(getInitialQuoteRequestFormState(initialRole));
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

      // Pre-flight Client Validation Gate (Layer 1)
      const gateResult = evaluateQuoteRequestReadiness(formState, itineraryDays);
      if (!gateResult.passed) {
        const toastPayload = toastAdapter.fromGateResult(gateResult);
        if (toastPayload) {
          toast(toastPayload.message, toastPayload.type);
          setErrorMsg(toastPayload.message);
        }
        return null;
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
        const toastPayload = toastAdapter.fromApiError(err, fallbackError);
        toast(toastPayload.message, toastPayload.type);
        setErrorMsg(toastPayload.message);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [changeSummary, formState, initialRequest, itineraryDays, onSuccess, toast]
  );

  return {
    formState,
    setFormState,
    setField,
    setRole,
    itineraryDays,
    setItineraryDays,
    addItineraryDay,
    removeItineraryDay,
    updateItineraryDay,
    applyRouteSequence,
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

