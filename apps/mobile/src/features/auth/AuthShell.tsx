import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { PropsWithChildren } from "react";
import { Pressable, StyleSheet, useWindowDimensions, View } from "react-native";

import { Screen, Text } from "@/components/ui";
import { useTheme } from "@/theme/ThemeProvider";

type AuthShellProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  description: string;
  showBack?: boolean;
}>;

export function AuthShell({
  eyebrow,
  title,
  description,
  showBack = true,
  children,
}: AuthShellProps) {
  const router = useRouter();
  const theme = useTheme();
  const { width, height } = useWindowDimensions();
  const centerOnDesktop = width >= 900 && height >= 700;
  const styles = StyleSheet.create({
    screen: {
      flexGrow: 1,
      width: "100%",
      maxWidth: 480,
      justifyContent: centerOnDesktop ? "center" : "flex-start",
      gap: theme.spacing.xl,
      paddingTop: centerOnDesktop ? theme.spacing.xl : 0,
      paddingBottom: theme.spacing.xl,
    },
    topBar: {
      minHeight: 44,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
    },
    header: { gap: theme.spacing.sm, maxWidth: 420 },
    form: {
      gap: theme.spacing.md,
      padding: theme.spacing.lg,
      borderRadius: theme.radius.lg,
      backgroundColor: theme.colors.surface,
      ...theme.elevation.card,
    },
    back: {
      width: 44,
      height: 44,
      marginLeft: -theme.spacing.sm,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: theme.radius.md,
    },
  });

  return (
    <Screen keyboardAware contentStyle={styles.screen}>
      <View style={styles.topBar}>
        {showBack ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            hitSlop={8}
            onPress={() => router.back()}
            style={({ pressed }) => [
              styles.back,
              {
                backgroundColor: pressed
                  ? theme.colors.surfaceMuted
                  : "transparent",
              },
            ]}
          >
            <Feather
              name="arrow-left"
              size={theme.iconSize.md}
              color={theme.colors.text}
            />
          </Pressable>
        ) : (
          <View style={{ width: 44 }} />
        )}
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <View
            style={{
              width: 32,
              height: 32,
              borderRadius: theme.radius.pill,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: theme.colors.primary,
            }}
          >
            <Text variant="caption" style={{ color: theme.colors.onPrimary }}>
              TK
            </Text>
          </View>
          <Text variant="bodyStrong">HairDoc TK</Text>
        </View>
      </View>
      <View style={styles.header}>
        <Text variant="caption" color="primary">
          {eyebrow}
        </Text>
        <Text variant="display">{title}</Text>
        <Text color="muted">{description}</Text>
      </View>
      <View style={styles.form}>{children}</View>
    </Screen>
  );
}
