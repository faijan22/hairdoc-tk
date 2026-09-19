import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  View,
} from "react-native";

import {
  Button,
  Card,
  Divider,
  LoadingIndicator,
  Screen,
  Text,
  TextField,
} from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getApiErrorMessage } from "@/features/auth/errors";
import {
  Appointment,
  AvailableSlot,
  cancelAppointment,
  createAppointment,
  getAppointment,
  getAppointments,
  getAvailableSlots,
  rescheduleAppointment,
} from "@/services/api/bookings";
import { ApiError } from "@/services/api/client";
import { getConsultation } from "@/services/api/consultations";
import { useTheme } from "@/theme/ThemeProvider";

function localDateKey(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateRange(days = 14) {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  return Array.from({ length: days }, (_, index) => {
    const value = new Date(start);
    value.setDate(start.getDate() + index);
    return value;
  });
}

function currentTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

function money(amount: string, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(Number(amount));
  } catch {
    return `${currency} ${amount}`;
  }
}

function bookingError(error: unknown) {
  if (
    error instanceof ApiError &&
    error.details &&
    typeof error.details === "object"
  ) {
    for (const value of Object.values(
      error.details as Record<string, unknown>,
    )) {
      if (Array.isArray(value) && value.length) return String(value[0]);
    }
  }
  return getApiErrorMessage(error);
}

function Guard({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  return children;
}

function Header({
  title,
  eyebrow = "PRIVATE BOOKING",
  backHref,
}: {
  title: string;
  eyebrow?: string;
  backHref?: Href;
}) {
  const router = useRouter();
  const theme = useTheme();
  return (
    <View style={{ minHeight: 48, justifyContent: "center", paddingLeft: 54 }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go back"
        onPress={() => {
          if (backHref) router.replace(backHref);
          else if (router.canGoBack()) router.back();
          else router.replace("/explore");
        }}
        style={({ pressed }) => ({
          cursor: "pointer",
          position: "absolute",
          left: 0,
          width: 44,
          height: 44,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: theme.radius.pill,
          backgroundColor: pressed
            ? theme.colors.surfaceMuted
            : theme.colors.surface,
        })}
      >
        <Feather
          name="chevron-left"
          size={theme.iconSize.md}
          color={theme.colors.text}
        />
      </Pressable>
      <Text variant="overline" color="accent">
        {eyebrow}
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function appointmentTime(item: Pick<Appointment, "starts_at" | "ends_at">) {
  const start = new Date(item.starts_at);
  const end = new Date(item.ends_at);
  return `${start.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" })} · ${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}–${end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}

function statusTone(status: Appointment["status"]) {
  return status === "CANCELLED" || status === "EXPIRED" || status === "NO_SHOW"
    ? "muted"
    : status === "PAYMENT_PENDING"
      ? "accent"
      : "primary";
}

export function BookingSlotScreen() {
  const { caseId, appointmentId } = useLocalSearchParams<{
    caseId: string;
    appointmentId?: string;
  }>();
  const router = useRouter();
  const theme = useTheme();
  const timezone = currentTimezone();
  const dates = useMemo(() => dateRange(), []);
  const from = localDateKey(dates[0]);
  const to = localDateKey(dates[dates.length - 1]);
  const slots = useQuery({
    queryKey: ["booking", "slots", caseId, from, to, timezone, appointmentId],
    queryFn: () => getAvailableSlots(caseId, from, to, timezone),
    enabled: Boolean(caseId),
  });
  const [requestedDate, setRequestedDate] = useState(from);
  const grouped = useMemo(() => {
    const result: Record<string, AvailableSlot[]> = {};
    for (const slot of slots.data?.slots || [])
      (result[slot.local_date] ||= []).push(slot);
    return result;
  }, [slots.data]);
  const selectedDate = grouped[requestedDate]?.length
    ? requestedDate
    : (slots.data?.slots[0]?.local_date ?? requestedDate);
  if (!caseId) return <Redirect href={"/consult" as Href} />;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header
          title={
            appointmentId ? "Choose a new time" : "Choose your appointment"
          }
        />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">A time that works for you.</Text>
          <Text color="muted">
            Times are shown in {timezone}. Availability is generated by the
            server from TK’s current schedule.
          </Text>
        </View>
        {slots.isLoading ? <LoadingIndicator /> : null}
        {slots.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Available times could not load.</Text>
            <Text color="danger">{bookingError(slots.error)}</Text>
            <Button onPress={() => slots.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {slots.data ? (
          <>
            <Card style={{ gap: theme.spacing.xs }}>
              <Text variant="bodyStrong">{slots.data.service_name}</Text>
              <Text variant="caption" color="muted">
                {slots.data.duration_minutes} minutes with{" "}
                {slots.data.expert_name} · TK’s timezone:{" "}
                {slots.data.expert_timezone}
              </Text>
            </Card>
            <View style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Select a date</Text>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: theme.spacing.xs,
                }}
              >
                {dates.map((day) => {
                  const key = localDateKey(day);
                  const count = grouped[key]?.length || 0;
                  const active = key === selectedDate;
                  return (
                    <Pressable
                      key={key}
                      accessibilityRole="button"
                      accessibilityState={{
                        selected: active,
                        disabled: !count,
                      }}
                      disabled={!count}
                      onPress={() => setRequestedDate(key)}
                      style={{
                        cursor: count ? "pointer" : "auto",
                        minWidth: 76,
                        alignItems: "center",
                        padding: theme.spacing.sm,
                        borderWidth: 1,
                        borderColor: active
                          ? theme.colors.primary
                          : theme.colors.border,
                        borderRadius: theme.radius.md,
                        backgroundColor: active
                          ? theme.colors.surfaceMuted
                          : theme.colors.surface,
                        opacity: count ? 1 : 0.45,
                      }}
                    >
                      <Text
                        variant="caption"
                        color={active ? "primary" : "muted"}
                      >
                        {day.toLocaleDateString(undefined, {
                          weekday: "short",
                        })}
                      </Text>
                      <Text variant="bodyStrong">{day.getDate()}</Text>
                      <Text variant="caption" color="muted">
                        {count || "—"}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
            <View style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Available times</Text>
              {grouped[selectedDate]?.length ? (
                <View
                  style={{
                    flexDirection: "row",
                    flexWrap: "wrap",
                    gap: theme.spacing.sm,
                  }}
                >
                  {grouped[selectedDate].map((slot) => (
                    <Button
                      key={slot.starts_at}
                      variant="secondary"
                      onPress={() =>
                        router.push(
                          `/book/review/${caseId}?startsAt=${encodeURIComponent(slot.starts_at)}${appointmentId ? `&appointmentId=${appointmentId}` : ""}` as Href,
                        )
                      }
                    >
                      {new Date(slot.local_start).toLocaleTimeString(
                        undefined,
                        { hour: "numeric", minute: "2-digit" },
                      )}
                    </Button>
                  ))}
                </View>
              ) : (
                <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
                  <Feather
                    name="calendar"
                    size={30}
                    color={theme.colors.textMuted}
                  />
                  <Text variant="bodyStrong">No times on this date.</Text>
                  <Text color="muted">
                    Choose another available date above.
                  </Text>
                </Card>
              )}
            </View>
            {!slots.data.slots.length ? (
              <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
                <Text variant="heading">No appointments are open yet.</Text>
                <Text color="muted" style={{ textAlign: "center" }}>
                  TK can add weekly hours or date-specific availability from her
                  workspace.
                </Text>
              </Card>
            ) : null}
          </>
        ) : null}
      </Screen>
    </Guard>
  );
}

export function BookingReviewScreen() {
  const { caseId, startsAt, appointmentId } = useLocalSearchParams<{
    caseId: string;
    startsAt?: string;
    appointmentId?: string;
  }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const timezone = currentTimezone();
  const item = useQuery({
    queryKey: ["consultations", caseId],
    queryFn: () => getConsultation(caseId),
    enabled: Boolean(caseId),
  });
  const mutation = useMutation({
    mutationFn: () =>
      appointmentId
        ? rescheduleAppointment(appointmentId, startsAt!, timezone)
        : createAppointment(caseId, startsAt!, timezone),
    onSuccess: async (appointment) => {
      await queryClient.invalidateQueries({ queryKey: ["appointments"] });
      router.replace(
        (appointmentId || appointment.status === "CONFIRMED"
          ? `/appointments/${appointment.public_id}`
          : `/checkout/${appointment.public_id}`) as Href,
      );
    },
  });
  if (!caseId || !startsAt)
    return (
      <Redirect
        href={caseId ? (`/book/${caseId}` as Href) : ("/consult" as Href)}
      />
    );
  const start = new Date(startsAt);
  const end = item.data
    ? new Date(start.getTime() + item.data.duration_minutes * 60_000)
    : start;
  const isFree = item.data ? Number(item.data.price_amount) === 0 : false;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title={appointmentId ? "Review new time" : "Review booking"} />
        <Card style={{ gap: theme.spacing.md }}>
          {item.isLoading ? <LoadingIndicator /> : null}
          {item.data ? (
            <>
              <Text variant="overline" color="accent">
                {item.data.service_name}
              </Text>
              <Text variant="title">
                {start.toLocaleDateString(undefined, {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                })}
              </Text>
              <Text variant="heading">
                {start.toLocaleTimeString(undefined, {
                  hour: "numeric",
                  minute: "2-digit",
                })}
                –
                {end.toLocaleTimeString(undefined, {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </Text>
              <Text color="muted">
                {timezone} · {item.data.duration_minutes} minutes
              </Text>
              <Divider />
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <Text color="muted">Consultation price</Text>
                <Text variant="bodyStrong">
                  {money(item.data.price_amount, item.data.currency)}
                </Text>
              </View>
            </>
          ) : null}
        </Card>
        <Card style={{ gap: theme.spacing.md }}>
          <Text variant="heading">
            {appointmentId
              ? "Confirm this change"
              : isFree
                ? "Confirm your consultation"
                : "Reserve and continue to payment"}
          </Text>
          <Text color="muted">
            {appointmentId
              ? "The original time is kept until this new slot is accepted by the server."
              : isFree
                ? "This consultation has no charge. Your appointment will be confirmed immediately—no card or checkout required."
                : "The server reserves this time while you complete Square's secure checkout. Your appointment is confirmed only after verified payment."}
          </Text>
          {mutation.isError ? (
            <Text color="danger">{bookingError(mutation.error)}</Text>
          ) : null}
          <Button
            loading={mutation.isPending}
            onPress={() => mutation.mutate()}
          >
            {appointmentId
              ? "Confirm new time"
              : isFree
                ? "Confirm appointment"
                : "Continue to payment"}
          </Button>
          <Button
            variant="ghost"
            disabled={mutation.isPending}
            onPress={() => router.back()}
          >
            Choose another time
          </Button>
        </Card>
      </Screen>
    </Guard>
  );
}

function AppointmentCard({
  item,
  onPress,
}: {
  item: Appointment;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Card style={{ gap: theme.spacing.md }}>
      <View style={{ gap: theme.spacing.xs }}>
        <Text variant="overline" color={statusTone(item.status)}>
          {item.status_label}
        </Text>
        <Text variant="heading">{item.service_name}</Text>
        <Text color="muted">{appointmentTime(item)}</Text>
        <Text variant="caption" color="muted">
          With {item.expert_name}
        </Text>
      </View>
      <Button variant="secondary" onPress={onPress}>
        View appointment
      </Button>
    </Card>
  );
}

export function AppointmentListScreen() {
  const router = useRouter();
  const theme = useTheme();
  const appointments = useQuery({
    queryKey: ["appointments"],
    queryFn: getAppointments,
  });
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="My appointments" backHref="/explore" />
        {appointments.isLoading ? <LoadingIndicator /> : null}
        {appointments.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Appointments could not load.</Text>
            <Text color="danger">{bookingError(appointments.error)}</Text>
            <Button onPress={() => appointments.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {appointments.isSuccess && !appointments.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather name="calendar" size={30} color={theme.colors.textMuted} />
            <Text variant="heading">No appointments yet.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              Complete an intake and private photos before choosing a time.
            </Text>
            <Button onPress={() => router.push("/consult" as Href)}>
              Explore consultations
            </Button>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {appointments.data?.map((item) => (
            <AppointmentCard
              key={item.public_id}
              item={item}
              onPress={() =>
                router.push(`/appointments/${item.public_id}` as Href)
              }
            />
          ))}
        </View>
      </Screen>
    </Guard>
  );
}

export function AppointmentDetailScreen() {
  const { appointmentId } = useLocalSearchParams<{ appointmentId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const [cancelVisible, setCancelVisible] = useState(false);
  const [reason, setReason] = useState("");
  const item = useQuery({
    queryKey: ["appointments", appointmentId],
    queryFn: () => getAppointment(appointmentId),
    enabled: Boolean(appointmentId),
  });
  const cancel = useMutation({
    mutationFn: () => cancelAppointment(appointmentId, reason),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["appointments", appointmentId], updated);
      await queryClient.invalidateQueries({ queryKey: ["appointments"] });
      setCancelVisible(false);
    },
  });
  if (!appointmentId) return <Redirect href={"/appointments" as Href} />;
  const active =
    item.data?.status === "PAYMENT_PENDING" ||
    item.data?.status === "CONFIRMED";
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Appointment details" />
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.isError ? (
          <Text color="danger">{bookingError(item.error)}</Text>
        ) : null}
        {item.data ? (
          <>
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="overline" color={statusTone(item.data.status)}>
                {item.data.status_label}
              </Text>
              <Text variant="title">{item.data.service_name}</Text>
              <Text variant="heading">{appointmentTime(item.data)}</Text>
              <Text color="muted">
                With {item.data.expert_name} · shown in your device timezone
              </Text>
              {item.data.status === "PAYMENT_PENDING" ? (
                <>
                  <Divider />
                  <Text variant="bodyStrong" color="accent">
                    Reserved pending payment
                  </Text>
                  <Text color="muted">
                    This hold expires{" "}
                    {item.data.reservation_expires_at
                      ? new Date(
                          item.data.reservation_expires_at,
                        ).toLocaleString()
                      : "soon"}
                    . Complete Square checkout to confirm it.
                  </Text>
                  <Button
                    onPress={() =>
                      router.push(`/checkout/${item.data!.public_id}` as Href)
                    }
                  >
                    Continue to payment
                  </Button>
                </>
              ) : null}
              {item.data.status === "CONFIRMED" ? (
                <>
                  <Divider />
                  <Text variant="bodyStrong">Photo-first consultation</Text>
                  <Text color="muted">
                    TK reviews your intake and private photos first. If a live
                    call is useful, she will arrange it with you in Messages.
                  </Text>
                  <Button onPress={() => router.push("/messages" as Href)}>
                    Open Messages
                  </Button>
                </>
              ) : null}
              {item.data.status === "EXPIRED" ? (
                <>
                  <Divider />
                  <Text color="muted">
                    The payment hold expired and this time is available again.
                  </Text>
                  <Button
                    onPress={() =>
                      router.push(
                        `/book/${item.data!.consultation_public_id}` as Href,
                      )
                    }
                  >
                    Choose another time
                  </Button>
                </>
              ) : null}
              {item.data.status === "CANCELLED" && item.data.cancel_reason ? (
                <>
                  <Divider />
                  <Text variant="caption" color="muted">
                    Cancellation note
                  </Text>
                  <Text>{item.data.cancel_reason}</Text>
                </>
              ) : null}
            </Card>
            {active ? (
              <View style={{ gap: theme.spacing.sm }}>
                <Button
                  variant="secondary"
                  onPress={() =>
                    router.push(
                      `/book/${item.data!.consultation_public_id}?appointmentId=${item.data!.public_id}` as Href,
                    )
                  }
                >
                  Reschedule
                </Button>
                <Button variant="ghost" onPress={() => setCancelVisible(true)}>
                  Cancel appointment
                </Button>
              </View>
            ) : null}
          </>
        ) : null}
        <Modal
          transparent
          animationType="fade"
          visible={cancelVisible}
          onRequestClose={() => setCancelVisible(false)}
        >
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : "height"}
            style={{
              flex: 1,
              justifyContent: "center",
              alignItems: "center",
              padding: theme.spacing.lg,
              backgroundColor: "rgba(0,0,0,0.55)",
            }}
          >
            <Card
              style={{ width: "100%", maxWidth: 440, gap: theme.spacing.md }}
            >
              <Text variant="title">Cancel this appointment?</Text>
              <Text color="muted">
                The reserved time will be released for someone else.
              </Text>
              <TextField
                label="Reason (optional)"
                value={reason}
                maxLength={300}
                onChangeText={setReason}
              />
              <Button
                variant="secondary"
                disabled={cancel.isPending}
                onPress={() => setCancelVisible(false)}
              >
                Keep appointment
              </Button>
              <Button
                loading={cancel.isPending}
                onPress={() => cancel.mutate()}
              >
                Cancel appointment
              </Button>
              {cancel.isError ? (
                <Text color="danger">{bookingError(cancel.error)}</Text>
              ) : null}
            </Card>
          </KeyboardAvoidingView>
        </Modal>
      </Screen>
    </Guard>
  );
}
