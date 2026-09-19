import Feather from "@expo/vector-icons/Feather";
import { Href, useRouter } from "expo-router";
import { View } from "react-native";

import { useAuthStore } from "./authStore";

import { Button, Card, LoadingIndicator, Screen, Text } from "@/components/ui";
import { useTheme } from "@/theme/ThemeProvider";

export function AccountDeletionInfoScreen() {
  const router = useRouter();
  const theme = useTheme();
  const status = useAuthStore((state) => state.status);
  const authenticated = status === "authenticated";
  return <Screen contentStyle={{ gap: theme.spacing.xl }}>
    <View style={{ gap: theme.spacing.xs }}>
      <Text variant="overline" color="danger">HAIRDOC TK ACCOUNT CONTROL</Text>
      <Text variant="display">Delete your account and associated data.</Text>
      <Text color="muted">This page is available on the web as well as inside the app, so you can begin deletion even after uninstalling the mobile app.</Text>
    </View>
    {status === "bootstrapping" ? <LoadingIndicator /> : <Card style={{ gap: theme.spacing.md }}>
      <Feather name="trash-2" size={theme.iconSize.lg} color={theme.colors.danger} />
      <Text variant="heading">A secure three-step process</Text>
      <Text color="muted">Sign in, review what will be removed or retained, re-enter your password, then type DELETE. The request revokes every session and cannot be undone.</Text>
      <Text variant="caption" color="muted">Information that must be kept for a legal, transaction, fraud-prevention, or care-audit obligation is de-identified and retained only for the period stated in the published Privacy Policy.</Text>
      <Button variant={authenticated ? "danger" : "primary"} onPress={() => router.push((authenticated ? "/settings/delete-account" : "/auth/sign-in?next=/settings/delete-account") as Href)}>
        {authenticated ? "Start account deletion" : "Sign in to delete account"}
      </Button>
    </Card>}
    <Button variant="ghost" onPress={() => router.replace("/explore" as Href)}>Return to HairDoc TK</Button>
  </Screen>;
}
