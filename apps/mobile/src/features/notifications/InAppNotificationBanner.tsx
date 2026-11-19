import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Modal, Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card, Text } from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { markNotificationCachedRead } from "@/features/messaging/realtimeCache";
import { useInboxRealtime } from "@/features/messaging/useInboxRealtime";
import { safeNotificationHref } from "@/features/notifications/navigation";
import {
  getNotifications,
  markNotificationRead,
  NotificationPage,
} from "@/services/api/notifications";
import { useTheme } from "@/theme/ThemeProvider";

export function InAppNotificationBanner() {
  const status = useAuthStore((state) => state.status);
  const userId = useAuthStore((state) => state.user?.public_id);
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const latestSeen = useRef<string | null | undefined>(undefined);
  const [bannerId, setBannerId] = useState<string | null>(null);
  useInboxRealtime(status === "authenticated" ? userId : undefined);
  const notifications = useQuery({
    queryKey: ["notifications", userId],
    queryFn: getNotifications,
    enabled: status === "authenticated",
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  const newest = notifications.data?.results[0];
  useEffect(() => {
    if (status !== "authenticated") {
      latestSeen.current = undefined;
      // Authentication is an external store boundary; clear any prior-user banner.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBannerId(null);
      return;
    }
    if (!notifications.data) return;
    if (latestSeen.current === undefined) {
      latestSeen.current = newest?.public_id ?? null;
      if (newest && !newest.read_at && newest.route !== pathname) {
        setBannerId(newest.public_id);
      }
      return;
    }
    if (newest && newest.public_id !== latestSeen.current) {
      latestSeen.current = newest.public_id;
      if (!newest.read_at && newest.route === pathname) {
        setBannerId(null);
        // The chat screen's read acknowledgement marks this notification on
        // the server too; no second read request is needed here.
        queryClient.setQueryData<NotificationPage>(
          ["notifications", userId],
          (current) => markNotificationCachedRead(current, {
            ...newest, read_at: new Date().toISOString(),
          }),
        );
      } else if (!newest.read_at) setBannerId(newest.public_id);
    }
  }, [newest, notifications.data, pathname, queryClient, status, userId]);
  const latest = notifications.data?.results.find(
    (item) => item.public_id === bannerId,
  );
  const read = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: (read) => queryClient.setQueryData<NotificationPage>(
      ["notifications", userId], (current) => markNotificationCachedRead(current, read),
    ),
  });
  if (status !== "authenticated" || !latest) return null;
  const dismiss = () => {
    setBannerId(null);
    read.mutate(latest.public_id);
  };
  const open = () => {
    dismiss();
    router.push(safeNotificationHref(latest.route));
  };
  return (
    <Modal visible transparent animationType="fade" onRequestClose={dismiss}>
      <View
        pointerEvents="box-none"
        style={{
          flex: 1,
          paddingTop: Math.max(insets.top, theme.spacing.md),
          paddingHorizontal: theme.spacing.md,
        }}
      >
        <Card
          style={{
            flexDirection: "row",
            alignItems: "center",
            gap: theme.spacing.sm,
            borderColor: theme.colors.primary,
          }}
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`${latest.title}. ${latest.body}`}
            onPress={open}
            style={({ pressed }) => ({
              cursor: "pointer",
              flex: 1,
              minWidth: 0,
              flexDirection: "row",
              alignItems: "center",
              gap: theme.spacing.md,
              opacity: pressed ? 0.72 : 1,
            })}
          >
            <View
              style={{
                width: 38,
                height: 38,
                borderRadius: 19,
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: theme.colors.primaryMuted,
              }}
            >
              <Feather
                name="bell"
                size={theme.iconSize.md}
                color={theme.colors.primary}
              />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text variant="bodyStrong">{latest.title}</Text>
              <Text variant="caption" color="muted">
                {latest.body}
              </Text>
            </View>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Dismiss notification"
            hitSlop={12}
            onPress={dismiss}
            style={({ pressed }) => ({
              cursor: "pointer",
              width: 40,
              height: 40,
              borderRadius: 20,
              alignItems: "center",
              justifyContent: "center",
              opacity: pressed ? 0.55 : 1,
            })}
          >
            <Feather
              name="x"
              size={theme.iconSize.md}
              color={theme.colors.textMuted}
            />
          </Pressable>
        </Card>
      </View>
    </Modal>
  );
}
