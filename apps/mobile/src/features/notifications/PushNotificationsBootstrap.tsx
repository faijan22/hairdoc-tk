import * as Notifications from "expo-notifications";
import { useRouter } from "expo-router";
import { useEffect } from "react";
import { Platform } from "react-native";

import {
  enablePushOnThisDevice,
  pushUnavailableReason,
} from "./pushNotifications";

import { useAuthStore } from "@/features/auth/authStore";
import { safeNotificationHref } from "@/features/notifications/navigation";

export function PushNotificationsBootstrap() {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);

  useEffect(() => {
    if (status !== "authenticated" || pushUnavailableReason()) return;
    const syncGrantedDevice = () =>
      Notifications.getPermissionsAsync()
        .then((permission) => {
          if (permission.status === "granted")
            return enablePushOnThisDevice(false);
          return undefined;
        })
        .catch(() => undefined);
    void syncGrantedDevice();
    const tokenSubscription = Notifications.addPushTokenListener(() => {
      void syncGrantedDevice();
    });
    return () => tokenSubscription.remove();
  }, [status]);

  useEffect(() => {
    if (Platform.OS === "web") return;

    const open = (response: Notifications.NotificationResponse) => {
      const route = response.notification.request.content.data?.route;
      router.push(safeNotificationHref(route));
    };
    const subscription =
      Notifications.addNotificationResponseReceivedListener(open);
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) open(response);
    });
    return () => subscription.remove();
  }, [router]);

  return null;
}
