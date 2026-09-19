import { networkInterfaces } from "node:os";

import type { ConfigContext, ExpoConfig } from "expo/config";

function isPrivateIpv4(address: string): boolean {
  if (address.startsWith("10.") || address.startsWith("192.168.")) return true;
  const match = /^172\.(\d+)\./.exec(address);
  return Boolean(match && Number(match[1]) >= 16 && Number(match[1]) <= 31);
}

function detectLanIpv4(): string | undefined {
  const candidates = Object.entries(networkInterfaces()).flatMap(
    ([name, addresses]) =>
      (addresses ?? [])
        .filter(
          (address) =>
            address.family === "IPv4" &&
            !address.internal &&
            isPrivateIpv4(address.address),
        )
        .map((address) => {
          const normalizedName = name.toLowerCase();
          const physicalAdapter = /^(wi-?fi|wireless|ethernet)/.test(
            normalizedName,
          )
            ? 100
            : 0;
          const virtualAdapter =
            /(vethernet|virtual|docker|wsl|hyper-v|loopback)/.test(
              normalizedName,
            )
              ? -200
              : 0;
          const commonLanRange = address.address.startsWith("192.168.")
            ? 30
            : address.address.startsWith("10.")
              ? 20
              : 10;
          return {
            address: address.address,
            score: physicalAdapter + virtualAdapter + commonLanRange,
          };
        }),
  );

  return candidates.sort((left, right) => right.score - left.score)[0]?.address;
}

export default ({ config }: ConfigContext): ExpoConfig => {
  const explicitApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
  const lanIp = process.env.EAS_BUILD === "true" ? undefined : detectLanIpv4();
  const developmentApiUrl =
    explicitApiUrl || (lanIp ? `http://${lanIp}:8000/api/v1` : undefined);

  return {
    ...config,
    name: config.name || "HairDoc TK",
    slug: config.slug || "hairdoc-tk",
    plugins: [
      ...(config.plugins ?? []),
      "expo-font",
      [
        "expo-notifications",
        { defaultChannel: "care-updates", color: "#184C39" },
      ],
    ],
    extra: {
      ...config.extra,
      developmentApiUrl,
    },
  };
};
