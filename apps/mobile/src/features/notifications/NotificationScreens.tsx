import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Redirect, useRouter } from "expo-router";
import { ComponentProps } from "react";
import { Pressable, View } from "react-native";

import { Button, Card, LoadingIndicator, Screen, Text } from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getApiErrorMessage } from "@/features/auth/errors";
import { markAllNotificationsCachedRead, markNotificationCachedRead } from "@/features/messaging/realtimeCache";
import { safeNotificationHref } from "@/features/notifications/navigation";
import { CareNotification, getNotifications, markAllNotificationsRead, markNotificationRead, NotificationPage } from "@/services/api/notifications";
import { useTheme } from "@/theme/ThemeProvider";

type FeatherName = ComponentProps<typeof Feather>["name"];
function iconFor(kind: CareNotification["kind"]): FeatherName {
  if (kind === "NEW_MESSAGE") return "message-circle";
  if (kind === "CONSULTATION_SUBMITTED") return "clipboard";
  if (kind.startsWith("APPOINTMENT_")) return "calendar";
  if (kind === "COACHING_PLAN_PUBLISHED") return "book-open";
  return "trending-up";
}
function dateLabel(value: string) { return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }

export function NotificationsScreen() {
  const router = useRouter(); const theme = useTheme(); const queryClient = useQueryClient();
  const status = useAuthStore((state) => state.status);
  const userId = useAuthStore((state) => state.user?.public_id);
  const notifications = useQuery({ queryKey: ["notifications", userId], queryFn: getNotifications, enabled: status === "authenticated", refetchOnWindowFocus: false, refetchOnReconnect: false, refetchOnMount: false });
  const read = useMutation({ mutationFn: markNotificationRead, onSuccess: (item) => queryClient.setQueryData<NotificationPage>(["notifications", userId], (current) => markNotificationCachedRead(current, item)) });
  const readAll = useMutation({ mutationFn: markAllNotificationsRead, onSuccess: () => queryClient.setQueryData<NotificationPage>(["notifications", userId], markAllNotificationsCachedRead) });
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  const open = (notification: CareNotification) => { if (!notification.read_at) read.mutate(notification.public_id); router.push(safeNotificationHref(notification.route)); };
  return (
    <Screen contentStyle={{ gap: theme.spacing.lg }}>
      <View style={{ minHeight: 48, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing.md }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={() => router.canGoBack() ? router.back() : router.replace("/explore")} style={({ pressed }) => ({ width: 44, height: 44, borderRadius: theme.radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: pressed ? theme.colors.surfaceMuted : theme.colors.surface })}><Feather name="chevron-left" size={22} color={theme.colors.text} /></Pressable>
        <View style={{ flex: 1 }}><Text variant="overline" color="accent">YOUR UPDATES</Text><Text variant="title">Notifications</Text></View>
        {notifications.data?.unread_count ? <Button variant="ghost" loading={readAll.isPending} onPress={() => readAll.mutate()} style={{ alignSelf: "center" }}>Mark all read</Button> : null}
      </View>
      {notifications.isLoading ? <LoadingIndicator /> : null}
      {notifications.isError ? <Card style={{ gap: theme.spacing.sm }}><Text variant="heading">Updates could not load</Text><Text color="muted">{getApiErrorMessage(notifications.error)}</Text><Button variant="secondary" onPress={() => notifications.refetch()}>Try again</Button></Card> : null}
      {notifications.data?.results.length === 0 ? <Card style={{ alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xl }}><Feather name="bell" size={28} color={theme.colors.textMuted} /><Text variant="heading">You’re all caught up</Text><Text color="muted" style={{ textAlign: "center" }}>Appointment, message, and care updates will appear here.</Text></Card> : null}
      <View style={{ gap: theme.spacing.sm }}>
        {notifications.data?.results.map((notification) => <Pressable key={notification.public_id} accessibilityRole="button" accessibilityLabel={`${notification.title}. ${notification.body}`} onPress={() => open(notification)} style={({ pressed }) => ({ opacity: pressed ? 0.76 : 1 })}>
          <Card style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md, backgroundColor: notification.read_at ? theme.colors.surface : theme.colors.primaryMuted }}>
            <View style={{ width: 40, height: 40, borderRadius: theme.radius.md, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.surface }}><Feather name={iconFor(notification.kind)} size={19} color={theme.colors.primary} /></View>
            <View style={{ flex: 1, minWidth: 0, gap: theme.spacing.xs }}>
              <View
                style={{
                  flexDirection: "row",
                  alignItems: "flex-start",
                  gap: theme.spacing.xs,
                }}
              >
                {!notification.read_at ? (
                  <View
                    style={{
                      width: 7,
                      height: 7,
                      marginTop: 8,
                      borderRadius: 4,
                      backgroundColor: theme.colors.primary,
                    }}
                  />
                ) : null}
                <Text variant="bodyStrong" style={{ flex: 1 }}>
                  {notification.title}
                </Text>
              </View>
              <Text variant="caption" color="muted">
                {dateLabel(notification.created_at)}
              </Text>
              <Text color="muted">{notification.body}</Text>
            </View>
            <Feather
              name="chevron-right"
              size={19}
              color={theme.colors.textMuted}
              style={{ marginTop: 2 }}
            />
          </Card>
        </Pressable>)}
      </View>
    </Screen>
  );
}
