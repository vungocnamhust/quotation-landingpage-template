'use client';

import React, { useState } from 'react';
import type { CostingSheetProfile, CostingSummary } from './types.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import { formatMinorAmount } from '../../lib/moneyFormat.ts';

export type ExistingPricingOption = {
  id: string;
  label?: string;
  currency?: string;
  group_total_amount_minor?: number;
  per_adult_amount_minor?: number;
  per_traveler_amount_minor?: number;
};

type ApplyPricingDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (targetOptionId: string | null, optionLabel: string) => Promise<void>;
  sheet: CostingSheetProfile;
  summary: CostingSummary;
  existingOptions?: ExistingPricingOption[];
  adultsCount?: number;
  isApplying?: boolean;
};

function formatCurrency(minor: number, currency: string): string {
  return formatMinorAmount(minor, currency || 'USD');
}

export const ApplyPricingDialog: React.FC<ApplyPricingDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  sheet,
  summary,
  existingOptions = [],
  adultsCount = 2,
  isApplying = false,
}) => {
  const [selectedOptionId, setSelectedOptionId] = useState<string>(() => {
    return existingOptions.length > 0 ? existingOptions[0].id : '__NEW__';
  });

  const selectedOption = existingOptions.find((opt) => opt.id === selectedOptionId);

  const [customLabel, setCustomLabel] = useState<string>(() => {
    return selectedOption?.label || `Gói tùy chọn ${existingOptions.length + 1}`;
  });

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) {
    return null;
  }

  const handleOptionChange = (optId: string) => {
    setSelectedOptionId(optId);
    if (optId === '__NEW__') {
      setCustomLabel(`Gói tùy chọn ${existingOptions.length + 1}`);
    } else {
      const match = existingOptions.find((opt) => opt.id === optId);
      setCustomLabel(match?.label || `Gói tùy chọn`);
    }
  };

  const handleApply = async () => {
    setErrorMsg(null);
    try {
      const targetId = selectedOptionId === '__NEW__' ? null : selectedOptionId;
      await onConfirm(targetId, customLabel);
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg('Không thể áp dụng giá dự toán. Vui lòng thử lại.');
      }
    }
  };

  const currentSellMinor = selectedOption?.group_total_amount_minor ?? 0;
  const newSellMinor = summary.sell_total_minor;
  const deltaMinor = newSellMinor - currentSellMinor;
  const deltaPercent = currentSellMinor > 0 ? ((deltaMinor / currentSellMinor) * 100).toFixed(1) : null;
  const perAdultMinor = Math.max(1, Math.floor(newSellMinor / Math.max(adultsCount, 1)));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isApplying) {
          onClose();
        }
      }}
    >
      <div
        className="relative w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className={cn(getTypographyClassName('cardTitle'), "text-slate-900 dark:text-slate-100")}>
                Áp dụng giá vào Báo giá
              </h3>
              <p className={cn(getTypographyClassName('caption'), "text-slate-500 dark:text-slate-400")}>
                Đồng bộ tổng giá bán từ bảng dự toán sang gói thương mại
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isApplying}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {errorMsg && (
            <div className={cn(getTypographyClassName('bodySm'), "p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400")}>
              {errorMsg}
            </div>
          )}

          {/* Option Selector */}
          <div>
            <label className={cn(getTypographyClassName('label'), "block text-slate-700 dark:text-slate-300 mb-1.5")}>
              Gói giá thương mại đích
            </label>
            <div className="grid grid-cols-1 gap-2">
              {existingOptions.map((opt, idx) => (
                <label
                  key={opt.id}
                  className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedOptionId === opt.id
                      ? 'border-amber-500 bg-amber-500/5 ring-2 ring-amber-500/20'
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="pricing_option"
                      value={opt.id}
                      checked={selectedOptionId === opt.id}
                      onChange={() => handleOptionChange(opt.id)}
                      className="text-amber-600 focus:ring-amber-500"
                    />
                    <div>
                      <span className={cn(getTypographyClassName('bodyMd'), "text-slate-900 dark:text-slate-100")}>
                        {opt.label || `Tùy chọn ${idx + 1}`}
                      </span>
                      <span className={cn(getTypographyClassName('caption'), "ml-2 text-slate-400")}>({opt.id})</span>
                    </div>
                  </div>
                  <span className={cn(getTypographyClassName('bodyMd'), "text-[var(--color-accent)]")}>
                    {formatCurrency(opt.group_total_amount_minor || 0, opt.currency || sheet.currency)}
                  </span>
                </label>
              ))}

              {existingOptions.length < 3 && (
                <label
                  className={`flex items-center justify-between p-3 rounded-xl border border-dashed cursor-pointer transition-all ${
                    selectedOptionId === '__NEW__'
                      ? 'border-amber-500 bg-amber-500/5 ring-2 ring-amber-500/20'
                      : 'border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="pricing_option"
                      value="__NEW__"
                      checked={selectedOptionId === '__NEW__'}
                      onChange={() => handleOptionChange('__NEW__')}
                      className="text-amber-600 focus:ring-amber-500"
                    />
                    <span className={cn(getTypographyClassName('bodyMd'), "text-slate-700 dark:text-slate-300")}>
                      + Tạo gói tùy chọn mới ({existingOptions.length + 1}/3)
                    </span>
                  </div>
                  <span className={cn(getTypographyClassName('caption'), "text-slate-400")}>Tối đa 3 gói</span>
                </label>
              )}
            </div>
          </div>

          {/* Option Label Field */}
          <div>
            <label className={cn(getTypographyClassName('label'), "block text-slate-700 dark:text-slate-300 mb-1.5")}>
              Tên hiển thị của gói giá
            </label>
            <input
              type="text"
              value={customLabel}
              onChange={(e) => setCustomLabel(e.target.value)}
              placeholder="VD: Gói tiêu chuẩn, Gói cao cấp..."
              className={cn(
                getTypographyClassName('bodySm'),
                "w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-amber-500",
              )}
            />
          </div>

          {/* Side-by-side Diff Preview */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 space-y-3">
            <div className={cn(getTypographyClassName('overline'), "text-slate-500 dark:text-slate-400")}>
              So sánh thay đổi
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className={cn(getTypographyClassName('caption'), "text-slate-500 dark:text-slate-400")}>
                  {selectedOption ? 'Giá thương mại hiện tại' : 'Giá hiện tại'}
                </div>
                <div className={cn(getTypographyClassName('cardTitle'), "text-slate-700 dark:text-slate-300")}>
                  {selectedOption ? formatCurrency(currentSellMinor, selectedOption.currency || sheet.currency) : '—'}
                </div>
              </div>

              <div>
                <div className={cn(getTypographyClassName('caption'), "text-amber-600 dark:text-amber-400")}>
                  Tổng giá bán mới từ Dự toán
                </div>
                <div className={cn(getTypographyClassName('cardTitle'), "text-[var(--color-accent)]")}>
                  {formatCurrency(newSellMinor, sheet.currency)}
                </div>
              </div>
            </div>

            {selectedOption && (
              <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <span className={cn(getTypographyClassName('caption'), "text-slate-500")}>Chênh lệch (Delta):</span>
                <span
                  className={cn(
                    getTypographyClassName('bodySm'),
                    deltaMinor > 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : deltaMinor < 0
                      ? 'text-rose-600 dark:text-rose-400'
                      : 'text-slate-500',
                  )}
                >
                  {deltaMinor > 0 ? '+' : ''}
                  {formatCurrency(deltaMinor, sheet.currency)} {deltaPercent ? `(${deltaMinor > 0 ? '+' : ''}${deltaPercent}%)` : ''}
                </span>
              </div>
            )}

            <div className="pt-2 border-t border-slate-200 dark:border-slate-700 grid grid-cols-2 gap-2">
              <div className={cn(getTypographyClassName('caption'), "text-slate-500 dark:text-slate-400")}>
                Tổng chi phí (Cost): <span className="text-slate-700 dark:text-slate-300">{formatCurrency(summary.cost_total_minor, sheet.currency)}</span>
              </div>
              <div className={cn(getTypographyClassName('caption'), "text-slate-500 dark:text-slate-400")}>
                Biên lợi nhuận: <span className="text-slate-700 dark:text-slate-300">{(summary.margin_bps / 100).toFixed(1)}%</span>
              </div>
              <div className={cn(getTypographyClassName('caption'), "col-span-2 text-slate-500 dark:text-slate-400")}>
                Ước tính mỗi khách ({adultsCount} người):{' '}
                <span className="text-slate-900 dark:text-slate-100">
                  {formatCurrency(perAdultMinor, sheet.currency)} / khách
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <button
            type="button"
            onClick={onClose}
            disabled={isApplying}
            className={cn(
              getTypographyClassName('buttonSecondary'),
              "px-4 py-2 rounded-xl text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors",
            )}
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleApply}
            disabled={isApplying || !customLabel.trim()}
            className={cn(
              getTypographyClassName('buttonPrimary'),
              "inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          >
            {isApplying ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Đang áp dụng...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Áp dụng vào báo giá</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
