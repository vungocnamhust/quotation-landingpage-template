/**
 * Canonical Reusable Component Example: DestinationSelect
 * 
 * Demonstrates:
 * 1. Headless Hook Extraction (useDestinationSearch)
 * 2. Flexible Value Contract (Single & Multiple mode, unified onChange)
 * 3. Size & Variant Matrix (sm, md, lg, compact, default)
 * 4. Encapsulated Semantic Tokens (CSS variables & Typography SSOT)
 * 5. Built-in Keyboard & A11y (Escape, ArrowDown/Up, Enter, ARIA listbox)
 */

import React, { useState } from "react";
import { DestinationSelect } from "@/components/destination/DestinationSelect";
import type { DestinationRef } from "@/components/destination/types";

export function DestinationSelectUsageExample() {
  // 1. Single Mode (Basic Form)
  const [selectedDestination, setSelectedDestination] = useState<string | null>("Hanoi");
  const [selectedRef, setSelectedRef] = useState<DestinationRef | null>(null);

  // 2. Multiple Mode (Trip Overview Tags)
  const [tripStops, setTripStops] = useState<DestinationRef[]>([
    { id: "dst_hanoi", name: "Hanoi", slug: "hanoi" },
    { id: "dst_danang", name: "Da Nang", slug: "da-nang" },
  ]);

  // 3. Compact Mode (Table Cell)
  const [dayDestination, setDayDestination] = useState("Ho Chi Minh City");

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* 1. Single Mode Usage */}
      <section className="flex flex-col gap-2">
        <h3 className="font-medium text-lg">1. Single Mode Form Input</h3>
        <DestinationSelect
          label="Primary Travel Destination"
          required
          value={selectedDestination}
          onChange={(name, ref) => {
            setSelectedDestination(name);
            setSelectedRef(ref ?? null);
          }}
          helperText="Select from catalog or type custom city"
        />
        <p className="text-sm text-gray-500">
          Current: {selectedDestination} (ID: {selectedRef?.id ?? "none"})
        </p>
      </section>

      {/* 2. Multiple Mode Usage */}
      <section className="flex flex-col gap-2">
        <h3 className="font-medium text-lg">2. Multi-Select Route Tag Chips</h3>
        <DestinationSelect
          mode="multiple"
          label="All Route Destinations"
          values={tripStops}
          onChange={(nextStops: DestinationRef[]) => setTripStops(nextStops)}
        />
        <p className="text-sm text-gray-500">
          Stops count: {tripStops.length}
        </p>
      </section>

      {/* 3. Compact Mode Usage (Inside Table / Dense Grid) */}
      <section className="flex flex-col gap-2">
        <h3 className="font-medium text-lg">3. Compact Table Row Cell</h3>
        <div className="w-64 border p-2 rounded">
          <DestinationSelect
            size="sm"
            variant="compact"
            placeholder="e.g. Hanoi"
            value={dayDestination}
            onChange={(name) => setDayDestination(name ?? "")}
          />
        </div>
      </section>
    </div>
  );
}
