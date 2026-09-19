type ApiRuntime = {
  explicitUrl?: string;
  configuredUrl?: string;
  hostUri?: string | null;
  browserHostname?: string;
  isWeb?: boolean;
};

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function isPrivateDevelopmentUrl(value: string): boolean {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:") return false;
    if (url.hostname === "localhost" || url.hostname === "127.0.0.1")
      return true;
    if (url.hostname.startsWith("10.") || url.hostname.startsWith("192.168."))
      return true;
    const match = /^172\.(\d+)\./.exec(url.hostname);
    return Boolean(match && Number(match[1]) >= 16 && Number(match[1]) <= 31);
  } catch {
    return false;
  }
}

export function resolveApiBaseUrl({
  explicitUrl,
  configuredUrl,
  hostUri,
  browserHostname,
  isWeb = false,
}: ApiRuntime): string {
  const metroHost = hostUri?.replace(/:\d+$/, "");
  const tunnelHost = isWeb
    ? browserHostname?.endsWith(".exp.direct")
      ? browserHostname
      : undefined
    : metroHost?.endsWith(".exp.direct")
      ? metroHost
      : undefined;
  const hasTunnelBridge = Boolean(tunnelHost);

  if (
    explicitUrl?.trim() &&
    !(hasTunnelBridge && isPrivateDevelopmentUrl(explicitUrl.trim()))
  ) {
    return withoutTrailingSlash(explicitUrl.trim());
  }

  if (hasTunnelBridge) {
    return `https://${tunnelHost}/__hairdoc_api/api/v1`;
  }

  // Keep local web and API on the same site so the rotating HTTP-only refresh
  // cookie survives a page reload. Native still uses the detected LAN host.
  if (
    isWeb &&
    browserHostname &&
    configuredUrl?.trim() &&
    isPrivateDevelopmentUrl(configuredUrl.trim())
  ) {
    const configured = new URL(configuredUrl.trim());
    configured.hostname = browserHostname;
    return withoutTrailingSlash(configured.toString());
  }

  if (configuredUrl?.trim()) {
    return withoutTrailingSlash(configuredUrl.trim());
  }

  const host = browserHostname || metroHost || "127.0.0.1";
  return `http://${host}:8000/api/v1`;
}
