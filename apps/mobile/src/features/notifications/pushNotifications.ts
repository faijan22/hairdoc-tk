import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import {
  getPushDevices,
  registerPushDevice,
  removePushDevice,
} from "@/services/api/notifications";

const DEVICE_ID_KEY = "hairdoc_tk_push_device_id";

function newDeviceId() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
    /[xy]/g,
    (character) => {
      const random = Math.floor(Math.random() * 16);
      return (character === "x" ? random : (random & 3) | 8).toString(16);
    },
  );
}

async function deviceId() {
  const existing = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (existing) return existing;
  const created = newDeviceId();
  await SecureStore.setItemAsync(DEVICE_ID_KEY, created);
  return created;
}

export async function unregisterPushOnThisDevice() {
  if (Platform.OS === "web") return;
  const currentId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!currentId) return;
  const devices = await getPushDevices();
  const current = devices.find((item) => item.device_id === currentId);
  if (current) await removePushDevice(current.public_id);
}

export function pushUnavailableReason(): string | null {
  if (Platform.OS === "web")
    return "Push notifications are available in the iOS and Android app.";
  if (Constants.appOwnership === "expo")
    return "Remote push needs a HairDoc TK development or store build; Expo Go cannot receive it.";
  if (
    !Constants.expoConfig?.extra?.eas?.projectId &&
    !Constants.easConfig?.projectId
  ) {
    return "The app build is not linked to its Expo project yet.";
  }
  return null;
}

export async function enablePushOnThisDevice(requestPermission = true) {
  const unavailable = pushUnavailableReason();
  if (unavailable) throw new Error(unavailable);
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("care-updates", {
      name: "Care updates",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 200],
      lockscreenVisibility: Notifications.AndroidNotificationVisibility.PRIVATE,
    });
  }
  let permission = await Notifications.getPermissionsAsync();
  if (permission.status !== "granted" && requestPermission)
    permission = await Notifications.requestPermissionsAsync();
  if (permission.status !== "granted")
    throw new Error("Notification permission was not granted.");
  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ??
    Constants.easConfig?.projectId;
  const token = await Notifications.getExpoPushTokenAsync({ projectId });
  return registerPushDevice({
    expo_token: token.data,
    platform: Platform.OS === "ios" ? "IOS" : "ANDROID",
    device_id: await deviceId(),
  });
}

if (Platform.OS !== "web") {
  Notifications.setNotificationHandler({
    // Foreground updates use the in-app banner; iOS/Android display remote
    // notifications normally while the app is backgrounded or closed.
    handleNotification: async () => ({
      shouldShowBanner: false,
      shouldShowList: false,
      shouldPlaySound: false,
      shouldSetBadge: false,
    }),
  });
}
