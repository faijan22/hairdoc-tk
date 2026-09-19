import { View } from "react-native";

import { spacing } from "@/theme/tokens";

export function Spacer({ size = "md" }: { size?: keyof typeof spacing }) {
  return <View aria-hidden style={{ height: spacing[size], width: spacing[size] }} />;
}

