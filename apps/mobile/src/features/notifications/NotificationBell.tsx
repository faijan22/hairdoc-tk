import Feather from "@expo/vector-icons/Feather";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, View } from "react-native";

import { Text } from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getNotifications } from "@/services/api/notifications";
import { useTheme } from "@/theme/ThemeProvider";

export function NotificationBell() {
  const router = useRouter();
  const theme = useTheme();
  const authenticated = useAuthStore((state) => state.status === "authenticated");
  const userId = useAuthStore((state) => state.user?.public_id);
  const notifications = useQuery({ queryKey: ["notifications", userId], queryFn: getNotifications, enabled: authenticated, refetchOnWindowFocus: false, refetchOnReconnect: false, refetchOnMount: false });
  const unread = notifications.data?.unread_count ?? 0;
  if (!authenticated) return null;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={unread ? `Notifications, ${unread} unread` : "Notifications"} onPress={() => router.push("/notifications")} style={({ pressed }) => ({ cursor: "pointer", width: 44, height: 44, borderRadius: theme.radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: pressed ? theme.colors.surfaceMuted : theme.colors.surface })}>
      <Feather name="bell" size={20} color={theme.colors.text} />
      {unread ? <View style={{ position: "absolute", right: -2, top: -2, minWidth: 19, height: 19, paddingHorizontal: 4, borderRadius: 10, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.primary, borderWidth: 2, borderColor: theme.colors.background }}><Text variant="caption" style={{ color: theme.colors.onPrimary, fontSize: 10 }}>{unread > 99 ? "99+" : unread}</Text></View> : null}
    </Pressable>
  );
}
