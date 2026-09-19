import { usePathname } from "expo-router";
import { PropsWithChildren } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleProp,
  View,
  ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { isFloatingTabRoute } from "@/components/FloatingTabBar";
import { useAuthStore } from "@/features/auth/authStore";
import { useTheme } from "@/theme/ThemeProvider";

type ScreenProps = PropsWithChildren<{
  scroll?: boolean;
  keyboardAware?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
}>;

export function Screen({
  children,
  scroll = true,
  keyboardAware = true,
  contentStyle,
}: ScreenProps) {
  const theme = useTheme();
  const authenticated = useAuthStore(
    (state) => state.status === "authenticated",
  );
  const pathname = usePathname();
  const sharedStyle: StyleProp<ViewStyle> = [
    {
      width: "100%",
      maxWidth: theme.layout.contentMaxWidth,
      alignSelf: "center",
      paddingHorizontal: 20,
      paddingTop: theme.spacing.xl,
      paddingBottom:
        authenticated && isFloatingTabRoute(pathname) ? 124 : theme.spacing.xl,
    },
    contentStyle,
  ];

  const content = scroll ? (
    <ScrollView
      contentContainerStyle={sharedStyle}
      showsVerticalScrollIndicator={false}
      automaticallyAdjustKeyboardInsets={keyboardAware && Platform.OS === "ios"}
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[{ flex: 1 }, sharedStyle]}>{children}</View>
  );

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      edges={["top", "right", "bottom", "left"]}
    >
      {keyboardAware ? (
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={
            Platform.OS === "ios"
              ? "padding"
              : Platform.OS === "android"
                ? "height"
                : undefined
          }
          enabled={Platform.OS === "android" || !scroll}
        >
          {content}
        </KeyboardAvoidingView>
      ) : (
        content
      )}
    </SafeAreaView>
  );
}
