import { ComponentProps, PropsWithChildren } from "react";
import { Pressable, StyleProp, View, ViewStyle } from "react-native";
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";

import { AppText } from "./AppText";
import { LoadingIndicator } from "./LoadingIndicator";

import { motion } from "@/theme/motion";
import { useTheme } from "@/theme/ThemeProvider";

type ButtonProps = PropsWithChildren<
  Omit<ComponentProps<typeof Pressable>, "style"> & {
    loading?: boolean;
    variant?: "primary" | "secondary" | "ghost" | "danger";
    style?: StyleProp<ViewStyle>;
  }
>;

export function Button({
  children,
  disabled,
  loading = false,
  variant = "primary",
  style,
  onPressIn,
  onPressOut,
  ...props
}: ButtonProps) {
  const theme = useTheme();
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  const isDisabled = disabled || loading;
  const isUnavailable = Boolean(disabled);
  const backgroundColor =
    variant === "primary"
      ? theme.colors.primary
      : variant === "danger"
        ? theme.colors.danger
        : variant === "secondary"
          ? theme.colors.surfaceMuted
          : "transparent";
  const foregroundColor =
    variant === "primary" || variant === "danger"
      ? theme.colors.onPrimary
      : theme.colors.primary;

  return (
    <Animated.View style={[animatedStyle, style]}>
      <Pressable
        accessibilityRole="button"
        disabled={isDisabled}
        onPressIn={(event) => {
          scale.set(reduceMotion ? 1 : withSpring(0.98, motion.spring));
          onPressIn?.(event);
        }}
        onPressOut={(event) => {
          scale.set(reduceMotion ? 1 : withSpring(1, motion.spring));
          onPressOut?.(event);
        }}
        style={({ pressed }) => ({
          cursor: isUnavailable ? "auto" : "pointer",
          minHeight: 50,
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "row",
          gap: theme.spacing.xs,
          paddingHorizontal: theme.spacing.lg,
          borderRadius: theme.radius.pill,
          backgroundColor,
          borderWidth: 0,
          opacity: isUnavailable ? 0.5 : pressed ? 0.9 : 1,
        })}
        {...props}
      >
        <AppText
          variant="bodyStrong"
          style={{ color: foregroundColor, opacity: loading ? 0 : 1 }}
        >
          {children}
        </AppText>
        {loading ? (
          <View
            pointerEvents="none"
            style={{
              position: "absolute",
              inset: 0,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <LoadingIndicator color={foregroundColor} />
          </View>
        ) : null}
      </Pressable>
    </Animated.View>
  );
}
