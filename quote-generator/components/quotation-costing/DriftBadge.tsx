'use client';

import React from 'react';
import type { CostingDriftProfile } from './types.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';

type DriftBadgeProps = {
  drift?: CostingDriftProfile | null;
  className?: string;
  onReapplyClick?: () => void;
};

export const DriftBadge: React.FC<DriftBadgeProps> = ({ drift, className = '', onReapplyClick }) => {
  if (!drift) {
    return null;
  }

  if (drift.has_drift) {
    const isCostingModified = drift.costing_modified_since_apply;
    const isCommercialModified = drift.commercial_modified_since_apply;
    
    let tooltip = 'Dữ liệu dự toán và giá thương mại đang có sự chênh lệch.';
    if (isCostingModified && isCommercialModified) {
      tooltip = 'Cả bảng dự toán và giá thương mại đều đã bị chỉnh sửa sau lần áp dụng trước.';
    } else if (isCostingModified) {
      tooltip = 'Bảng dự toán có thay đổi dòng dịch vụ sau lần áp dụng giá gần nhất.';
    } else if (isCommercialModified) {
      tooltip = 'Giá thương mại trên báo giá đã bị thay đổi thủ công.';
    }

    return (
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400",
          className,
        )}
        title={tooltip}
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
        <span className={cn(getTypographyClassName('label'))}>
          Chênh lệch dự toán
        </span>
        {onReapplyClick && (
          <button
            type="button"
            onClick={onReapplyClick}
            className={cn(getTypographyClassName('label'), 'ml-1 underline hover:text-amber-700 dark:hover:text-amber-300')}
          >
            Đồng bộ lại
          </button>
        )}
      </div>
    );
  }

  if (drift.last_applied_at) {
    return (
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
          className,
        )}
        title={`Đã áp dụng lúc ${new Date(drift.last_applied_at).toLocaleTimeString()}`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
        <span className={cn(getTypographyClassName('label'))}>
          Đã đồng bộ giá
        </span>
      </div>
    );
  }

  return null;
};

