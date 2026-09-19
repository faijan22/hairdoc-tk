import { ComponentProps } from "react";
import { Text as NativeText, StyleProp, TextStyle } from "react-native";

import { useTheme } from "@/theme/ThemeProvider";
import { typography } from "@/theme/tokens";

type TextVariant = keyof typeof typography;

type AppTextProps = ComponentProps<typeof NativeText> & {
  variant?: TextVariant;
  color?: "default" | "muted" | "primary" | "accent" | "danger";
  style?: StyleProp<TextStyle>;
};

export function AppText({ variant = "body", color = "default", style, ...props }: AppTextProps) {
  const { colors } = useTheme();
  const colorValue = {
    default: colors.text,
    muted: colors.textMuted,
    primary: colors.primary,
    accent: colors.accent,
    danger: colors.danger,
  }[color];

  return (
    <NativeText
      {...props}
      style={[
        typography[variant],
        { color: colorValue },
        style,
      ]}
    />
  );
}
