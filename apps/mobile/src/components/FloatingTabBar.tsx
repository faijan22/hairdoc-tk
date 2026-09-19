import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { Href, usePathname, useRouter } from "expo-router";
import { ComponentProps, useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { AppText as Text } from "@/components/ui/AppText";
import { useAuthStore } from "@/features/auth/authStore";
import { getConversations } from "@/services/api/messaging";
import { useTheme } from "@/theme/ThemeProvider";

type IconName = ComponentProps<typeof Feather>["name"];
type Tab = {
  label: string;
  icon: IconName;
  href: Href;
  match: string;
  activeRoutes?: string[];
};

const clientTabs: Tab[] = [
  { label: "Home", icon: "home", href: "/explore", match: "/explore" },
  { label: "Consult", icon: "search", href: "/consult", match: "/consult" },
  {
    label: "Messages",
    icon: "message-circle",
    href: "/messages",
    match: "/messages",
  },
  {
    label: "Visits",
    icon: "calendar",
    href: "/appointments",
    match: "/appointments",
  },
  { label: "Profile", icon: "user", href: "/settings", match: "/settings" },
];

const expertTabs: Tab[] = [
  { label: "Home", icon: "home", href: "/explore", match: "/explore" },
  {
    label: "Reviews",
    icon: "clipboard",
    href: "/staff/consultations",
    match: "/staff/consultations",
  },
  {
    label: "Messages",
    icon: "message-circle",
    href: "/messages",
    match: "/messages",
  },
  {
    label: "Schedule",
    icon: "calendar",
    href: "/staff/appointments",
    match: "/staff",
    activeRoutes: ["/staff/appointments", "/staff/availability"],
  },
  { label: "Profile", icon: "user", href: "/settings", match: "/settings" },
];

const visibleRoutes = new Set([
  "/explore",
  "/consult",
  "/messages",
  "/appointments",
  "/settings",
  "/staff/consultations",
  "/staff/appointments",
  "/staff/availability",
]);

export function isFloatingTabRoute(pathname: string) {
  return visibleRoutes.has(pathname);
}

function isActiveTab(tab: Tab, pathname: string) {
  return Boolean(
    tab.activeRoutes?.includes(pathname) ||
    pathname === tab.href ||
    (tab.match !== "/staff" && pathname.startsWith(`${tab.match}/`)),
  );
}

export function FloatingTabBar() {
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const pathname = usePathname();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const reduceMotion = useReducedMotion();
  const [barWidth, setBarWidth] = useState(0);
  const conversations = useQuery({
    queryKey: ["conversations", user?.public_id],
    queryFn: getConversations,
    enabled: status === "authenticated",
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  const unreadMessages =
    conversations.data?.reduce((total, item) => total + item.unread_count, 0) ||
    0;
  const tabs = user?.is_staff ? expertTabs : clientTabs;
  const activeIndex = Math.max(
    0,
    tabs.findIndex((tab) => isActiveTab(tab, pathname)),
  );
  const indicatorPosition = useSharedValue(activeIndex);
  const horizontalInset = theme.spacing.xs;
  const segmentWidth = Math.max(
    0,
    (barWidth - horizontalInset * 2) / tabs.length,
  );
  const indicatorStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: indicatorPosition.value * segmentWidth }],
  }));

  useEffect(() => {
    indicatorPosition.value = reduceMotion
      ? activeIndex
      : withTiming(activeIndex, { duration: 260 });
  }, [activeIndex, indicatorPosition, reduceMotion]);

  if (status !== "authenticated" || !isFloatingTabRoute(pathname)) return null;

  return (
    <View
      pointerEvents="box-none"
      style={{
        position: "absolute",
        left: theme.spacing.md,
        right: theme.spacing.md,
        bottom: Math.max(insets.bottom, theme.spacing.sm),
        alignItems: "center",
        zIndex: 50,
      }}
    >
      <View
        accessibilityRole="tablist"
        onLayout={(event) => setBarWidth(event.nativeEvent.layout.width)}
        style={{
          width: "100%",
          maxWidth: 680,
          minHeight: 70,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-around",
          paddingHorizontal: theme.spacing.xs,
          paddingVertical: 6,
          borderRadius: 35,
          backgroundColor: theme.colors.surface,
          shadowColor: "#0E1D14",
          shadowOpacity: 0.12,
          shadowRadius: 22,
          shadowOffset: { width: 0, height: 10 },
          elevation: 10,
        }}
      >
        {barWidth > 0 ? (
          <Animated.View
            pointerEvents="none"
            style={[
              {
                position: "absolute",
                left: horizontalInset,
                top: 6,
                bottom: 6,
                width: segmentWidth,
                borderRadius: theme.radius.lg,
                backgroundColor: theme.colors.primaryMuted,
              },
              indicatorStyle,
            ]}
          />
        ) : null}
        {tabs.map((tab) => {
          const active = isActiveTab(tab, pathname);
          return (
            <Pressable
              key={tab.label}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={tab.label}
              onPress={() => router.replace(tab.href)}
              style={({ pressed }) => ({
                cursor: "pointer",
                flex: 1,
                minWidth: 0,
                minHeight: 54,
                paddingHorizontal: theme.spacing.xs,
                borderRadius: theme.radius.lg,
                alignItems: "center",
                justifyContent: "center",
                gap: 2,
                opacity: pressed ? 0.68 : 1,
                zIndex: 1,
              })}
            >
              <View style={{ position: "relative" }}>
                <Feather
                  name={tab.icon}
                  size={20}
                  color={
                    active ? theme.colors.primary : theme.colors.textMuted
                  }
                />
                {tab.label === "Messages" && unreadMessages > 0 ? (
                  <View
                    accessibilityLabel={`${unreadMessages} unread messages`}
                    style={{
                      position: "absolute",
                      right: -4,
                      top: -3,
                      width: 9,
                      height: 9,
                      borderRadius: 5,
                      borderWidth: 2,
                      borderColor: theme.colors.surface,
                      backgroundColor: theme.colors.primary,
                    }}
                  />
                ) : null}
              </View>
              <Text
                variant="overline"
                style={{
                  fontSize: 10,
                  lineHeight: 13,
                  color: active ? theme.colors.primary : theme.colors.textMuted,
                }}
              >
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
