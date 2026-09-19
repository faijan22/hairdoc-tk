import { ActivityIndicator } from "react-native";

import { useTheme } from "@/theme/ThemeProvider";

export function LoadingIndicator({ color }: { color?: string }) {
  const theme = useTheme();
  return <ActivityIndicator color={color ?? theme.colors.primary} />;
}

