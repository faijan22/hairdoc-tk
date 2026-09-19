import "react-native-gesture-handler";
import "react-native-reanimated";

import { Stack } from "expo-router";
import { View } from "react-native";

import { AppProviders } from "@/providers/AppProviders";
import { useTheme } from "@/theme/ThemeProvider";

function AppNavigator() {
  const theme = useTheme();

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Stack
        screenOptions={{
          headerShown: false,
          animation: "fade",
          animationDuration: 200,
          contentStyle: { backgroundColor: theme.colors.background },
        }}
      />
    </View>
  );
}

export default function RootLayout() {
  return (
    <AppProviders>
      <AppNavigator />
    </AppProviders>
  );
}
