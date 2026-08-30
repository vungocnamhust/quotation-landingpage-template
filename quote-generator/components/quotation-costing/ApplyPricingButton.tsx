'use client';

import React, { useState } from 'react';
import type { CostingDriftProfile, CostingSheetProfile, CostingSummary } from './types.ts';
import { ApplyPricingDialog, type ExistingPricingOption } from './ApplyPricingDialog.tsx';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';

type ApplyPricingButtonProps = {
  sheet: CostingSheetProfile;
  summary: CostingSummary;
  existingOptions?: ExistingPricingOption[];
  adultsCount?: number;
  childrenCount?: number;
  drift?: CostingDriftProfile | null;
  onApply: (targetOptionId: string | null, optionLabel: string) => Promise<void>;
  isApplying?: boolean;
  className?: string;
};

export const ApplyPricingButton: React.FC<ApplyPricingButtonProps> = ({
  sheet,
  summary,
  existingOptions = [],
  adultsCount = 2,
  childrenCount = 0,
  drift,
  onApply,
  isApplying = false,
  className = '',
}) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const isAttached = Boolean(sheet.quotation_id);
  const hasLinesAndSell = summary.sell_total_minor > 0;
  const isEnabled = isAttached && hasLinesAndSell;

  let disabledTooltip = '';
  if (!isAttached) {
    disabledTooltip = 'Cần liên kết bảng dự toán với báo giá trước khi áp dụng giá.';
  } else if (!hasLinesAndSell) {
    disabledTooltip = 'Cần có ít nhất 1 dòng dịch vụ có tổng giá bán lớn hơn 0.';
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsDialogOpen(true)}
        disabled={!isEnabled || isApplying}
        title={disabledTooltip}
        className={cn(
          "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-xs hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed",
          getTypographyClassName("buttonPrimary"),
          className,
        )}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
        <span>
          Áp dụng giá vào báo giá
        </span>
      </button>

      {/* Mounted only while open so its useState initializers re-run per open (16.3 F-24). */}
      {isDialogOpen ? (
      <ApplyPricingDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onConfirm={onApply}
        sheet={sheet}
        summary={summary}
        existingOptions={existingOptions}
        adultsCount={adultsCount}
        childrenCount={childrenCount}
        drift={drift}
        isApplying={isApplying}
      />
      ) : null}
    </>
  );
};
