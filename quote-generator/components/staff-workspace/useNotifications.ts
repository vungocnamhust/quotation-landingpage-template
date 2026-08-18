"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { quotationFetch } from "../../lib/apiError";
import { useToast } from "./ToastProvider";

const API_BASE =
  process.env.NEXT_PUBLIC_NOTIFICATION_API_URL ||
  process.env.NEXT_PUBLIC_QUOTATION_API_URL ||
  (typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8111"
    : "");

export type NotificationItem = {
  id: string;
  source_service: string;
  source_event_id: string;
  notification_type: string;
  recipient_email: string;
  recipient_profile_id?: string | null;
  brand_id?: string | null;
  title: string;
  body: string;
  severity: "info" | "success" | "warning" | "error";
  action_url?: string | null;
  aggregate_type?: string | null;
  aggregate_id?: string | null;
  metadata_json?: Record<string, unknown>;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
};

type NotificationListResponse = {
  items: NotificationItem[];
  total: number;
  unread_count: number;
  limit: number;
  offset: number;
};

type UnreadCountResponse = {
  unread_count: number;
};

const fetcher = <T,>(url: string) =>
  quotationFetch<T>(url, undefined, "Could not load notifications.");

export function useNotifications(options?: {
  isRead?: boolean;
  limit?: number;
  severity?: string;
}) {
  const router = useRouter();
  const { toast, notify } = useToast();

  const queryParams = new URLSearchParams();
  if (options?.isRead !== undefined) queryParams.set("is_read", String(options.isRead));
  if (options?.severity) queryParams.set("severity", options.severity);
  if (options?.limit) queryParams.set("limit", String(options.limit));

  const listUrl = `${API_BASE}/api/v2/notifications?${queryParams.toString()}`;
  const unreadCountUrl = `${API_BASE}/api/v2/notifications/unread-count`;

  const {
    data: listData,
    error: listError,
    mutate: mutateList,
    isLoading: isListLoading,
  } = useSWR<NotificationListResponse>(listUrl, fetcher, {
    revalidateOnFocus: true,
    refreshInterval: 60000,
  });

  const {
    data: countData,
    mutate: mutateCount,
  } = useSWR<UnreadCountResponse>(unreadCountUrl, fetcher, {
    revalidateOnFocus: true,
    refreshInterval: 30000,
  });

  // Listen to real-time Server-Sent Events (SSE)
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    function connectSSE() {
      const streamUrl = `${API_BASE}/api/v2/notifications/stream`;
      eventSource = new EventSource(streamUrl, { withCredentials: true });

      eventSource.addEventListener("notification", (event) => {
        try {
          const rawItem = JSON.parse(event.data);
          const newItem: NotificationItem = {
            id: rawItem.id,
            source_service: rawItem.source_service || "quotation-app",
            source_event_id: rawItem.source_event_id || "",
            notification_type: rawItem.notification_type || "system",
            recipient_email: rawItem.recipient_email || "",
            title: rawItem.title || "Notification",
            body: rawItem.body || "",
            severity: rawItem.severity || "info",
            action_url: rawItem.action_url,
            is_read: false,
            created_at: rawItem.created_at || new Date().toISOString(),
          };

          // Optimistically update list and unread count
          mutateList((current) => {
            if (!current) return current;
            const exists = current.items.some((i) => i.id === newItem.id);
            if (exists) return current;
            return {
              ...current,
              items: [newItem, ...current.items],
              total: current.total + 1,
              unread_count: current.unread_count + 1,
            };
          }, false);

          mutateCount((c) => ({
            unread_count: (c?.unread_count ?? 0) + 1,
          }), false);

          // Pop up interactive toast for important severity levels
          const toastType = newItem.severity === "error" ? "error" : newItem.severity === "success" ? "success" : "info";
          if (newItem.action_url) {
            const targetUrl = newItem.action_url;
            notify({
              message: `${newItem.title}: ${newItem.body}`,
              type: toastType,
              action: {
                label: "View",
                onClick: () => {
                  router.push(targetUrl);
                },
              },
            });
          } else {
            toast(`${newItem.title}: ${newItem.body}`, toastType);
          }
        } catch (err) {
          console.error("Error processing SSE notification:", err);
        }
      });

      eventSource.addEventListener("unread_count_updated", (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (typeof payload.unread_count === "number") {
            mutateCount({ unread_count: payload.unread_count }, false);
          }
        } catch {
          // ignore
        }
      });

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        // Attempt reconnection after 5 seconds
        reconnectTimeout = setTimeout(connectSSE, 5000);
      };
    }

    connectSSE();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [mutateList, mutateCount, notify, toast, router]);

  const markAsRead = useCallback(
    async (notificationId: string) => {
      // Optimistic update
      mutateList((current) => {
        if (!current) return current;
        return {
          ...current,
          items: current.items.map((i) =>
            i.id === notificationId ? { ...i, is_read: true, read_at: new Date().toISOString() } : i
          ),
          unread_count: Math.max(0, current.unread_count - 1),
        };
      }, false);

      mutateCount((c) => ({
        unread_count: Math.max(0, (c?.unread_count ?? 1) - 1),
      }), false);

      try {
        await quotationFetch(
          `${API_BASE}/api/v2/notifications/${notificationId}/read`,
          { method: "PATCH" },
          "Failed to mark notification as read."
        );
      } catch (err) {
        mutateList();
        mutateCount();
        toast("Could not mark notification as read.", "error");
      }
    },
    [mutateList, mutateCount, toast]
  );

  const markAllAsRead = useCallback(async () => {
    // Optimistic update
    mutateList((current) => {
      if (!current) return current;
      return {
        ...current,
        items: current.items.map((i) => ({ ...i, is_read: true, read_at: new Date().toISOString() })),
        unread_count: 0,
      };
    }, false);

    mutateCount({ unread_count: 0 }, false);

    try {
      await quotationFetch(
        `${API_BASE}/api/v2/notifications/mark-all-read`,
        { method: "POST" },
        "Failed to mark all notifications as read."
      );
    } catch (err) {
      mutateList();
      mutateCount();
      toast("Could not mark all notifications as read.", "error");
    }
  }, [mutateList, mutateCount, toast]);

  return {
    notifications: listData?.items ?? [],
    total: listData?.total ?? 0,
    unreadCount: countData?.unread_count ?? listData?.unread_count ?? 0,
    isLoading: isListLoading,
    error: listError,
    markAsRead,
    markAllAsRead,
    refetch: mutateList,
  };
}
