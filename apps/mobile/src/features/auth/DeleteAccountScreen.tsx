import Feather from "@expo/vector-icons/Feather";
import { useMutation } from "@tanstack/react-query";
import { Href, Redirect, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, View } from "react-native";

import { useAuthStore } from "./authStore";
import { getApiErrorMessage } from "./errors";

import { Button, Card, LoadingIndicator, Screen, Text, TextField } from "@/components/ui";
import { deleteAccount } from "@/services/api/auth";
import { useTheme } from "@/theme/ThemeProvider";

export function DeleteAccountScreen() {
  const router = useRouter();
  const theme = useTheme();
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);
  const [step, setStep] = useState(1);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [understood, setUnderstood] = useState(false);
  const styles = useMemo(() => StyleSheet.create({
    screen: { gap: theme.spacing.xl },
    header: { minHeight: 48, alignItems: "center", justifyContent: "center", paddingHorizontal: 52 },
    back: { position: "absolute", left: 0, width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: theme.radius.pill, backgroundColor: theme.colors.surface },
    card: { gap: theme.spacing.md },
    row: { flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm },
    actions: { gap: theme.spacing.sm },
    check: { width: 24, height: 24, borderRadius: theme.radius.sm, borderWidth: 1, borderColor: understood ? theme.colors.danger : theme.colors.border, backgroundColor: understood ? theme.colors.danger : theme.colors.surface, alignItems: "center", justifyContent: "center" },
  }), [theme, understood]);
  const deletion = useMutation({
    mutationFn: () => deleteAccount(password, confirmation),
    onSuccess: async () => {
      await signOut();
      Alert.alert("Account deleted", "Your HairDoc TK account and removable personal data have been deleted.");
      router.replace("/auth/sign-in" as Href);
    },
  });

  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated" || !user) return <Redirect href="/auth/sign-in" />;

  return <Screen contentStyle={styles.screen} keyboardAware>
    <View style={styles.header}>
      <Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={() => step > 1 ? setStep(step - 1) : router.back()} style={styles.back}>
        <Feather name="chevron-left" size={theme.iconSize.md} color={theme.colors.text} />
      </Pressable>
      <Text variant="title">Delete account</Text>
    </View>
    <View style={{ gap: theme.spacing.xs }}>
      <Text variant="overline" color="danger">STEP {step} OF 3</Text>
      <Text variant="display">{step === 1 ? "Understand what happens." : step === 2 ? "Confirm it is you." : "Final confirmation."}</Text>
    </View>
    {user.is_staff ? <Card style={styles.card}><Text variant="heading">Care ownership must be transferred first.</Text><Text color="muted">TK and staff accounts cannot be deleted while they may own services, appointments, or client records. Transfer that work from Django Admin before deletion.</Text></Card> : null}
    {!user.is_staff && step === 1 ? <Card style={styles.card}>
      <Text variant="heading">This permanently removes your account.</Text>
      {[
        "You will be signed out on every device and cannot recover this login.",
        "Your profile, preferences, private photos, intake answers, and consultation messages are removed.",
        "Transaction or care-audit records may be retained only where law requires, without your login details; the published Privacy Policy explains the applicable retention.",
      ].map((item) => <View key={item} style={styles.row}><Feather name="minus" size={theme.iconSize.sm} color={theme.colors.danger} /><Text style={{ flex: 1 }}>{item}</Text></View>)}
      <Button onPress={() => setStep(2)}>Continue</Button>
    </Card> : null}
    {!user.is_staff && step === 2 ? <Card style={styles.card}>
      <Text color="muted">Re-enter the password for {user.email}.</Text>
      <TextField label="Current password" value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" autoCorrect={false} />
      <Button disabled={!password} onPress={() => setStep(3)}>Continue</Button>
    </Card> : null}
    {!user.is_staff && step === 3 ? <Card style={styles.card}>
      <Text color="muted">Type <Text variant="bodyStrong">DELETE</Text> exactly. This is the final step.</Text>
      <TextField label="Type DELETE" value={confirmation} onChangeText={setConfirmation} autoCapitalize="characters" autoCorrect={false} />
      <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: understood }} onPress={() => setUnderstood(!understood)} style={styles.row}>
        <View style={styles.check}>{understood ? <Feather name="check" size={16} color="#FFFFFF" /> : null}</View>
        <Text style={{ flex: 1 }}>I understand this account cannot be recovered.</Text>
      </Pressable>
      {deletion.isError ? <Text color="danger">{getApiErrorMessage(deletion.error)}</Text> : null}
      <View style={styles.actions}>
        <Button variant="secondary" disabled={deletion.isPending} onPress={() => router.back()}>Keep my account</Button>
        <Button variant="danger" loading={deletion.isPending} disabled={confirmation !== "DELETE" || !understood} onPress={() => deletion.mutate()}>Permanently delete account</Button>
      </View>
    </Card> : null}
  </Screen>;
}
