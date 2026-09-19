import { Feather } from "@expo/vector-icons";
import { Redirect, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import Animated, {
  FadeIn,
  FadeInDown,
  FadeOut,
  useReducedMotion,
} from "react-native-reanimated";

import { useOnboardingStore } from "./onboardingStore";

import { Button, LoadingIndicator, Screen, Text } from "@/components/ui";
import { motion } from "@/theme/motion";
import { useTheme } from "@/theme/ThemeProvider";

const steps = [
  {
    icon: "search" as const,
    label: "Personal guidance",
    title: "Start with what your hair needs.",
    body: "Share your concerns, goals, lifestyle, and hair history privately before meeting with TK.",
  },
  {
    icon: "camera" as const,
    label: "Useful context",
    title: "Arrive with the right details.",
    body: "Complete your intake and add the requested hair or scalp photos at your own pace.",
  },
  {
    icon: "message-circle" as const,
    label: "Private connection",
    title: "Keep care in one clear place.",
    body: "Book your appointment, message TK, and return to the details you have already shared.",
  },
] as const;

export function OnboardingScreen() {
  const router = useRouter();
  const theme = useTheme();
  const reduceMotion = useReducedMotion();
  const [stepIndex, setStepIndex] = useState(0);
  const { completed, complete, hasHydrated } = useOnboardingStore();
  const step = steps[stepIndex];
  const isLast = stepIndex === steps.length - 1;
  const duration = reduceMotion ? 0 : motion.duration.normal;
  const styles = useMemo(
    () =>
      StyleSheet.create({
        screen: {
          flexGrow: 1,
          justifyContent: "space-between",
          gap: theme.spacing.lg,
          paddingTop: theme.spacing.sm,
        },
        topBar: {
          minHeight: 44,
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        },
        brand: { flexDirection: "row", alignItems: "center", gap: 10 },
        brandMark: {
          width: 32,
          height: 32,
          borderRadius: theme.radius.pill,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.primary,
        },
        skip: {
          minHeight: 44,
          justifyContent: "center",
          paddingHorizontal: theme.spacing.sm,
        },
        visual: {
          height: 290,
          borderRadius: 32,
          overflow: "hidden",
          padding: theme.spacing.lg,
          justifyContent: "space-between",
          backgroundColor: theme.colors.primaryMuted,
        },
        washLarge: {
          position: "absolute",
          width: 270,
          height: 270,
          borderRadius: 135,
          right: -92,
          top: -88,
          backgroundColor: theme.colors.decorative,
          opacity: 0.72,
        },
        washSmall: {
          position: "absolute",
          width: 128,
          height: 128,
          borderRadius: 64,
          left: -38,
          bottom: -42,
          backgroundColor: theme.colors.surface,
          opacity: 0.72,
        },
        visualTop: {
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        },
        stepBadge: {
          minWidth: 46,
          height: 32,
          paddingHorizontal: theme.spacing.sm,
          borderRadius: theme.radius.pill,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.surface,
        },
        iconDisc: {
          width: 104,
          height: 104,
          alignSelf: "center",
          borderRadius: 52,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.surface,
          shadowColor: "#102117",
          shadowOpacity: 0.08,
          shadowRadius: 18,
          shadowOffset: { width: 0, height: 8 },
          elevation: 4,
        },
        content: { minHeight: 156, gap: theme.spacing.sm },
        copy: { maxWidth: 520 },
        footer: { gap: theme.spacing.md },
        progress: { flexDirection: "row", gap: 6 },
        segment: { height: 5, flex: 1, borderRadius: theme.radius.pill },
      }),
    [theme],
  );

  if (!hasHydrated)
    return (
      <Screen
        scroll={false}
        contentStyle={{ alignItems: "center", justifyContent: "center" }}
      >
        <LoadingIndicator />
      </Screen>
    );
  if (completed) return <Redirect href="/explore" />;
  const finish = () => {
    complete();
    router.replace("/explore");
  };

  return (
    <Screen contentStyle={styles.screen}>
      <View style={styles.topBar}>
        <View style={styles.brand}>
          <View style={styles.brandMark}>
            <Text variant="caption" style={{ color: theme.colors.onPrimary }}>
              TK
            </Text>
          </View>
          <Text variant="bodyStrong">HairDoc TK</Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Skip introduction"
          onPress={finish}
          style={styles.skip}
        >
          <Text variant="caption" color="muted">
            Skip
          </Text>
        </Pressable>
      </View>
      <View style={styles.visual}>
        <View style={styles.washLarge} />
        <View style={styles.washSmall} />
        <View style={styles.visualTop}>
          <View style={styles.stepBadge}>
            <Text variant="caption" color="primary">
              0{stepIndex + 1}
            </Text>
          </View>
          <Text variant="caption" color="primary">
            Private by design
          </Text>
        </View>
        <Animated.View
          key={`visual-${stepIndex}`}
          entering={FadeIn.duration(duration)}
          exiting={FadeOut.duration(duration)}
          style={styles.iconDisc}
        >
          <Feather name={step.icon} size={42} color={theme.colors.primary} />
        </Animated.View>
        <Text variant="bodyStrong" color="primary">
          {step.label}
        </Text>
      </View>
      <Animated.View
        key={`copy-${stepIndex}`}
        entering={FadeInDown.duration(duration)}
        exiting={FadeOut.duration(duration)}
        style={styles.content}
      >
        <Text variant="display" style={styles.copy}>
          {step.title}
        </Text>
        <Text color="muted" style={styles.copy}>
          {step.body}
        </Text>
      </Animated.View>
      <View style={styles.footer}>
        <View
          accessibilityLabel={`Step ${stepIndex + 1} of ${steps.length}`}
          style={styles.progress}
        >
          {steps.map((item, index) => (
            <View
              key={item.label}
              style={[
                styles.segment,
                {
                  backgroundColor:
                    index <= stepIndex
                      ? theme.colors.primary
                      : theme.colors.border,
                },
              ]}
            />
          ))}
        </View>
        <Button
          onPress={() =>
            isLast ? finish() : setStepIndex((current) => current + 1)
          }
        >
          {isLast ? "Open HairDoc TK" : "Continue"}
        </Button>
      </View>
    </Screen>
  );
}
