import { Platform } from "react-native";
import { create } from "zustand";

import {
  clearRefreshToken,
  readRefreshToken,
  writeRefreshToken,
} from "./refreshTokenStorage";
import { configureRefreshHandler, setAccessToken } from "./tokenRuntime";

import { unregisterPushOnThisDevice } from "@/features/notifications/pushNotifications";
import {
  AuthUser,
  login,
  logout,
  logoutAll,
  refreshSession,
} from "@/services/api/auth";

type AuthStatus = "bootstrapping" | "anonymous" | "authenticated";

type AuthState = {
  status: AuthStatus;
  user: AuthUser | null;
  bootstrap: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signOutEverywhere: () => Promise<void>;
  setUser: (user: AuthUser) => void;
};

async function clearLocalSession(): Promise<void> {
  setAccessToken(null);
  await clearRefreshToken();
  useAuthStore.setState({ status: "anonymous", user: null });
}

async function persistNativeRefreshToken(token?: string): Promise<void> {
  if (Platform.OS === "web") return;
  if (!token) throw new Error("The server did not issue a device session.");
  await writeRefreshToken(token);
}

async function refreshStoredSession(): Promise<string | null> {
  const storedToken = await readRefreshToken();
  if (Platform.OS !== "web" && !storedToken) {
    await clearLocalSession();
    return null;
  }
  try {
    const session = await refreshSession(storedToken);
    await persistNativeRefreshToken(session.refresh_token);
    setAccessToken(session.access_token);
    useAuthStore.setState({ status: "authenticated", user: session.user });
    return session.access_token;
  } catch (error) {
    const isNetworkFailure =
      error instanceof TypeError ||
      (error instanceof Error && error.name === "AbortError");
    if (isNetworkFailure) {
      setAccessToken(null);
      useAuthStore.setState({ status: "anonymous", user: null });
    } else {
      await clearLocalSession();
    }
    return null;
  }
}

let bootstrapInFlight: Promise<void> | null = null;

export const useAuthStore = create<AuthState>((set) => ({
  status: "bootstrapping",
  user: null,
  bootstrap: async () => {
    if (!bootstrapInFlight) {
      bootstrapInFlight = refreshStoredSession()
        .then(() => undefined)
        .finally(() => {
          bootstrapInFlight = null;
        });
    }
    await bootstrapInFlight;
  },
  signIn: async (email, password) => {
    const session = await login({
      email,
      password,
      device_name:
        Platform.OS === "web" ? "Web browser" : `${Platform.OS} device`,
    });
    await persistNativeRefreshToken(session.refresh_token);
    setAccessToken(session.access_token);
    set({ status: "authenticated", user: session.user });
  },
  signOut: async () => {
    const storedToken = await readRefreshToken();
    try {
      await unregisterPushOnThisDevice().catch(() => undefined);
      if (Platform.OS === "web" || storedToken) await logout(storedToken);
    } catch {
      // Local sign-out must still complete if the API is temporarily unreachable.
    } finally {
      await clearLocalSession();
    }
  },
  signOutEverywhere: async () => {
    try {
      await unregisterPushOnThisDevice().catch(() => undefined);
      await logoutAll();
    } catch {
      // Local sign-out must still complete if the API is temporarily unreachable.
    } finally {
      await clearLocalSession();
    }
  },
  setUser: (user) => set({ user }),
}));

configureRefreshHandler(refreshStoredSession);
