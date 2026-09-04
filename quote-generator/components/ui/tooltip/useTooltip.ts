"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type FocusEvent,
  type KeyboardEvent,
  type MouseEvent,
} from "react";

export type TooltipPlacement = "top" | "bottom" | "left" | "right";

export interface RectLike {
  top: number;
  bottom: number;
  left: number;
  right: number;
  width: number;
  height: number;
}

export interface ComputePositionOptions {
  triggerRect: RectLike;
  tooltipRect: { width: number; height: number };
  placement?: TooltipPlacement;
  offset?: number;
  viewportWidth?: number;
  viewportHeight?: number;
  padding?: number;
}

/**
 * Pure coordinate and collision detection calculation for tooltips.
 * Computes viewport fixed coordinates and handles boundary flipping/clamping.
 */
export function computeTooltipPosition({
  triggerRect,
  tooltipRect,
  placement = "top",
  offset = 8,
  viewportWidth = 1024,
  viewportHeight = 768,
  padding = 8,
}: ComputePositionOptions): { top: number; left: number; actualPlacement: TooltipPlacement } {
  let actualPlacement = placement;
  let top = 0;
  let left = 0;

  const width = Math.max(tooltipRect.width, 160);
  const height = Math.max(tooltipRect.height, 40);

  if (placement === "top") {
    top = triggerRect.top - height - offset;
    left = triggerRect.left + (triggerRect.width - width) / 2;

    if (top < padding && triggerRect.bottom + height + offset <= viewportHeight - padding) {
      top = triggerRect.bottom + offset;
      actualPlacement = "bottom";
    }
  } else if (placement === "bottom") {
    top = triggerRect.bottom + offset;
    left = triggerRect.left + (triggerRect.width - width) / 2;

    if (top + height > viewportHeight - padding && triggerRect.top - height - offset >= padding) {
      top = triggerRect.top - height - offset;
      actualPlacement = "top";
    }
  } else if (placement === "left") {
    top = triggerRect.top + (triggerRect.height - height) / 2;
    left = triggerRect.left - width - offset;

    if (left < padding && triggerRect.right + width + offset <= viewportWidth - padding) {
      left = triggerRect.right + offset;
      actualPlacement = "right";
    }
  } else if (placement === "right") {
    top = triggerRect.top + (triggerRect.height - height) / 2;
    left = triggerRect.right + offset;

    if (left + width > viewportWidth - padding && triggerRect.left - width - offset >= padding) {
      left = triggerRect.left - width - offset;
      actualPlacement = "left";
    }
  }

  left = Math.max(padding, Math.min(left, viewportWidth - width - padding));
  top = Math.max(padding, Math.min(top, viewportHeight - height - padding));

  return { top, left, actualPlacement };
}

export interface UseTooltipOptions {
  delay?: number;
  placement?: TooltipPlacement;
  offset?: number;
  disabled?: boolean;
  closeOnEscape?: boolean;
  closeOnOutsideClick?: boolean;
}

export interface UseTooltipReturn {
  isOpen: boolean;
  open: (immediate?: boolean) => void;
  close: (immediate?: boolean) => void;
  toggle: () => void;
  coords: { top: number; left: number };
  actualPlacement: TooltipPlacement;
  triggerRef: React.RefObject<HTMLButtonElement | null>;
  tooltipRef: React.RefObject<HTMLDivElement | null>;
  tooltipId: string;
  triggerProps: {
    ref: React.RefObject<HTMLButtonElement | null>;
    "aria-describedby": string | undefined;
    onMouseEnter: (e: MouseEvent) => void;
    onMouseLeave: (e: MouseEvent) => void;
    onFocus: (e: FocusEvent) => void;
    onBlur: (e: FocusEvent) => void;
    onClick: (e: MouseEvent) => void;
    onKeyDown: (e: KeyboardEvent) => void;
    tabIndex: number;
  };
  tooltipProps: {
    ref: React.RefObject<HTMLDivElement | null>;
    id: string;
    role: "tooltip";
    style: CSSProperties;
    onMouseEnter: () => void;
    onMouseLeave: () => void;
  };
}

export function useTooltip({
  delay = 150,
  placement = "top",
  offset = 8,
  disabled = false,
  closeOnEscape = true,
  closeOnOutsideClick = true,
}: UseTooltipOptions = {}): UseTooltipReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [actualPlacement, setActualPlacement] = useState<TooltipPlacement>(placement);

  const rawId = useId();
  const tooltipId = `tooltip-${rawId.replace(/[:]/g, "_")}`;

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const openTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (openTimerRef.current) {
      clearTimeout(openTimerRef.current);
      openTimerRef.current = null;
    }
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const updatePosition = useCallback(() => {
    if (typeof window === "undefined" || !triggerRef.current) return;
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current
      ? tooltipRef.current.getBoundingClientRect()
      : { width: 280, height: 90 };

    const pos = computeTooltipPosition({
      triggerRect,
      tooltipRect,
      placement,
      offset,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    });

    setCoords({ top: pos.top, left: pos.left });
    setActualPlacement(pos.actualPlacement);
  }, [placement, offset]);

  const open = useCallback(
    (immediate = false) => {
      if (disabled) return;
      clearTimers();
      if (immediate || delay === 0) {
        setIsOpen(true);
      } else {
        openTimerRef.current = setTimeout(() => {
          setIsOpen(true);
        }, delay);
      }
    },
    [disabled, clearTimers, delay],
  );

  const close = useCallback(
    (immediate = false) => {
      clearTimers();
      if (immediate) {
        setIsOpen(false);
      } else {
        closeTimerRef.current = setTimeout(() => {
          setIsOpen(false);
        }, 100);
      }
    },
    [clearTimers],
  );

  const toggle = useCallback(() => {
    if (disabled) return;
    clearTimers();
    setIsOpen((prev) => !prev);
  }, [disabled, clearTimers]);

  // Update position whenever open state changes or on window events
  useEffect(() => {
    if (!isOpen) return;

    updatePosition();

    function handleScrollOrResize() {
      updatePosition();
    }

    window.addEventListener("scroll", handleScrollOrResize, { capture: true, passive: true });
    window.addEventListener("resize", handleScrollOrResize, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScrollOrResize, { capture: true });
      window.removeEventListener("resize", handleScrollOrResize);
    };
  }, [isOpen, updatePosition]);

  // Outside click and Escape key dismissal
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: globalThis.KeyboardEvent) {
      if (closeOnEscape && e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close(true);
        triggerRef.current?.focus();
      }
    }

    function handleClickOutside(e: globalThis.MouseEvent | globalThis.TouchEvent) {
      if (!closeOnOutsideClick) return;
      const target = e.target as Node | null;
      if (!target) return;
      if (
        triggerRef.current &&
        !triggerRef.current.contains(target) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(target)
      ) {
        close(true);
      }
    }

    document.addEventListener("keydown", handleKeyDown, true);
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [isOpen, closeOnEscape, closeOnOutsideClick, close]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  const handleTriggerMouseEnter = useCallback(() => {
    open(false);
  }, [open]);

  const handleTriggerMouseLeave = useCallback(() => {
    close(false);
  }, [close]);

  const handleTriggerFocus = useCallback(() => {
    open(true);
  }, [open]);

  const handleTriggerBlur = useCallback(() => {
    close(true);
  }, [close]);

  const handleTriggerClick = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation();
      toggle();
    },
    [toggle],
  );

  const handleTriggerKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    },
    [toggle],
  );

  const handleTooltipMouseEnter = useCallback(() => {
    clearTimers();
  }, [clearTimers]);

  const handleTooltipMouseLeave = useCallback(() => {
    close(false);
  }, [close]);

  return {
    isOpen,
    open,
    close,
    toggle,
    coords,
    actualPlacement,
    triggerRef,
    tooltipRef,
    tooltipId,
    triggerProps: {
      ref: triggerRef,
      "aria-describedby": isOpen ? tooltipId : undefined,
      onMouseEnter: handleTriggerMouseEnter,
      onMouseLeave: handleTriggerMouseLeave,
      onFocus: handleTriggerFocus,
      onBlur: handleTriggerBlur,
      onClick: handleTriggerClick,
      onKeyDown: handleTriggerKeyDown,
      tabIndex: disabled ? -1 : 0,
    },
    tooltipProps: {
      ref: tooltipRef,
      id: tooltipId,
      role: "tooltip",
      style: {
        position: "fixed",
        top: `${coords.top}px`,
        left: `${coords.left}px`,
        zIndex: 9999,
      },
      onMouseEnter: handleTooltipMouseEnter,
      onMouseLeave: handleTooltipMouseLeave,
    },
  };
}
