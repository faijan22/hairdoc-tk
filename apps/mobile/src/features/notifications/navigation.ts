import type { Href } from "expo-router";

const allowedRoutes = [
  /^\/messages\/[0-9a-f-]{36}$/i,
  /^\/appointments\/[0-9a-f-]{36}$/i,
  /^\/staff\/appointments$/,
  /^\/staff\/consultations\/[0-9a-f-]{36}$/i,
  /^\/plans\/[0-9a-f-]{36}$/i,
  /^\/staff\/progress\/[0-9a-f-]{36}$/i,
  /^\/progress\/[0-9a-f-]{36}$/i,
];

export function safeNotificationHref(route: unknown): Href {
  if (
    typeof route === "string" &&
    allowedRoutes.some((pattern) => pattern.test(route))
  ) {
    return route as Href;
  }
  return "/notifications" as Href;
}
