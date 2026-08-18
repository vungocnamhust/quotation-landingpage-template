"use client";

import { use } from "react";
import DetailRequestView from "../../../../components/staff-workspace/DetailRequestView";
import { useRequestDetail } from "../../../../components/staff-workspace/useRequestDetail";
import { getTypographyClassName } from "../../../../config/typography";
import { cn } from "../../../../utils/cn";

type Props = {
  params: Promise<{ id: string }>;
};

export default function DetailRequestPage({ params }: Props) {
  const { id } = use(params);
  const { request, error, isLoading } = useRequestDetail(id);

  if (isLoading) {
    return (
      <div className="h-64 animate-pulse rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6" />
    );
  }

  if (error || !request) {
    return (
      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-[var(--color-on-surface)] shadow-[var(--elevation-card)]">
        <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>
          {error || `Request ${id} could not be found.`}
        </p>
      </div>
    );
  }

  return <DetailRequestView request={request} />;
}
