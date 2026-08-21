"use client";

import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import {
  createDestination,
  listDestinationsCatalog,
  updateDestination,
  updateDestinationStatus,
  type DestinationCatalogInput,
  type DestinationProfile,
} from "../../../lib/quotationApi.ts";

export const blankDestinationInput = (): DestinationCatalogInput => ({
  canonicalName: "",
  slug: "",
  countrySlug: "vietnam",
  regionSlug: null,
  provinceSlug: null,
  latitude: 0,
  longitude: 0,
  aliases: [],
});

export function profileToInput(profile: DestinationProfile): DestinationCatalogInput {
  return {
    canonicalName: profile.name,
    slug: profile.slug,
    countrySlug: profile.countrySlug,
    regionSlug: profile.regionSlug,
    provinceSlug: profile.provinceSlug,
    latitude: profile.latitude ?? 0,
    longitude: profile.longitude ?? 0,
    aliases: profile.aliases ?? [],
  };
}

export function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

export function useDestinationManager(
  enabled: boolean,
  activeFilter: "all" | "true" | "false",
  deferredSearch: string,
  countryFilter?: string
) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<DestinationProfile | null>(null);
  const [draft, setDraft] = useState<DestinationCatalogInput>(blankDestinationInput);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  // Fetch destinations via SWR if active category is destinations
  const queryKey = ["destinations", activeFilter, deferredSearch, countryFilter ?? ""];
  const {
    data: destinationResponse,
    error,
    isLoading,
    mutate: mutateDestinations,
  } = useSWR(
    enabled ? queryKey : null,
    ([, active, query, country]) =>
      listDestinationsCatalog({
        active: active as "true" | "false" | "all",
        query,
        countrySlug: country || undefined,
        limit: 100,
      })
  );

  const items = useMemo(() => destinationResponse?.items ?? [], [destinationResponse]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setDraft(blankDestinationInput());
    setMessage("");
    setIsDrawerOpen(true);
  }, []);

  const openEdit = useCallback((profile: DestinationProfile) => {
    setEditing(profile);
    setDraft(profileToInput(profile));
    setMessage("");
    setIsDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setIsDrawerOpen(false);
  }, []);

  const saveDestination = useCallback(async () => {
    if (!draft.canonicalName.trim()) {
      setMessage("Destination canonical name is required.");
      return;
    }
    if (!draft.slug.trim()) {
      setMessage("Destination slug is required.");
      return;
    }
    if (draft.latitude < -90 || draft.latitude > 90) {
      setMessage("Latitude must be between -90 and 90.");
      return;
    }
    if (draft.longitude < -180 || draft.longitude > 180) {
      setMessage("Longitude must be between -180 and 180.");
      return;
    }

    setPending(true);
    setMessage("");
    try {
      const normalizedAliases = Array.from(
        new Set(
          draft.aliases
            .map((a) => a.trim().toLowerCase())
            .filter((a) => Boolean(a))
        )
      );

      const input: DestinationCatalogInput = {
        ...draft,
        canonicalName: draft.canonicalName.trim(),
        slug: draft.slug.trim(),
        aliases: normalizedAliases,
      };

      if (editing) {
        await updateDestination(editing.id, input);
      } else {
        await createDestination(input);
      }
      await mutateDestinations();
      setIsDrawerOpen(false);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Destination could not be saved."
      );
    } finally {
      setPending(false);
    }
  }, [draft, editing, mutateDestinations]);

  const toggleDestinationStatus = useCallback(
    async (profile: DestinationProfile) => {
      setPending(true);
      try {
        await updateDestinationStatus(profile.id, !profile.isActive);
        await mutateDestinations();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Status update failed.");
      } finally {
        setPending(false);
      }
    },
    [mutateDestinations]
  );

  return {
    items,
    isLoading,
    error,
    isDrawerOpen,
    editing,
    draft,
    message,
    pending,
    setDraft,
    openCreate,
    openEdit,
    closeDrawer,
    saveDestination,
    toggleDestinationStatus,
    mutateDestinations,
  };
}
