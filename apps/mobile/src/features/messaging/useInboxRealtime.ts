import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { AppState, Platform } from "react-native";

import { applyNotificationReads, upsertConversation, upsertNotification } from "@/features/messaging/realtimeCache";
import {
  Conversation,
  getInboxRealtimeTicket,
  hasRealtimeTransport,
  parseRealtimeConversation,
  realtimeUrl,
} from "@/services/api/messaging";
import { NotificationPage, parseRealtimeNotification, parseRealtimeNotificationReads } from "@/services/api/notifications";

/** One authenticated user stream keeps the inbox and in-app alerts current. */
export function useInboxRealtime(userId?: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!userId) return;
    let stopped = false;
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    let failures = 0;
    let hasBeenReady = false;
    let previousAppState = AppState.currentState;

    const catchUp = () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations", userId], exact: true });
      void queryClient.invalidateQueries({ queryKey: ["notifications", userId], exact: true });
    };
    const connect = async () => {
      if (stopped || !hasRealtimeTransport()) return;
      try {
        const issued = await getInboxRealtimeTicket();
        if (stopped) return;
        const url = realtimeUrl(issued.websocket_path, issued.ticket);
        if (!url) return;
        socket = new WebSocket(url);
        socket.onopen = () => {
          heartbeat = setInterval(() => {
            if (socket?.readyState === WebSocket.OPEN)
              socket.send(JSON.stringify({ type: "ping" }));
          }, 20_000);
        };
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(String(event.data));
            if (payload.type === "realtime.ready") {
              failures = 0;
              if (hasBeenReady) catchUp();
              hasBeenReady = true;
            }
            if (payload.type === "inbox.changed") {
              const next = parseRealtimeConversation(payload.conversation);
              if (queryClient.getQueryData<Conversation[]>(["conversations", userId])) {
                queryClient.setQueryData<Conversation[]>(["conversations", userId], (current) => upsertConversation(current, next));
                queryClient.setQueryData(["conversations", userId, next.public_id], next);
              } else void queryClient.invalidateQueries({ queryKey: ["conversations", userId], exact: true });
            }
            if (payload.type === "notification.created") {
              const next = parseRealtimeNotification(payload.notification);
              const key = ["notifications", userId];
              if (queryClient.getQueryData<NotificationPage>(key))
                queryClient.setQueryData<NotificationPage>(key, (current) => upsertNotification(current, next));
              else void queryClient.invalidateQueries({ queryKey: key, exact: true });
            }
            if (payload.type === "notifications.read") {
              const event = parseRealtimeNotificationReads(payload);
              queryClient.setQueryData<NotificationPage>(
                ["notifications", userId],
                (current) => applyNotificationReads(current, event.notification_ids, event.read_at, event.unread_count),
              );
            }
          } catch { /* Ignore malformed ephemeral events. */ }
        };
        socket.onerror = () => socket?.close();
        socket.onclose = () => {
          if (heartbeat) clearInterval(heartbeat);
          if (!stopped)
            retry = setTimeout(() => void connect(), Math.min(30_000, 2000 * 2 ** Math.min(failures++, 4)));
        };
      } catch {
        if (!stopped)
          retry = setTimeout(() => void connect(), Math.min(30_000, 2000 * 2 ** Math.min(failures++, 4)));
      }
    };
    void connect();
    const appState = AppState.addEventListener("change", (state) => {
      if (state === "active" && previousAppState !== "active") catchUp();
      previousAppState = state;
    });
    const webVisible = () => {
      if (document.visibilityState === "visible") catchUp();
    };
    if (Platform.OS === "web") document.addEventListener("visibilitychange", webVisible);
    return () => {
      stopped = true;
      if (retry) clearTimeout(retry);
      if (heartbeat) clearInterval(heartbeat);
      appState.remove();
      if (Platform.OS === "web") document.removeEventListener("visibilitychange", webVisible);
      socket?.close();
    };
  }, [queryClient, userId]);
}
