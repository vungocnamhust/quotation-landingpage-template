"use client";

import { BookingTermsEditor } from "./BookingTermsEditor";
import type { BookingFact, QuotationFacts } from "../factsTypes";

type Props = {
  booking: BookingFact;
  readOnly?: boolean;
  onUpdate: <K extends keyof QuotationFacts>(key: K, value: QuotationFacts[K]) => void;
};

export function FactSellerSection({
  booking,
  readOnly = false,
  onUpdate,
}: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <BookingTermsEditor
          booking={booking}
          readOnly={readOnly}
          onChange={(next) => onUpdate("booking_facts", next)}
        />
      </div>
    </div>
  );
}
