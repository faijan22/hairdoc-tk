import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera } from "expo-camera";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useEffect, useState } from "react";
import { Linking, Modal, Pressable, View } from "react-native";

import { Button, Card, Divider, LoadingIndicator, Screen, Text } from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getApiErrorMessage } from "@/features/auth/errors";
import { ApiError } from "@/services/api/client";
import { completeVideo, getVideoState, joinVideo, reportVideoEvent } from "@/services/api/video";
import { useTheme } from "@/theme/ThemeProvider";

type PermissionState = "checking" | "ready" | "needed" | "denied";

function videoError(error: unknown) {
  if (error instanceof ApiError && error.details && typeof error.details === "object") {
    const video = (error.details as { video?: unknown }).video;
    if (Array.isArray(video) && video.length) return String(video[0]);
  }
  return getApiErrorMessage(error);
}

function Guard({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  return children;
}

function Header({ title }: { title: string }) {
  const router = useRouter();
  const theme = useTheme();
  return (
    <View style={{ minHeight: 48, justifyContent: "center", paddingLeft: 54 }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go back"
        onPress={() => router.back()}
        style={({ pressed }) => ({
          cursor: "pointer", position: "absolute", left: 0, width: 44, height: 44,
          alignItems: "center", justifyContent: "center", borderRadius: theme.radius.pill,
          backgroundColor: pressed ? theme.colors.surfaceMuted : theme.colors.surface,
        })}
      >
        <Feather name="chevron-left" size={theme.iconSize.md} color={theme.colors.text} />
      </Pressable>
      <Text variant="overline" color="accent">PRIVATE APPOINTMENT</Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function appointmentTime(startsAt: string, endsAt: string) {
  const start = new Date(startsAt); const end = new Date(endsAt);
  return `${start.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })} · ${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}–${end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}

export function VideoLobbyScreen() {
  const { appointmentId } = useLocalSearchParams<{ appointmentId: string }>();
  const router = useRouter(); const theme = useTheme();
  const [permission, setPermission] = useState<PermissionState>("checking");
  const state = useQuery({
    queryKey: ["video", appointmentId], queryFn: () => getVideoState(appointmentId),
    enabled: Boolean(appointmentId), refetchInterval: 15_000,
  });

  useEffect(() => {
    let active = true;
    Promise.all([Camera.getCameraPermissionsAsync(), Camera.getMicrophonePermissionsAsync()])
      .then(([camera, microphone]) => {
        if (!active) return;
        if (camera.granted && microphone.granted) setPermission("ready");
        else if ((!camera.canAskAgain && !camera.granted) || (!microphone.canAskAgain && !microphone.granted)) setPermission("denied");
        else setPermission("needed");
      })
      .catch(() => active && setPermission("needed"));
    return () => { active = false; };
  }, []);

  const requestPermissions = async () => {
    const [camera, microphone] = await Promise.all([
      Camera.requestCameraPermissionsAsync(), Camera.requestMicrophonePermissionsAsync(),
    ]);
    const next = camera.granted && microphone.granted ? "ready" : "denied";
    setPermission(next);
    if (next === "denied" && appointmentId) void reportVideoEvent(appointmentId, "PERMISSION_DENIED").catch(() => undefined);
  };

  if (!appointmentId) return <Redirect href="/appointments" />;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Video consultation" />
        {state.isLoading ? <LoadingIndicator /> : null}
        {state.isError ? <Card style={{ gap: theme.spacing.md }}><Text variant="heading">Video status could not load.</Text><Text color="danger">{videoError(state.error)}</Text><Button onPress={() => state.refetch()}>Try again</Button></Card> : null}
        {state.data ? <>
          <Card style={{ gap: theme.spacing.md }}>
            <View style={{ width: 46, height: 46, borderRadius: theme.radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.surfaceMuted }}>
              <Feather name={state.data.reason_code === "completed" ? "check" : "video"} size={22} color={theme.colors.primary} />
            </View>
            <Text variant="title">{state.data.service_name}</Text>
            <Text variant="bodyStrong">{appointmentTime(state.data.starts_at, state.data.ends_at)}</Text>
            <Text color="muted">{state.data.message}</Text>
          </Card>
          {state.data.reason_code !== "completed" && state.data.provider_configured ? <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Camera & microphone</Text>
            <Text color="muted">Check access before entering. The secure room starts with both devices off so you choose when to turn them on.</Text>
            {permission === "checking" ? <LoadingIndicator /> : null}
            {permission === "ready" ? <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}><Feather name="check-circle" size={20} color={theme.colors.primary} /><Text variant="bodyStrong" color="primary">Device access is ready.</Text></View> : null}
            {permission === "needed" ? <Button variant="secondary" onPress={() => void requestPermissions()}>Check camera and microphone</Button> : null}
            {permission === "denied" ? <><Text color="danger">Camera or microphone access is blocked. Allow both in device settings, then return here.</Text><Button variant="secondary" onPress={() => Linking.openSettings()}>Open device settings</Button></> : null}
          </Card> : null}
          <Card style={{ gap: theme.spacing.sm }}>
            <Text variant="bodyStrong">Private by default</Text>
            <Text color="muted">Only you and the assigned TK receive appointment-scoped access. Recording, provider chat, and screen sharing are disabled.</Text>
          </Card>
          {state.data.reason_code === "completed" ? <Button onPress={() => router.replace(`/appointments/${appointmentId}` as Href)}>Back to appointment</Button> : <Button disabled={!state.data.can_join || permission !== "ready"} onPress={() => router.push(`/video/call/${appointmentId}` as Href)}>Continue to secure room</Button>}
        </> : null}
      </Screen>
    </Guard>
  );
}

export function VideoCallScreen() {
  const { appointmentId } = useLocalSearchParams<{ appointmentId: string }>();
  const theme = useTheme(); const router = useRouter(); const queryClient = useQueryClient();
  const [hasEntered, setHasEntered] = useState(false); const [completeVisible, setCompleteVisible] = useState(false);
  const state = useQuery({ queryKey: ["video", appointmentId], queryFn: () => getVideoState(appointmentId), enabled: Boolean(appointmentId), refetchInterval: 10_000 });
  const launch = useMutation({ mutationFn: async () => {
    const grant = await joinVideo(appointmentId);
    await reportVideoEvent(appointmentId, hasEntered ? "RECONNECTED" : "JOINED").catch(() => undefined);
    setHasEntered(true);
    await WebBrowser.openBrowserAsync(grant.join_url);
    await reportVideoEvent(appointmentId, "LEFT").catch(() => undefined);
    return grant;
  }, onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["video", appointmentId] }); } });
  const complete = useMutation({ mutationFn: () => completeVideo(appointmentId), onSuccess: async (updated) => { queryClient.setQueryData(["video", appointmentId], updated); await queryClient.invalidateQueries({ queryKey: ["appointments"] }); setCompleteVisible(false); } });
  if (!appointmentId) return <Redirect href="/appointments" />;
  return <Guard><Screen contentStyle={{ gap: theme.spacing.xl }}><Header title="Secure call" />{state.isLoading ? <LoadingIndicator /> : null}{state.data ? <>
    <Card style={{ alignItems: "center", gap: theme.spacing.md, paddingVertical: theme.spacing.xl }}>
      <View style={{ width: 64, height: 64, borderRadius: theme.radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.surfaceMuted }}><Feather name={state.data.reason_code === "completed" ? "check" : "video"} size={28} color={theme.colors.primary} /></View>
      <Text variant="title" style={{ textAlign: "center" }}>{state.data.reason_code === "completed" ? "Consultation complete" : hasEntered ? "Ready to reconnect" : "Your private room is ready"}</Text>
      <Text color="muted" style={{ textAlign: "center" }}>{state.data.reason_code === "completed" ? "TK has completed this appointment." : "The call opens in a secure video window and returns you here when you leave."}</Text>
    </Card>
    {state.data.reason_code !== "completed" ? <><Button loading={launch.isPending} disabled={!state.data.can_join} onPress={() => launch.mutate()}>{hasEntered ? "Rejoin video call" : "Enter video call"}</Button>{launch.isError ? <Text color="danger">{videoError(launch.error)}</Text> : null}<Text variant="caption" color="muted" style={{ textAlign: "center" }}>If the connection drops, return here and tap Rejoin. A fresh short-lived access token is issued each time.</Text>{state.data.participant_role === "EXPERT" && hasEntered ? <><Divider /><Button variant="secondary" onPress={() => setCompleteVisible(true)}>Mark consultation complete</Button></> : null}</> : <Button onPress={() => router.replace((state.data.participant_role === "EXPERT" ? "/staff/appointments" : `/appointments/${appointmentId}`) as Href)}>Back to appointments</Button>}
  </> : null}{state.isError ? <Text color="danger">{videoError(state.error)}</Text> : null}<Modal transparent animationType="fade" visible={completeVisible} onRequestClose={() => setCompleteVisible(false)}><View style={{ flex: 1, justifyContent: "center", alignItems: "center", padding: theme.spacing.lg, backgroundColor: "rgba(0,0,0,0.55)" }}><Card style={{ width: "100%", maxWidth: 440, gap: theme.spacing.md }}><Text variant="title">Complete this consultation?</Text><Text color="muted">This ends appointment access for both participants. Use Rejoin first if the call is not finished.</Text>{complete.isError ? <Text color="danger">{videoError(complete.error)}</Text> : null}<Button variant="secondary" disabled={complete.isPending} onPress={() => setCompleteVisible(false)}>Keep room open</Button><Button loading={complete.isPending} onPress={() => complete.mutate()}>Complete consultation</Button></Card></View></Modal></Screen></Guard>;
}
