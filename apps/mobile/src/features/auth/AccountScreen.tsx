import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Modal, Pressable, StyleSheet, View } from "react-native";

import { useAuthStore } from "./authStore";
import { getApiErrorMessage } from "./errors";

import { Button, Card, LoadingIndicator, Screen, Text } from "@/components/ui";
import { getSessions, revokeSession } from "@/services/api/auth";
import { useTheme } from "@/theme/ThemeProvider";

export function AccountScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const theme = useTheme();
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);
  const signOutEverywhere = useAuthStore((state) => state.signOutEverywhere);
  const [confirmAllVisible, setConfirmAllVisible] = useState(false);
  const [signingOutEverywhere, setSigningOutEverywhere] = useState(false);
  const sessions = useQuery({ queryKey: ["auth", "sessions", user?.public_id], queryFn: getSessions, enabled: status === "authenticated" });
  const revoke = useMutation({
    mutationFn: revokeSession,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["auth", "sessions", user?.public_id] }),
  });
  const styles = StyleSheet.create({
    screen: { gap: theme.spacing.xl },
    header: { minHeight: 48, alignItems: "center", justifyContent: "center", paddingHorizontal: 52 },
    back: { position: "absolute", left: 0, width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: theme.radius.pill, backgroundColor: theme.colors.surface },
    cards: { gap: theme.spacing.md },
    session: { gap: theme.spacing.sm },
    row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: theme.spacing.md },
    actions: { gap: theme.spacing.sm },
    modalBackdrop: { flex: 1, justifyContent: "center", alignItems: "center", padding: theme.spacing.lg, backgroundColor: "rgba(0,0,0,0.55)" },
    modalCard: { width: "100%", maxWidth: 440, gap: theme.spacing.md },
  });

  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status === "anonymous" || !user) return <Redirect href="/auth/sign-in" />;

  return (
    <Screen contentStyle={styles.screen}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Back to settings" onPress={() => router.back()} style={styles.back}>
          <Feather name="chevron-left" size={theme.iconSize.md} color={theme.colors.text} />
        </Pressable>
        <Text variant="title">Account security</Text>
      </View>

      <View style={styles.actions}>
        <Text color="muted">Change your password, review active devices, or sign out securely.</Text>
        <Button variant="secondary" onPress={() => router.push("/auth/change-password")}>Change password</Button>
      </View>

      <View style={styles.cards}>
        <Text variant="heading">Signed-in devices</Text>
        {sessions.isLoading ? <LoadingIndicator /> : null}
        {sessions.isError ? <Text color="danger">{getApiErrorMessage(sessions.error)}</Text> : null}
        {sessions.data?.map((session) => (
          <Card key={session.public_id} style={styles.session}>
            <View style={styles.row}>
              <Text variant="bodyStrong">{session.device_name}</Text>
              {session.is_current ? <Text variant="caption" color="accent">CURRENT</Text> : null}
            </View>
            <Text variant="caption" color="muted">Last active {new Date(session.last_used_at).toLocaleString()}</Text>
            {!session.is_current ? (
              <Button variant="ghost" loading={revoke.isPending && revoke.variables === session.public_id} onPress={() => revoke.mutate(session.public_id)}>Revoke device</Button>
            ) : null}
          </Card>
        ))}
      </View>

      <View style={styles.actions}>
        <Button onPress={() => void signOut()}>Sign out</Button>
        <Button variant="ghost" onPress={() => setConfirmAllVisible(true)}>Sign out on all devices</Button>
      </View>

      <Modal transparent animationType="fade" visible={confirmAllVisible} onRequestClose={() => setConfirmAllVisible(false)}>
        <View style={styles.modalBackdrop}>
          <Card accessibilityLabel="Sign out on all devices confirmation" style={styles.modalCard}>
            <Text variant="title">Sign out on all devices?</Text>
            <Text color="muted">This revokes every signed-in device, including this one. You will also be returned to the sign-in screen.</Text>
            <View style={styles.actions}>
              <Button variant="secondary" disabled={signingOutEverywhere} onPress={() => setConfirmAllVisible(false)}>Cancel</Button>
              <Button loading={signingOutEverywhere} onPress={async () => { setSigningOutEverywhere(true); await signOutEverywhere(); setConfirmAllVisible(false); }}>Sign out everywhere</Button>
            </View>
          </Card>
        </View>
      </Modal>
    </Screen>
  );
}
