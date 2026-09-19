import Feather from "@expo/vector-icons/Feather";
import { useRouter } from "expo-router";
import { ComponentProps } from "react";
import { Pressable, useWindowDimensions, View } from "react-native";
import Animated, {
  FadeInDown,
  FadeInRight,
  useReducedMotion,
} from "react-native-reanimated";

import { Button, Screen, Text } from "@/components/ui";
import { motion } from "@/theme/motion";
import { useTheme } from "@/theme/ThemeProvider";

type IconName = ComponentProps<typeof Feather>["name"];

const benefits: { icon: IconName; title: string; body: string }[] = [
  {
    icon: "lock",
    title: "Private by design",
    body: "Your consultation details and photos stay inside your protected account.",
  },
  {
    icon: "camera",
    title: "Show, don’t explain",
    body: "Share useful hair and scalp views when you choose, directly with TK.",
  },
  {
    icon: "compass",
    title: "Keep your direction",
    body: "Return to appointments, guidance, messages, and progress in one place.",
  },
];

function FeatureCard({
  icon,
  title,
  body,
  wide,
}: {
  icon: IconName;
  title: string;
  body: string;
  wide: boolean;
}) {
  const theme = useTheme();
  return (
    <View
      style={{
        width: wide ? "31.8%" : "100%",
        minHeight: 180,
        padding: 22,
        gap: 18,
        borderRadius: 28,
        backgroundColor: "rgba(255,255,255,0.82)",
        borderWidth: 1,
        borderColor: "rgba(24,76,57,0.08)",
        ...theme.elevation.card,
      }}
    >
      <View
        style={{
          width: 44,
          height: 44,
          borderRadius: 16,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#E0EBE3",
        }}
      >
        <Feather name={icon} size={20} color="#184C39" />
      </View>
      <View style={{ gap: 6 }}>
        <Text variant="heading">{title}</Text>
        <Text color="muted">{body}</Text>
      </View>
    </View>
  );
}

export function PublicLandingScreen() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const { width } = useWindowDimensions();
  const desktop = width >= 900;
  const tablet = width >= 680;
  const duration = reduceMotion ? 0 : motion.duration.normal;

  return (
    <Screen
      contentStyle={{
        maxWidth: 1180,
        gap: desktop ? 38 : 26,
        paddingHorizontal: desktop ? 40 : 20,
        paddingTop: desktop ? 22 : 10,
        paddingBottom: 48,
      }}
    >
      <Animated.View
        entering={FadeInDown.duration(duration)}
        style={{
          minHeight: 54,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <View style={{ flexDirection: "row", alignItems: "center", gap: 11 }}>
          <View
            style={{
              width: 42,
              height: 42,
              borderRadius: 15,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#184C39",
            }}
          >
            <Text
              variant="bodyStrong"
              style={{ color: "#FFFFFF", letterSpacing: -0.5 }}
            >
              TK
            </Text>
          </View>
          <View>
            <Text variant="bodyStrong">HairDoc TK</Text>
            <Text variant="caption" color="muted">
              Private hair care
            </Text>
          </View>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          {tablet ? (
            <Text variant="caption" color="muted">
              Already have an account?
            </Text>
          ) : null}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Sign in"
            onPress={() => router.push("/auth/sign-in")}
            style={({ pressed }) => ({
              cursor: "pointer",
              minHeight: 44,
              paddingHorizontal: 20,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 22,
              backgroundColor: pressed ? "#E3EAE5" : "#FFFFFF",
            })}
          >
            <Text variant="bodyStrong">Sign in</Text>
          </Pressable>
        </View>
      </Animated.View>

      <View
        style={{
          minHeight: desktop ? 570 : undefined,
          flexDirection: desktop ? "row" : "column",
          overflow: "hidden",
          borderRadius: desktop ? 42 : 32,
          backgroundColor: "#E5EEE7",
        }}
      >
        <Animated.View
          entering={FadeInDown.delay(reduceMotion ? 0 : 80).duration(duration)}
          style={{
            width: desktop ? "57%" : "100%",
            minHeight: desktop ? 570 : 470,
            justifyContent: "center",
            padding: desktop ? 58 : 28,
            gap: desktop ? 26 : 22,
          }}
        >
          <View
            style={{
              alignSelf: "flex-start",
              flexDirection: "row",
              alignItems: "center",
              gap: 8,
              paddingHorizontal: 13,
              paddingVertical: 8,
              borderRadius: 18,
              backgroundColor: "rgba(255,255,255,0.72)",
            }}
          >
            <View
              style={{
                width: 7,
                height: 7,
                borderRadius: 4,
                backgroundColor: "#5C836B",
              }}
            />
            <Text variant="caption" style={{ color: "#355C47" }}>
              ONE-TO-ONE WITH TK
            </Text>
          </View>
          <Text
            variant="display"
            style={{
              maxWidth: 650,
              fontSize: desktop ? 66 : 43,
              lineHeight: desktop ? 69 : 47,
              letterSpacing: desktop ? -2.4 : -1.3,
              color: "#102117",
            }}
          >
            Hair care that starts with listening.
          </Text>
          <Text
            style={{
              maxWidth: 570,
              fontSize: desktop ? 19 : 17,
              lineHeight: desktop ? 29 : 26,
              color: "#526158",
            }}
          >
            Create your private space to share what matters, prepare for your
            consultation, and keep TK’s guidance close.
          </Text>
          <View
            style={{
              flexDirection: tablet ? "row" : "column",
              alignItems: tablet ? "center" : "stretch",
              gap: 12,
              paddingTop: 6,
            }}
          >
            <Button onPress={() => router.push("/auth/sign-up")}>
              Create your account
            </Button>
            <Button
              variant="ghost"
              onPress={() => router.push("/auth/sign-in")}
            >
              I already have an account
            </Button>
          </View>
          <View
            style={{
              flexDirection: "row",
              flexWrap: "wrap",
              gap: 16,
              paddingTop: 6,
            }}
          >
            {["Private photo sharing", "Direct messages with TK"].map(
              (label) => (
                <View
                  key={label}
                  style={{ flexDirection: "row", alignItems: "center", gap: 7 }}
                >
                  <Feather name="check" size={16} color="#527663" />
                  <Text variant="caption" style={{ color: "#526158" }}>
                    {label}
                  </Text>
                </View>
              ),
            )}
          </View>
        </Animated.View>

        <Animated.View
          entering={FadeInRight.delay(reduceMotion ? 0 : 150).duration(
            duration,
          )}
          style={{
            width: desktop ? "43%" : "100%",
            minHeight: desktop ? 570 : 390,
            overflow: "hidden",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#CADDCF",
          }}
        >
          <View
            pointerEvents="none"
            style={{
              position: "absolute",
              width: 330,
              height: 330,
              borderRadius: 165,
              top: -118,
              right: -98,
              backgroundColor: "#B4CCBC",
            }}
          />
          <View
            pointerEvents="none"
            style={{
              position: "absolute",
              width: 190,
              height: 190,
              borderRadius: 95,
              bottom: -72,
              left: -45,
              backgroundColor: "#F1DDBF",
              opacity: 0.72,
            }}
          />
          <View
            style={{
              width: desktop ? "78%" : "82%",
              maxWidth: 365,
              padding: 24,
              marginVertical:desktop ? 0 : 30,
              gap: 20,
              borderRadius: 30,
              backgroundColor: "rgba(255,255,255,0.88)",
              borderWidth: 1,
              borderColor: "rgba(255,255,255,0.72)",
              shadowColor: "#173D2D",
              shadowOpacity: 0.12,
              shadowRadius: 26,
              shadowOffset: { width: 0, height: 16 },
              elevation: 7,
            }}
          >
            <View
              style={{
                flexDirection: "row",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <View
                style={{
                  width: 46,
                  height: 46,
                  borderRadius: 17,
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: "#E4EEE7",
                }}
              >
                <Feather name="heart" size={21} color="#184C39" />
              </View>
              <View
                style={{
                  paddingHorizontal: 11,
                  paddingVertical: 6,
                  borderRadius: 14,
                  backgroundColor: "#F5EFE5",
                }}
              >
                <Text variant="caption" style={{ color: "#765F3F" }}>
                  Your private space
                </Text>
              </View>
            </View>
            <View style={{ gap: 6 }}>
              <Text variant="title" style={{ color: "#102117" }}>
                A clearer starting point.
              </Text>
              <Text style={{ color: "#667069" }}>
                Everything TK needs to understand your goals, organised before
                you meet.
              </Text>
            </View>
            <View style={{ gap: 10 }}>
              {[
                ["message-square", "Tell your story"],
                ["camera", "Add useful photos"],
                ["calendar", "Choose your time"],
              ].map(([icon, label], index) => (
                <View
                  key={label}
                  style={{
                    minHeight: 55,
                    paddingHorizontal: 14,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: 12,
                    borderRadius: 18,
                    backgroundColor: index === 0 ? "#EAF1EC" : "#F7F8F6",
                  }}
                >
                  <View
                    style={{
                      width: 31,
                      height: 31,
                      borderRadius: 11,
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: "#FFFFFF",
                    }}
                  >
                    <Feather
                      name={icon as IconName}
                      size={15}
                      color="#527663"
                    />
                  </View>
                  <Text variant="bodyStrong" style={{ color: "#27342C" }}>
                    {label}
                  </Text>
                  {index === 0 ? (
                    <Feather
                      name="arrow-right"
                      size={16}
                      color="#527663"
                      style={{ marginLeft: "auto" }}
                    />
                  ) : null}
                </View>
              ))}
            </View>
          </View>
        </Animated.View>
      </View>

      <Animated.View
        entering={FadeInDown.delay(reduceMotion ? 0 : 230).duration(duration)}
        style={{ gap: 18 }}
      >
        <View style={{ maxWidth: 600, gap: 5 }}>
          <Text variant="overline" color="primary">
            BUILT AROUND YOUR CARE
          </Text>
          <Text variant="title">
            Simple where it should be. Personal where it matters.
          </Text>
        </View>
        <View
          style={{
            flexDirection: desktop ? "row" : "column",
            justifyContent: "space-between",
            gap: 14,
          }}
        >
          {benefits.map((benefit) => (
            <FeatureCard key={benefit.title} {...benefit} wide={desktop} />
          ))}
        </View>
      </Animated.View>
    </Screen>
  );
}
