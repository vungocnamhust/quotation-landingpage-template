"use client";

import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import {
  createAccommodation,
  listAccommodations,
  updateAccommodation,
  updateAccommodationStatus,
  uploadAccommodationAsset,
  type AccommodationProfile,
  type AccommodationProfileInput,
} from "../../../lib/quotationApi";
import type { DestinationRef } from "../../destination/types";

export const blankAccommodationInput = (): AccommodationProfileInput => ({
  destinationId: "",
  name: "",
  room_type: null,
  intro: null,
  phone: null,
  display_city: null,
  display_date: null,
  hotel_asset: null,
  room_asset: null,
});

export function profileToInput(profile: AccommodationProfile): AccommodationProfileInput {
  return {
    destinationId: profile.destination_id,
    name: profile.name,
    room_type: profile.room_type,
    intro: profile.intro,
    phone: profile.phone,
    display_city: profile.display_city,
    display_date: profile.display_date,
    hotel_asset: profile.hotel_asset,
    room_asset: profile.room_asset,
  };
}

export function useAccommodationManager(
  enabled: boolean,
  activeFilter: "all" | "true" | "false",
  deferredSearch: string
) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<AccommodationProfile | null>(null);
  const [draft, setDraft] = useState<AccommodationProfileInput>(blankAccommodationInput);
  const [destinationRef, setDestinationRef] = useState<DestinationRef | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  // Fetch accommodations via SWR if active category is accommodations
  const queryKey = ["accommodations", activeFilter, deferredSearch];
  const {
    data: profileResponse,
    error,
    isLoading,
    mutate: mutateProfiles,
  } = useSWR(
    enabled ? queryKey : null,
    ([, active, query]) =>
      listAccommodations({ active: active as "true" | "false" | "all", query })
  );

  const items = useMemo(() => profileResponse?.items ?? [], [profileResponse]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setDraft(blankAccommodationInput());
    setDestinationRef(null);
    setMessage("");
    setIsDrawerOpen(true);
  }, []);

  const openEdit = useCallback((profile: AccommodationProfile) => {
    setEditing(profile);
    setDraft(profileToInput(profile));
    setDestinationRef(profile.destination_ref);
    setMessage("");
    setIsDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setIsDrawerOpen(false);
  }, []);

  const saveAccommodation = useCallback(async () => {
    if (!destinationRef || !draft.name.trim()) {
      setMessage("Destination and accommodation name are required.");
      return;
    }
    setPending(true);
    try {
      const input = { ...draft, destinationId: destinationRef.id };
      if (editing) {
        await updateAccommodation(editing.id, input);
      } else {
        await createAccommodation(input);
      }
      await mutateProfiles();
      setIsDrawerOpen(false);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Accommodation could not be saved."
      );
    } finally {
      setPending(false);
    }
  }, [destinationRef, draft, editing, mutateProfiles]);

  const uploadAsset = useCallback(
    async (target: "hotel_asset" | "room_asset", file: File) => {
      if (!editing) return;
      setPending(true);
      try {
        const uploaded = await uploadAccommodationAsset(
          file,
          editing.id,
          target === "hotel_asset" ? "exteriors" : "interiors"
        );
        setDraft((current) => ({ ...current, [target]: uploaded.r2Key }));
        setMessage("Asset uploaded. Save profile to confirm modifications.");
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Asset upload failed.");
      } finally {
        setPending(false);
      }
    },
    [editing]
  );

  const toggleAccommodationStatus = useCallback(
    async (profile: AccommodationProfile) => {
      setPending(true);
      try {
        await updateAccommodationStatus(profile.id, !profile.is_active);
        await mutateProfiles();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Status update failed.");
      } finally {
        setPending(false);
      }
    },
    [mutateProfiles]
  );

  return {
    items,
    isLoading,
    error,
    isDrawerOpen,
    editing,
    draft,
    destinationRef,
    message,
    pending,
    setDraft,
    setDestinationRef,
    openCreate,
    openEdit,
    closeDrawer,
    saveAccommodation,
    uploadAsset,
    toggleAccommodationStatus,
    mutateProfiles,
  };
}
