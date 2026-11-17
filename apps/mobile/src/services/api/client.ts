import { fetch as expoFetch } from "expo/fetch";
import { Platform } from "react-native";

import { API_BASE_URL } from "./config";

import {
  getAccessToken,
  refreshAccessToken,
} from "@/features/auth/tokenRuntime";

const DEFAULT_API_TIMEOUT_MS = API_BASE_URL.includes(".exp.direct/")
  ? 20_000
  : 10_000;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "REQUEST_ERROR",
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  authenticate?: boolean;
  retryAuth?: boolean;
  timeoutMs?: number;
};

type ErrorEnvelope = {
  error?: { code?: string; message?: string; details?: unknown };
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    authenticate = true,
    retryAuth = true,
    timeoutMs = DEFAULT_API_TIMEOUT_MS,
  } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const accessToken = authenticate ? getAccessToken() : null;
    const isForm = typeof FormData !== "undefined" && body instanceof FormData;
    const request = isForm ? expoFetch : fetch;
    const response = await request(`${API_BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(Platform.OS === "web" ? { "X-HairDoc-Client": "web" } : {}),
        ...(body === undefined || isForm
          ? {}
          : { "Content-Type": "application/json" }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body:
        body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      signal: controller.signal,
    });

    if (response.status === 401 && authenticate && retryAuth) {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken)
        return apiRequest<T>(path, { ...options, retryAuth: false });
    }

    if (response.status === 204) return undefined as T;
    const responseText = await response.text();
    let payload: (T & ErrorEnvelope) | undefined;
    try {
      payload = JSON.parse(responseText) as T & ErrorEnvelope;
    } catch {
      if (!response.ok) {
        if (__DEV__)
          console.warn(`[HairDoc API] ${method} ${path} returned ${response.status} without JSON.`);
        throw new ApiError(
          response.status >= 500
            ? "The server could not complete this request."
            : "The server returned an invalid response.",
          response.status,
          "INVALID_RESPONSE",
        );
      }
      throw new ApiError(
        "The server returned an invalid response.",
        response.status,
        "INVALID_RESPONSE",
      );
    }
    if (!response.ok) {
      if (__DEV__)
        console.warn(`[HairDoc API] ${method} ${path} returned ${response.status}.`);
      throw new ApiError(
        payload?.error?.message ||
          `Request failed with status ${response.status}.`,
        response.status,
        payload?.error?.code,
        payload?.error?.details,
      );
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(
        "The request took too long. Check the Expo tunnel and try again.",
        0,
        "REQUEST_TIMEOUT",
      );
    }
    if (__DEV__ && error instanceof Error)
      console.warn(
        `[HairDoc API] ${method} ${path} failed before receiving a response: ${error.name}: ${error.message}`,
      );
    throw new ApiError(
      "The app could not reach the backend. Check the local server and Expo tunnel.",
      0,
      "NETWORK_ERROR",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export function apiGet<T>(
  path: string,
  timeoutMs = DEFAULT_API_TIMEOUT_MS,
): Promise<T> {
  return apiRequest<T>(path, { timeoutMs });
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  authenticate = true,
): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body, authenticate });
}

export function apiPostForm<T>(path: string, body: FormData): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body, timeoutMs: 45_000 });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, { method: "PATCH", body });
}

export function apiDelete(path: string): Promise<void> {
  return apiRequest<void>(path, { method: "DELETE" });
}
