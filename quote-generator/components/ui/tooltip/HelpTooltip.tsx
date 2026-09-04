"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { HelpCircle, Info } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import {
  resolveTooltipContent,
  type CostingConceptKey,
} from "../../../lib/glossary/costingGlossary.ts";
import { useTooltip, type TooltipPlacement } from "./useTooltip.ts";

export type HelpTooltipSize = "sm" | "md";
export type HelpTooltipVariant = "default" | "subtle" | "rich";

const emptySubscribe = () => () => {};

function useIsMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}

export interface HelpTooltipProps {
  /** Strongly typed concept key resolving title, description, and example from the central glossary. */
  conceptKey?: CostingConceptKey;
  /** Explicit title override or custom title. */
  title?: ReactNode;
  /** Explicit content/explanation override. */
  content?: ReactNode;
  /** Alias for content to maximize prop flexibility. */
  text?: ReactNode;
  /** Explicit example override or addition. */
  example?: ReactNode;
  /** Size token: sm (13px trigger icon) or md (15px trigger icon). Default: sm */
  size?: HelpTooltipSize;
  /** Presentation variant: default, subtle, or rich. Default: default */
  variant?: HelpTooltipVariant;
  /** Placement direction: top, bottom, left, or right. Default: top */
  placement?: TooltipPlacement;
  /** Hover delay in milliseconds. Default: 150 */
  delay?: number;
  /** Custom trigger container class name. */
  triggerClassName?: string;
  /** Custom tooltip card class name. */
  tooltipClassName?: string;
  /** Accessible trigger label. Defaults to concept title or "Xem giải thích". */
  "aria-label"?: string;
  /** Icon flavor: help (HelpCircle) or info (Info). Default: help */
  icon?: "help" | "info";
  /** Optional custom trigger content replacing the default icon. */
  children?: ReactNode;
  /** Whether the tooltip is disabled. */
  disabled?: boolean;
}

export function HelpTooltip({
  conceptKey,
  title: customTitle,
  content: customContent,
  text: customText,
  example: customExample,
  size = "sm",
  variant = "default",
  placement = "top",
  delay = 150,
  triggerClassName,
  tooltipClassName,
  "aria-label": ariaLabel,
  icon = "help",
  children,
  disabled = false,
}: HelpTooltipProps) {
  const mounted = useIsMounted();

  const resolved = resolveTooltipContent({
    conceptKey,
    title: typeof customTitle === "string" ? customTitle : undefined,
    content: typeof customContent === "string" ? customContent : undefined,
    text: typeof customText === "string" ? customText : undefined,
    example: typeof customExample === "string" ? customExample : undefined,
  });

  const finalTitle = customTitle ?? resolved.title;
  const finalContent = customContent ?? customText ?? resolved.content;
  const finalExample = customExample ?? resolved.example;

  const { isOpen, triggerProps, tooltipProps } = useTooltip({
    placement,
    delay,
    disabled,
  });

  const iconSize = size === "md" ? 15 : 13;
  const IconComponent = icon === "info" ? Info : HelpCircle;

  const accessibleLabel =
    ariaLabel || (typeof finalTitle === "string" && finalTitle ? `Giải thích: ${finalTitle}` : "Xem giải thích khái niệm");

  const triggerElement = children ? (
    <button
      type="button"
      {...triggerProps}
      aria-label={accessibleLabel}
      disabled={disabled}
      className={cn("inline-flex items-center justify-center cursor-pointer", triggerClassName)}
    >
      {children}
    </button>
  ) : (
    <button
      type="button"
      {...triggerProps}
      aria-label={accessibleLabel}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center rounded-full text-[var(--color-muted)] transition-colors hover:text-[var(--color-on-surface)] focus-visible:outline-hidden focus-visible:ring-1.5 focus-visible:ring-[var(--color-accent)] cursor-pointer disabled:cursor-not-allowed disabled:opacity-40",
        size === "md" ? "p-1" : "p-0.5",
        triggerClassName,
      )}
    >
      <IconComponent size={iconSize} aria-hidden="true" />
    </button>
  );

  const tooltipElement =
    isOpen && mounted && typeof document !== "undefined" ? (
      createPortal(
        <div
          {...tooltipProps}
          className={cn(
            "pointer-events-auto rounded-[var(--radius-card)] bg-[var(--color-surface)] text-[var(--color-on-surface)] transition-opacity duration-150 ease-out",
            variant === "subtle" && "max-w-xs border border-[var(--color-border)] p-2.5 shadow-md",
            variant === "default" && "max-w-xs md:max-w-sm border border-[var(--color-border-strong)] p-3 shadow-lg",
            variant === "rich" && "max-w-sm md:max-w-md border border-[var(--color-border-strong)] p-3.5 shadow-xl",
            tooltipClassName,
          )}
        >
          {finalTitle ? (
            <div className="mb-1 flex items-center gap-1.5">
              {variant === "rich" ? (
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" aria-hidden="true" />
              ) : null}
              <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
                {finalTitle}
              </span>
            </div>
          ) : null}

          {finalContent ? (
            <div
              className={cn(
                variant === "subtle" ? getTypographyClassName("caption") : getTypographyClassName("bodySm"),
                "text-[var(--color-muted)]",
              )}
            >
              {finalContent}
            </div>
          ) : null}

          {finalExample ? (
            <div
              className={cn(
                getTypographyClassName("caption"),
                "mt-2 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-1 text-[var(--color-muted)]",
              )}
            >
              <span className="text-[var(--color-accent)]">Ví dụ: </span>
              {finalExample}
            </div>
          ) : null}
        </div>,
        document.body,
      )
    ) : null;

  return (
    <>
      {triggerElement}
      {tooltipElement}
    </>
  );
}

export default HelpTooltip;
