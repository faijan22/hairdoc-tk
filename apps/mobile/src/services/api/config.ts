import Constants from "expo-constants";
import { Platform } from "react-native";

import { resolveApiBaseUrl } from "./runtime";

const browserHostname =
  Platform.OS === "web"
    ? (globalThis as typeof globalThis & { location?: { hostname?: string } })
        .location?.hostname
    : undefined;

const configuredApiUrl = Constants.expoConfig?.extra?.developmentApiUrl;
const expoGoHost = (Constants.expoGoConfig as { debuggerHost?: string } | null)
  ?.debuggerHost;

export const API_BASE_URL = resolveApiBaseUrl({
  explicitUrl: process.env.EXPO_PUBLIC_API_URL,
  configuredUrl:
    typeof configuredApiUrl === "string" ? configuredApiUrl : undefined,
  hostUri: Constants.expoConfig?.hostUri || expoGoHost,
  browserHostname,
  isWeb: Platform.OS === "web",
});

// REST can use Metro's Expo tunnel bridge while realtime connects to the same
// development API address that is already reachable from the physical device.
export const REALTIME_API_BASE_URL =
  process.env.EXPO_PUBLIC_REALTIME_API_URL?.trim()
    ? process.env.EXPO_PUBLIC_REALTIME_API_URL.trim().replace(/\/+$/, "")
    : Platform.OS === "web"
    ? API_BASE_URL
    : typeof configuredApiUrl === "string" && configuredApiUrl.trim()
      ? configuredApiUrl.trim().replace(/\/+$/, "")
      : API_BASE_URL;
