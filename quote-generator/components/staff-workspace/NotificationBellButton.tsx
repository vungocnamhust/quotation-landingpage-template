"use client";

import { Bell } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";

interface NotificationBellButtonProps {
  unreadCount: number;
  isOpen: boolean;
  onClick: () => void;
}

export function NotificationBellButton({
  unreadCount,
  isOpen,
  onClick,
}: NotificationBellButtonProps) {
  const displayCount = unreadCount > 99 ? "99+" : unreadCount;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Notifications (${unreadCount} unread)`}
      aria-expanded={isOpen}
      className={cn(
        "relative flex h-10 w-10 items-center justify-center rounded-[var(--radius-button)] border transition-all",
        isOpen
          ? "border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]"
      )}
    >
      <Bell size={18} aria-hidden="true" className={unreadCount > 0 ? "animate-pulse" : ""} />
      {unreadCount > 0 ? (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "absolute -top-1.5 -right-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-white shadow-sm ring-2 ring-[var(--color-surface)]"
          )}
        >
          {displayCount}
        </span>
      ) : null}
    </button>
  );
}
