import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import { PropsWithChildren, useState } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { FloatingTabBar } from "@/components/FloatingTabBar";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { InAppNotificationBanner } from "@/features/notifications/InAppNotificationBanner";
import { PushNotificationsBootstrap } from "@/features/notifications/PushNotificationsBootstrap";
import { ThemeProvider } from "@/theme/ThemeProvider";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000,
          },
        },
      }),
  );

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <StatusBar style="dark" />
            <AuthBootstrap />
            <PushNotificationsBootstrap />
            {children}
            <FloatingTabBar />
            <InAppNotificationBanner />
          </ThemeProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
