import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, View } from "react-native";

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
  createStaffAvailabilityException,
  deleteStaffAvailabilityException,
  getStaffAppointments,
  getStaffAvailabilityExceptions,
  getStaffWeeklyAvailability,
  updateStaffWeeklyAvailability,
} from "@/services/api/bookings";
import { ApiError } from "@/services/api/client";
import { useTheme } from "@/theme/ThemeProvider";

const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
type EditableRule = {
  key: string;
  weekday: number;
  local_start: string;
  local_end: string;
};

function staffError(error: unknown) {
  if (
    error instanceof ApiError &&
    error.details &&
    typeof error.details === "object"
  ) {
    for (const value of Object.values(
      error.details as Record<string, unknown>,
    )) {
      if (Array.isArray(value) && value.length) return String(value[0]);
      if (value && typeof value === "object") {
        for (const nested of Object.values(value as Record<string, unknown>))
          if (Array.isArray(nested) && nested.length) return String(nested[0]);
      }
    }
  }
  return getApiErrorMessage(error);
}

function StaffGuard({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  if (!user?.is_staff) return <Redirect href="/explore" />;
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
        TK WORKSPACE
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function Choice({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={{
        cursor: "pointer",
        paddingHorizontal: theme.spacing.sm,
        paddingVertical: theme.spacing.xs,
        borderRadius: theme.radius.pill,
        borderWidth: 1,
        borderColor: selected ? theme.colors.primary : theme.colors.border,
        backgroundColor: selected
          ? theme.colors.surfaceMuted
          : theme.colors.surface,
      }}
    >
      <Text variant="caption" color={selected ? "primary" : "muted"}>
        {label}
      </Text>
    </Pressable>
  );
}

export function StaffAvailabilityScreen() {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const weekly = useQuery({
    queryKey: ["staff", "availability", "weekly"],
    queryFn: getStaffWeeklyAvailability,
  });
  const exceptions = useQuery({
    queryKey: ["staff", "availability", "exceptions"],
    queryFn: getStaffAvailabilityExceptions,
  });
  const deviceTimezone =
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const [draft, setDraft] = useState<{
    timezone: string;
    rules: EditableRule[];
  } | null>(null);
  const [saved, setSaved] = useState(false);
  const [exceptionDate, setExceptionDate] = useState("");
  const [kind, setKind] = useState<"BLOCKED" | "EXTRA">("BLOCKED");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [note, setNote] = useState("");
  const timezone = draft?.timezone ?? weekly.data?.timezone ?? deviceTimezone;
  const rules =
    draft?.rules ??
    weekly.data?.rules.map((item) => ({
      key: item.public_id,
      weekday: item.weekday,
      local_start: item.local_start,
      local_end: item.local_end,
    })) ??
    [];
  const setTimezone = (value: string) => setDraft({ timezone: value, rules });
  const setRules = (update: (current: EditableRule[]) => EditableRule[]) =>
    setDraft({ timezone, rules: update(rules) });
  const save = useMutation({
    mutationFn: () =>
      updateStaffWeeklyAvailability(
        timezone,
        rules.map((item) => ({
          weekday: item.weekday,
          local_start: item.local_start,
          local_end: item.local_end,
          is_active: true,
        })),
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(["staff", "availability", "weekly"], data);
      setDraft({
        timezone: data.timezone,
        rules: data.rules.map((item) => ({
          key: item.public_id,
          weekday: item.weekday,
          local_start: item.local_start,
          local_end: item.local_end,
        })),
      });
      setSaved(true);
    },
  });
  const addException = useMutation({
    mutationFn: () =>
      createStaffAvailabilityException({
        date: exceptionDate,
        kind,
        local_start: kind === "EXTRA" || start || end ? start : null,
        local_end: kind === "EXTRA" || start || end ? end : null,
        timezone,
        note,
      }),
    onSuccess: async () => {
      setExceptionDate("");
      setStart("");
      setEnd("");
      setNote("");
      await queryClient.invalidateQueries({
        queryKey: ["staff", "availability", "exceptions"],
      });
    },
  });
  const removeException = useMutation({
    mutationFn: deleteStaffAvailabilityException,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["staff", "availability", "exceptions"],
      }),
  });
  const updateRule = (key: string, patch: Partial<EditableRule>) => {
    setSaved(false);
    setRules((current) =>
      current.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  };
  return (
    <StaffGuard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Availability" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Set the rhythm of your week.</Text>
          <Text color="muted">
            Clients only see server-generated times that fit these hours and
            their consultation duration.
          </Text>
        </View>
        {weekly.isLoading || exceptions.isLoading ? <LoadingIndicator /> : null}
        {weekly.isError || exceptions.isError ? (
          <Text color="danger">
            {staffError(weekly.error || exceptions.error)}
          </Text>
        ) : null}
        <Card style={{ gap: theme.spacing.md }}>
          <Text variant="heading">Schedule timezone</Text>
          <TextField
            label="IANA timezone"
            value={timezone}
            onChangeText={(value) => {
              setSaved(false);
              setTimezone(value);
            }}
            placeholder="Europe/London"
          />
          <Text variant="caption" color="muted">
            All weekly hours and exceptions below are interpreted in this
            timezone.
          </Text>
        </Card>
        <View style={{ gap: theme.spacing.md }}>
          <Text variant="heading">Weekly hours</Text>
          {rules.map((rule) => (
            <Card key={rule.key} style={{ gap: theme.spacing.md }}>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: theme.spacing.xs,
                }}
              >
                {days.map((day, index) => (
                  <Choice
                    key={day}
                    label={day.slice(0, 3)}
                    selected={rule.weekday === index}
                    onPress={() => updateRule(rule.key, { weekday: index })}
                  />
                ))}
              </View>
              <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                <TextField
                  style={{ flex: 1 }}
                  label="Starts (HH:MM)"
                  value={rule.local_start}
                  onChangeText={(value) =>
                    updateRule(rule.key, { local_start: value })
                  }
                />
                <TextField
                  style={{ flex: 1 }}
                  label="Ends (HH:MM)"
                  value={rule.local_end}
                  onChangeText={(value) =>
                    updateRule(rule.key, { local_end: value })
                  }
                />
              </View>
              <Button
                variant="ghost"
                onPress={() => {
                  setSaved(false);
                  setRules((current) =>
                    current.filter((item) => item.key !== rule.key),
                  );
                }}
              >
                Remove hours
              </Button>
            </Card>
          ))}
          {!rules.length ? (
            <Card>
              <Text color="muted">
                No weekly hours. Clients will not see bookable times unless
                extra availability is added below.
              </Text>
            </Card>
          ) : null}
          <Button
            variant="secondary"
            onPress={() => {
              setSaved(false);
              setRules((current) => [
                ...current,
                {
                  key: `new-${Date.now()}`,
                  weekday: 0,
                  local_start: "09:00",
                  local_end: "17:00",
                },
              ]);
            }}
          >
            Add weekly hours
          </Button>
          {saved ? (
            <View accessibilityLiveRegion="polite">
              <Text variant="bodyStrong" color="primary">
                Weekly availability saved.
              </Text>
            </View>
          ) : null}
          {save.isError ? (
            <Text color="danger">{staffError(save.error)}</Text>
          ) : null}
          <Button loading={save.isPending} onPress={() => save.mutate()}>
            Save weekly availability
          </Button>
        </View>
        <Divider />
        <View style={{ gap: theme.spacing.md }}>
          <Text variant="heading">Date exceptions</Text>
          <Card style={{ gap: theme.spacing.md }}>
            <TextField
              label="Date (YYYY-MM-DD)"
              value={exceptionDate}
              onChangeText={setExceptionDate}
              placeholder="2026-09-20"
            />
            <View style={{ flexDirection: "row", gap: theme.spacing.xs }}>
              <Choice
                label="Block time"
                selected={kind === "BLOCKED"}
                onPress={() => setKind("BLOCKED")}
              />
              <Choice
                label="Add extra hours"
                selected={kind === "EXTRA"}
                onPress={() => setKind("EXTRA")}
              />
            </View>
            <Text color="muted">
              {kind === "BLOCKED"
                ? "Leave both times empty to block the whole day."
                : "Enter the extra hours clients may book."}
            </Text>
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <TextField
                style={{ flex: 1 }}
                label="Starts (optional)"
                value={start}
                onChangeText={setStart}
                placeholder="09:00"
              />
              <TextField
                style={{ flex: 1 }}
                label="Ends (optional)"
                value={end}
                onChangeText={setEnd}
                placeholder="12:00"
              />
            </View>
            <TextField
              label="Private schedule note (optional)"
              value={note}
              maxLength={160}
              onChangeText={setNote}
            />
            <Button
              disabled={!exceptionDate}
              loading={addException.isPending}
              onPress={() => addException.mutate()}
            >
              Add exception
            </Button>
            {addException.isError ? (
              <Text color="danger">{staffError(addException.error)}</Text>
            ) : null}
          </Card>
          {exceptions.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
              <Text variant="overline" color="accent">
                {item.kind === "BLOCKED" ? "BLOCKED" : "EXTRA HOURS"}
              </Text>
              <Text variant="bodyStrong">
                {new Date(`${item.date}T12:00:00`).toLocaleDateString(
                  undefined,
                  {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  },
                )}
              </Text>
              <Text color="muted">
                {item.local_start && item.local_end
                  ? `${item.local_start}–${item.local_end}`
                  : "Whole day"}
                {item.note ? ` · ${item.note}` : ""}
              </Text>
              <Button
                variant="ghost"
                loading={
                  removeException.isPending &&
                  removeException.variables === item.public_id
                }
                onPress={() => removeException.mutate(item.public_id)}
              >
                Remove exception
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </StaffGuard>
  );
}

function staffAppointmentTime(item: Appointment) {
  const start = new Date(item.starts_at);
  const end = new Date(item.ends_at);
  return `${start.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })} · ${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}–${end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}

export function StaffAppointmentListScreen() {
  const theme = useTheme();
  const router = useRouter();
  const appointments = useQuery({
    queryKey: ["staff", "appointments"],
    queryFn: getStaffAppointments,
  });
  return (
    <StaffGuard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Appointments" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Your consultation calendar.</Text>
          <Text color="muted">
            Payment-pending holds and confirmed appointments appear here.
            Expired and cancelled records remain visible for context.
          </Text>
        </View>
        {appointments.isLoading ? <LoadingIndicator /> : null}
        {appointments.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Appointments could not load.</Text>
            <Text color="danger">{staffError(appointments.error)}</Text>
            <Button onPress={() => appointments.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {appointments.isSuccess && !appointments.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather name="calendar" size={30} color={theme.colors.textMuted} />
            <Text variant="heading">No client appointments yet.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              Bookings will appear after clients submit their photos and reserve
              an available time.
            </Text>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {appointments.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
              <Text
                variant="overline"
                color={
                  item.status === "PAYMENT_PENDING"
                    ? "accent"
                    : item.status === "CONFIRMED"
                      ? "primary"
                      : "muted"
                }
              >
                {item.status_label}
              </Text>
              <Text variant="heading">{item.client_name}</Text>
              <Text>{item.service_name}</Text>
              <Text color="muted">{staffAppointmentTime(item)}</Text>
              <Text variant="caption" color="muted">
                Client timezone: {item.client_timezone}
              </Text>
              {item.status === "CONFIRMED" ? (
                <Button onPress={() => router.push("/messages" as Href)}>
                  Message client
                </Button>
              ) : null}
            </Card>
          ))}
        </View>
      </Screen>
    </StaffGuard>
  );
}
