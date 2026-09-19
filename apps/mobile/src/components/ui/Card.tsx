import { PropsWithChildren } from "react";
import { StyleProp, View, ViewStyle } from "react-native";

import { useTheme } from "@/theme/ThemeProvider";

type CardProps = PropsWithChildren<{
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}>;

export function Card({ children, style, accessibilityLabel }: CardProps) {
  const theme = useTheme();

  return (
    <View
      accessibilityLabel={accessibilityLabel}
      style={[
        {
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radius.lg,
          padding: 20,
        },
        theme.elevation.card,
        style,
      ]}
    >
      {children}
    </View>
  );
}
