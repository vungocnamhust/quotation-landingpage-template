"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  X,
  CheckCheck,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  ExternalLink,
  Sparkles,
  FileText,
  Inbox,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { NotificationItem } from "./useNotifications.ts";
import { useToast } from "./ToastProvider.tsx";

interface NotificationCenterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: NotificationItem[];
  unreadCount: number;
  isLoading: boolean;
  onMarkAsRead: (id: string) => Promise<void>;
  onMarkAllAsRead: () => Promise<void>;
}

function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSeconds < 60) return "Just now";
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
    if (diffSeconds < 172800) return "Yesterday";
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

function getSeverityIcon(severity: string) {
  switch (severity) {
    case "success":
      return <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />;
    case "error":
      return <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />;
    case "warning":
      return <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />;
    default:
      return <Info size={16} className="text-sky-600 shrink-0 mt-0.5" />;
  }
}

function getSourceIcon(sourceService: string) {
  if (sourceService === "dmc-agentic-ai") {
    return <Sparkles size={12} className="text-purple-600" />;
  }
  return <FileText size={12} className="text-[var(--color-muted)]" />;
}

export function NotificationCenterDrawer({
  isOpen,
  onClose,
  notifications,
  unreadCount,
  isLoading,
  onMarkAsRead,
  onMarkAllAsRead,
}: NotificationCenterDrawerProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<"all" | "unread">("all");
  const [markingAll, setMarkingAll] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredItems = notifications.filter((item) => {
    if (activeTab === "unread") return !item.is_read;
    return true;
  });

  const handleMarkAll = async () => {
    try {
      setMarkingAll(true);
      await onMarkAllAsRead();
      toast("All notifications marked as read.", "info");
    } catch {
      toast("Could not mark notifications as read.", "error");
    } finally {
      setMarkingAll(false);
    }
  };

  const handleItemClick = async (item: NotificationItem) => {
    if (!item.is_read) {
      await onMarkAsRead(item.id);
    }
    if (item.action_url) {
      onClose();
      router.push(item.action_url);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="notification-center-title"
    >
      <div
        className="fixed inset-0"
        aria-hidden="true"
        onClick={onClose}
      />

      <div className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl transition-transform">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
          <div className="flex items-center gap-2">
            <h2
              id="notification-center-title"
              className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}
            >
              Notifications
            </h2>
            {unreadCount > 0 ? (
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full bg-red-100 px-2 py-0.5 text-red-700 dark:bg-red-950 dark:text-red-300"
                )}
              >
                {unreadCount} new
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            {unreadCount > 0 ? (
              <button
                type="button"
                onClick={handleMarkAll}
                disabled={markingAll}
                className={cn(
                  getTypographyClassName("caption"),
                  "flex items-center gap-1.5 rounded-[var(--radius-button)] px-2.5 py-1 text-[var(--color-muted)] transition-colors hover:text-[var(--color-on-surface)]"
                )}
                title="Mark all as read"
              >
                <CheckCheck size={14} aria-hidden="true" />
                <span>Mark all read</span>
              </button>
            ) : null}

            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-button)] text-[var(--color-muted)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-on-surface)]"
              aria-label="Close notifications"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex border-b border-[var(--color-border)] px-5 pt-2">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={cn(
              getTypographyClassName("bodySm"),
              "border-b-2 px-3 py-2 transition-colors",
              activeTab === "all"
                ? "border-[var(--color-accent)] text-[var(--color-accent)]"
                : "border-transparent text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
            )}
          >
            All ({notifications.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("unread")}
            className={cn(
              getTypographyClassName("bodySm"),
              "border-b-2 px-3 py-2 transition-colors",
              activeTab === "unread"
                ? "border-[var(--color-accent)] text-[var(--color-accent)]"
                : "border-transparent text-[var(--color-muted)] hover:text-[var(--color-on-surface)]"
            )}
          >
            Unread ({unreadCount})
          </button>
        </div>

        {/* Content List */}
        <div className="flex-1 overflow-y-auto p-4 divide-y divide-[var(--color-border)]">
          {isLoading && notifications.length === 0 ? (
            <div className="flex h-40 items-center justify-center">
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
                Loading notifications…
              </p>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex h-60 flex-col items-center justify-center text-center p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)] mb-3">
                <Inbox size={22} aria-hidden="true" />
              </div>
              <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
                {activeTab === "unread" ? "No unread notifications" : "No notifications yet"}
              </p>
              <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] mt-1")}>
                You are completely caught up with your travel quotations and requests.
              </p>
            </div>
          ) : (
            filteredItems.map((item) => (
              <div
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={cn(
                  "group flex cursor-pointer items-start gap-3 rounded-[var(--radius-card)] p-3 transition-colors",
                  item.is_read
                    ? "hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)]"
                    : "bg-[var(--color-accent-wash)]/40 hover:bg-[var(--color-accent-wash)] text-[var(--color-on-surface)]"
                )}
              >
                {getSeverityIcon(item.severity)}

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={cn(getTypographyClassName("overline"), "flex items-center gap-1 text-[var(--color-muted)]")}>
                        {getSourceIcon(item.source_service)}
                        {item.source_service === "dmc-agentic-ai" ? "Agentic AI" : "Quotation"}
                      </span>
                    </div>
                    <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] shrink-0")}>
                      {formatRelativeTime(item.created_at)}
                    </span>
                  </div>

                  <p className={cn(getTypographyClassName("bodySm"), "mt-0.5 truncate text-[var(--color-on-surface)]")}>
                    {item.title}
                  </p>

                  <p className={cn(getTypographyClassName("caption"), "mt-0.5 line-clamp-2 text-[var(--color-muted)]")}>
                    {item.body}
                  </p>

                  {item.action_url ? (
                    <div className={cn(getTypographyClassName("caption"), "mt-2 flex items-center gap-1 text-[var(--color-accent)] group-hover:underline")}>
                      <span>View details</span>
                      <ExternalLink size={12} aria-hidden="true" />
                    </div>
                  ) : null}
                </div>

                {!item.is_read ? (
                  <span
                    className="h-2 w-2 rounded-full bg-[var(--color-accent)] shrink-0 self-center"
                    aria-label="Unread"
                  />
                ) : null}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
