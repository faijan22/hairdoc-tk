import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import {
  ComponentProps,
  PropsWithChildren,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Controller, useForm } from "react-hook-form";
import { Linking, Pressable, StyleSheet, Switch, View } from "react-native";
import { z } from "zod";

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
import { applyApiFieldErrors, applyZodErrors } from "@/features/auth/formUtils";
import {
  enablePushOnThisDevice,
  pushUnavailableReason,
} from "@/features/notifications/pushNotifications";
import { getMe, updateMe } from "@/services/api/auth";
import { ApiError } from "@/services/api/client";
import {
  getConsents,
  getHairProfile,
  getLegalDocument,
  getNotificationPreferences,
  HairProfile,
  hairTextures,
  legalFileUrl,
  LegalType,
  legalTypes,
  NotificationPreferences,
  scalpTypes,
  updateConsent,
  updateHairProfile,
  updateNotificationPreferences,
} from "@/services/api/settings";
import { useTheme } from "@/theme/ThemeProvider";

type IconName = ComponentProps<typeof Feather>["name"];

function SettingsGuard({ children }: PropsWithChildren) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  return children;
}

function SettingsPage({
  title,
  children,
}: PropsWithChildren<{ title: string }>) {
  const router = useRouter();
  const theme = useTheme();
  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace("/explore");
  };
  const styles = useMemo(
    () =>
      StyleSheet.create({
        content: { gap: theme.spacing.xl },
        header: {
          minHeight: 48,
          alignItems: "center",
          justifyContent: "center",
          paddingHorizontal: 52,
        },
        back: {
          position: "absolute",
          left: 0,
          width: 44,
          height: 44,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: theme.radius.pill,
          backgroundColor: theme.colors.surface,
        },
      }),
    [theme],
  );
  return (
    <SettingsGuard>
      <Screen contentStyle={styles.content}>
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={goBack}
            style={styles.back}
          >
            <Feather
              name="chevron-left"
              size={theme.iconSize.md}
              color={theme.colors.text}
            />
          </Pressable>
          <Text variant="title">{title}</Text>
        </View>
        {children}
      </Screen>
    </SettingsGuard>
  );
}

function SettingsSection({
  title,
  children,
}: PropsWithChildren<{ title: string }>) {
  const theme = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <Text variant="heading">{title}</Text>
      <Card style={{ padding: 0, overflow: "hidden" }}>{children}</Card>
    </View>
  );
}

function SettingsRow({
  icon,
  label,
  value,
  onPress,
  last = false,
}: {
  icon: IconName;
  label: string;
  value?: string;
  onPress: () => void;
  last?: boolean;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => ({
        cursor: "pointer",
        minHeight: 66,
        paddingHorizontal: theme.spacing.md,
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.md,
        backgroundColor: pressed
          ? theme.colors.surfaceMuted
          : theme.colors.surface,
        borderBottomWidth: last ? 0 : 1,
        borderBottomColor: theme.colors.border,
      })}
    >
      <View
        style={{
          width: 38,
          height: 38,
          borderRadius: theme.radius.sm,
          backgroundColor: theme.colors.surfaceMuted,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Feather
          name={icon}
          size={theme.iconSize.sm}
          color={theme.colors.primary}
        />
      </View>
      <Text variant="bodyStrong" style={{ flex: 1 }}>
        {label}
      </Text>
      {value ? (
        <Text
          variant="caption"
          color="muted"
          numberOfLines={1}
          style={{ maxWidth: 150 }}
        >
          {value}
        </Text>
      ) : null}
      <Feather
        name="chevron-right"
        size={theme.iconSize.sm}
        color={theme.colors.textMuted}
      />
    </Pressable>
  );
}

function SavedFeedback({ children }: PropsWithChildren) {
  const theme = useTheme();
  return (
    <View
      accessibilityLiveRegion="polite"
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.xs,
        paddingHorizontal: theme.spacing.md,
        paddingVertical: theme.spacing.sm,
        borderRadius: theme.radius.md,
        backgroundColor: theme.colors.surfaceMuted,
      }}
    >
      <Feather
        name="check-circle"
        size={theme.iconSize.sm}
        color={theme.colors.success}
      />
      <Text
        variant="bodyStrong"
        color="primary"
        style={{ flex: 1, paddingRight: theme.spacing.xs }}
      >
        {children}
      </Text>
    </View>
  );
}

export function SettingsHomeScreen() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const preferences = useQuery({
    queryKey: ["settings", "preferences"],
    queryFn: getNotificationPreferences,
  });
  return (
    <SettingsPage title="Settings">
      <View style={{ gap: 4 }}>
        <Text variant="overline" color="accent">
          YOUR PRIVATE SPACE
        </Text>
        <Text color="muted">
          Manage what HairDoc TK knows and how we reach you.
        </Text>
      </View>
      <SettingsSection title="Your profile">
        <SettingsRow
          icon="user"
          label="Personal details"
          value={user?.first_name || "Add details"}
          onPress={() => router.push("/settings/personal")}
        />
        <SettingsRow
          icon="activity"
          label="Hair profile"
          onPress={() => router.push("/settings/hair-profile")}
          last
        />
      </SettingsSection>
      <SettingsSection title="Preferences">
        <SettingsRow
          icon="clock"
          label="Time zone"
          value={preferences.data?.timezone || "UTC"}
          onPress={() => router.push("/settings/timezone")}
        />
        <SettingsRow
          icon="bell"
          label="Notifications"
          onPress={() => router.push("/settings/notifications")}
          last
        />
      </SettingsSection>
      <SettingsSection title="Consultations">
        <SettingsRow
          icon="calendar"
          label="My appointments"
          onPress={() => router.push("/appointments" as Href)}
          last
        />
      </SettingsSection>
      <SettingsSection title="Privacy & legal">
        <SettingsRow
          icon="file-text"
          label="Terms of Use"
          onPress={() =>
            router.push({
              pathname: "/settings/legal/[type]",
              params: { type: "TERMS" },
            })
          }
        />
        <SettingsRow
          icon="shield"
          label="Privacy Policy"
          onPress={() =>
            router.push({
              pathname: "/settings/legal/[type]",
              params: { type: "PRIVACY" },
            })
          }
        />
        <SettingsRow
          icon="info"
          label="Consultation Disclaimer"
          onPress={() =>
            router.push({
              pathname: "/settings/legal/[type]",
              params: { type: "CONSULTATION_DISCLAIMER" },
            })
          }
        />
        <SettingsRow
          icon="camera"
          label="Photo & Data Consent"
          onPress={() =>
            router.push({
              pathname: "/settings/legal/[type]",
              params: { type: "PHOTO_DATA_CONSENT" },
            })
          }
          last
        />
      </SettingsSection>
      <SettingsSection title="Account">
        <SettingsRow
          icon="lock"
          label="Password & signed-in devices"
          onPress={() => router.push("/settings/security")}
        />
        <SettingsRow
          icon="trash-2"
          label="Delete account"
          onPress={() => router.push("/settings/delete-account" as Href)}
          last
        />
      </SettingsSection>
      {user?.is_staff ? (
        <SettingsSection title="TK workspace">
          <SettingsRow
            icon="clipboard"
            label="Consultations ready for review"
            onPress={() => router.push("/staff/consultations" as Href)}
          />
          <SettingsRow
            icon="clock"
            label="Manage availability"
            onPress={() => router.push("/staff/availability" as Href)}
          />
          <SettingsRow
            icon="calendar"
            label="Client appointments"
            onPress={() => router.push("/staff/appointments" as Href)}
          />
          <SettingsRow
            icon="message-circle"
            label="Client messages"
            onPress={() => router.push("/messages" as Href)}
            last
          />
        </SettingsSection>
      ) : null}
    </SettingsPage>
  );
}

const personalSchema = z.object({
  first_name: z.string().trim().max(150, "Use 150 characters or fewer."),
  last_name: z.string().trim().max(150, "Use 150 characters or fewer."),
  phone: z.string().trim().max(32, "Use 32 characters or fewer."),
});
type PersonalValues = z.infer<typeof personalSchema>;

export function PersonalProfileScreen() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((state) => state.setUser);
  const user = useQuery({ queryKey: ["settings", "me"], queryFn: getMe });
  const [saved, setSaved] = useState(false);
  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<PersonalValues>({
    defaultValues: { first_name: "", last_name: "", phone: "" },
  });
  useEffect(() => {
    if (user.data)
      reset({
        first_name: user.data.first_name,
        last_name: user.data.last_name,
        phone: user.data.phone,
      });
  }, [reset, user.data]);
  const submit = handleSubmit(async (values) => {
    const parsed = personalSchema.safeParse(values);
    const report = (field: string, message: string) =>
      setError(field as keyof PersonalValues, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      const updated = await updateMe(parsed.data);
      setUser(updated);
      queryClient.setQueryData(["settings", "me"], updated);
      reset(parsed.data);
      setSaved(true);
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });
  return (
    <SettingsPage title="Personal details">
      <Text color="muted">
        Your email is your sign-in ID and cannot be changed here.
      </Text>
      {user.isLoading ? <LoadingIndicator /> : null}
      {user.isError ? (
        <Text color="danger">{getApiErrorMessage(user.error)}</Text>
      ) : null}
      {user.data ? (
        <Card style={{ gap: 16 }}>
          <TextField label="Email" value={user.data.email} editable={false} />
          <Controller
            control={control}
            name="first_name"
            render={({ field }) => (
              <TextField
                label="First name"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={errors.first_name?.message}
              />
            )}
          />
          <Controller
            control={control}
            name="last_name"
            render={({ field }) => (
              <TextField
                label="Last name"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={errors.last_name?.message}
              />
            )}
          />
          <Controller
            control={control}
            name="phone"
            render={({ field }) => (
              <TextField
                label="Phone (optional)"
                keyboardType="phone-pad"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={errors.phone?.message}
              />
            )}
          />
          {errors.root?.message ? (
            <Text variant="caption" color="danger">
              {errors.root.message}
            </Text>
          ) : null}
          {saved && !isDirty ? (
            <SavedFeedback>Personal details saved.</SavedFeedback>
          ) : null}
          <Button disabled={!isDirty} loading={isSubmitting} onPress={submit}>
            Save personal details
          </Button>
        </Card>
      ) : null}
    </SettingsPage>
  );
}

type HairValues = Omit<HairProfile, "updated_at">;
const hairSchema = z.object({
  hair_texture: z.enum(hairTextures).or(z.literal("")),
  scalp_type: z.enum(scalpTypes).or(z.literal("")),
  concerns: z.string().trim().max(500),
  goals: z.string().trim().max(500),
  current_routine: z.string().trim().max(1000),
});
const textureLabels: Record<(typeof hairTextures)[number], string> = {
  STRAIGHT: "Straight",
  WAVY: "Wavy",
  CURLY: "Curly",
  COILY: "Coily",
  UNSURE: "Not sure",
  PREFER_NOT_TO_SAY: "Prefer not to say",
};
const scalpLabels: Record<(typeof scalpTypes)[number], string> = {
  BALANCED: "Balanced",
  DRY: "Dry",
  OILY: "Oily",
  SENSITIVE: "Sensitive",
  UNSURE: "Not sure",
};

function ChoiceField<T extends string>({
  label,
  value,
  options,
  labels,
  onChange,
}: {
  label: string;
  value: T | "";
  options: readonly T[];
  labels: Record<T, string>;
  onChange: (value: T) => void;
}) {
  const theme = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <Text variant="caption">{label}</Text>
      <View
        style={{
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        }}
      >
        {options.map((option) => (
          <Pressable
            key={option}
            accessibilityRole="radio"
            accessibilityState={{ selected: value === option }}
            onPress={() => onChange(option)}
            style={{
              cursor: "pointer",
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.sm,
              borderRadius: theme.radius.pill,
              borderWidth: 1,
              borderColor:
                value === option ? theme.colors.primary : theme.colors.border,
              backgroundColor:
                value === option
                  ? theme.colors.surfaceMuted
                  : theme.colors.surface,
            }}
          >
            <Text
              variant="caption"
              color={value === option ? "primary" : "default"}
            >
              {labels[option]}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function HairProfileScreen() {
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: ["settings", "hair-profile"],
    queryFn: getHairProfile,
  });
  const [saved, setSaved] = useState(false);
  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<HairValues>({
    defaultValues: {
      hair_texture: "",
      scalp_type: "",
      concerns: "",
      goals: "",
      current_routine: "",
    },
  });
  useEffect(() => {
    if (profile.data) {
      const { updated_at: _, ...values } = profile.data;
      reset(values);
    }
  }, [profile.data, reset]);
  const submit = handleSubmit(async (values) => {
    const parsed = hairSchema.safeParse(values);
    const report = (field: string, message: string) =>
      setError(field as keyof HairValues, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      const updated = await updateHairProfile(parsed.data);
      queryClient.setQueryData(["settings", "hair-profile"], updated);
      const { updated_at: _, ...savedValues } = updated;
      reset(savedValues);
      setSaved(true);
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });
  return (
    <SettingsPage title="Hair profile">
      <Text color="muted">
        A short reusable snapshot. The consultation intake will ask for deeper
        medical and hair-history details later.
      </Text>
      {profile.isLoading ? <LoadingIndicator /> : null}
      {profile.isError ? (
        <Text color="danger">{getApiErrorMessage(profile.error)}</Text>
      ) : null}
      {profile.data ? (
        <Card style={{ gap: 20 }}>
          <Controller
            control={control}
            name="hair_texture"
            render={({ field }) => (
              <ChoiceField
                label="Hair texture"
                value={field.value}
                options={hairTextures}
                labels={textureLabels}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="scalp_type"
            render={({ field }) => (
              <ChoiceField
                label="Scalp type"
                value={field.value}
                options={scalpTypes}
                labels={scalpLabels}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="concerns"
            render={({ field }) => (
              <TextField
                label="Main concerns (optional)"
                multiline
                value={field.value}
                onChangeText={field.onChange}
                error={errors.concerns?.message}
                style={{
                  minHeight: 96,
                  paddingVertical: 12,
                  textAlignVertical: "top",
                }}
              />
            )}
          />
          <Controller
            control={control}
            name="goals"
            render={({ field }) => (
              <TextField
                label="Hair goals (optional)"
                multiline
                value={field.value}
                onChangeText={field.onChange}
                error={errors.goals?.message}
                style={{
                  minHeight: 96,
                  paddingVertical: 12,
                  textAlignVertical: "top",
                }}
              />
            )}
          />
          <Controller
            control={control}
            name="current_routine"
            render={({ field }) => (
              <TextField
                label="Current routine (optional)"
                multiline
                value={field.value}
                onChangeText={field.onChange}
                error={errors.current_routine?.message}
                style={{
                  minHeight: 112,
                  paddingVertical: 12,
                  textAlignVertical: "top",
                }}
              />
            )}
          />
          {errors.root?.message ? (
            <Text variant="caption" color="danger">
              {errors.root.message}
            </Text>
          ) : null}
          {saved && !isDirty ? (
            <SavedFeedback>
              Hair profile saved. TK can review its consultation snapshot in the
              private app workspace.
            </SavedFeedback>
          ) : null}
          <Button disabled={!isDirty} loading={isSubmitting} onPress={submit}>
            Save hair profile
          </Button>
        </Card>
      ) : null}
    </SettingsPage>
  );
}

const timezoneSchema = z.object({
  timezone: z.string().trim().min(1, "Enter a timezone.").max(64),
});
type TimezoneValues = z.infer<typeof timezoneSchema>;
export function TimezoneScreen() {
  const queryClient = useQueryClient();
  const preferences = useQuery({
    queryKey: ["settings", "preferences"],
    queryFn: getNotificationPreferences,
  });
  const deviceTimezone =
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const [saved, setSaved] = useState(false);
  const {
    control,
    handleSubmit,
    reset,
    setValue,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<TimezoneValues>({ defaultValues: { timezone: "UTC" } });
  useEffect(() => {
    if (preferences.data) reset({ timezone: preferences.data.timezone });
  }, [preferences.data, reset]);
  const submit = handleSubmit(async (values) => {
    const parsed = timezoneSchema.safeParse(values);
    const report = (field: string, message: string) =>
      setError(field as keyof TimezoneValues, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      const updated = await updateNotificationPreferences(parsed.data);
      queryClient.setQueryData(["settings", "preferences"], updated);
      reset({ timezone: updated.timezone });
      setSaved(true);
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });
  return (
    <SettingsPage title="Time zone">
      <Text color="muted">
        Appointment times and reminders will use this time zone. Use an IANA
        name such as Europe/London.
      </Text>
      {preferences.isLoading ? <LoadingIndicator /> : null}
      {preferences.data ? (
        <Card style={{ gap: 16 }}>
          <Controller
            control={control}
            name="timezone"
            render={({ field }) => (
              <TextField
                label="Time zone"
                autoCapitalize="none"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={errors.timezone?.message}
              />
            )}
          />
          <Button
            variant="secondary"
            onPress={() =>
              setValue("timezone", deviceTimezone, { shouldDirty: true })
            }
          >
            Use device time zone: {deviceTimezone}
          </Button>
          {errors.root?.message ? (
            <Text variant="caption" color="danger">
              {errors.root.message}
            </Text>
          ) : null}
          {saved && !isDirty ? (
            <SavedFeedback>Time zone saved.</SavedFeedback>
          ) : null}
          <Button disabled={!isDirty} loading={isSubmitting} onPress={submit}>
            Save time zone
          </Button>
        </Card>
      ) : null}
    </SettingsPage>
  );
}

type PreferenceKey = Exclude<
  keyof NotificationPreferences,
  "timezone" | "updated_at"
>;
const notificationRows: {
  key: PreferenceKey;
  label: string;
  description: string;
}[] = [
  {
    key: "email_enabled",
    label: "Email",
    description: "Account and consultation updates by email.",
  },
  {
    key: "push_enabled",
    label: "Push notifications",
    description: "Allow notifications on registered devices.",
  },
  {
    key: "appointment_reminders",
    label: "Appointment reminders",
    description: "Reminders before a scheduled consultation.",
  },
  {
    key: "message_notifications",
    label: "New messages",
    description: "Alerts when TK replies to your consultation.",
  },
  {
    key: "coaching_updates",
    label: "Care plan & progress",
    description: "Updates when guidance or progress feedback is ready.",
  },
];
export function NotificationsScreen() {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const [deviceStatus, setDeviceStatus] = useState("");
  const [enabling, setEnabling] = useState(false);
  const preferences = useQuery({
    queryKey: ["settings", "preferences"],
    queryFn: getNotificationPreferences,
  });
  const mutation = useMutation({
    mutationFn: (input: Partial<NotificationPreferences>) =>
      updateNotificationPreferences(input),
    onMutate: async (input) => {
      await queryClient.cancelQueries({
        queryKey: ["settings", "preferences"],
      });
      const previous = queryClient.getQueryData<NotificationPreferences>([
        "settings",
        "preferences",
      ]);
      if (previous)
        queryClient.setQueryData(["settings", "preferences"], {
          ...previous,
          ...input,
        });
      return { previous };
    },
    onError: (_error, _input, context) => {
      if (context?.previous)
        queryClient.setQueryData(["settings", "preferences"], context.previous);
    },
    onSuccess: (data) =>
      queryClient.setQueryData(["settings", "preferences"], data),
  });
  const enableDevice = async () => {
    setEnabling(true);
    setDeviceStatus("");
    try {
      await enablePushOnThisDevice();
      setDeviceStatus("This device is ready for HairDoc TK alerts.");
    } catch (error) {
      setDeviceStatus(
        error instanceof Error
          ? error.message
          : "This device could not be enabled.",
      );
    } finally {
      setEnabling(false);
    }
  };
  const unavailable = pushUnavailableReason();
  return (
    <SettingsPage title="Notifications">
      <Text color="muted">
        Choose which care updates can alert you. Message previews stay private
        and never include the message text.
      </Text>
      {preferences.isLoading ? <LoadingIndicator /> : null}
      {preferences.isError ? (
        <Text color="danger">{getApiErrorMessage(preferences.error)}</Text>
      ) : null}
      {preferences.data ? (
        <>
          <SettingsSection title="How we contact you">
            {notificationRows.map((row, index) => (
              <View key={row.key}>
                <View
                  style={{
                    minHeight: 76,
                    paddingHorizontal: theme.spacing.md,
                    paddingVertical: theme.spacing.sm,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: theme.spacing.md,
                  }}
                >
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text variant="bodyStrong">{row.label}</Text>
                    <Text variant="caption" color="muted">
                      {row.description}
                    </Text>
                  </View>
                  <Switch
                    accessibilityLabel={row.label}
                    value={preferences.data[row.key]}
                    onValueChange={(value) =>
                      mutation.mutate({ [row.key]: value })
                    }
                    style={{ cursor: "pointer" }}
                    trackColor={{
                      false: theme.colors.border,
                      true: theme.colors.decorative,
                    }}
                    thumbColor={
                      preferences.data[row.key]
                        ? theme.colors.primary
                        : theme.colors.surface
                    }
                  />
                </View>
                {index < notificationRows.length - 1 ? <Divider /> : null}
              </View>
            ))}
          </SettingsSection>
          <Card style={{ gap: theme.spacing.sm }}>
            <Text variant="heading">This device</Text>
            <Text color="muted">
              Allow appointment, message, and care updates on this phone.
            </Text>
            {unavailable ? (
              <Text variant="caption" color="muted">
                {unavailable}
              </Text>
            ) : (
              <Button loading={enabling} onPress={() => void enableDevice()}>
                Enable on this device
              </Button>
            )}
            {deviceStatus ? (
              <Text
                variant="bodyStrong"
                color={deviceStatus.includes("ready") ? "primary" : "danger"}
              >
                {deviceStatus}
              </Text>
            ) : null}
          </Card>
        </>
      ) : null}
      {mutation.isError ? (
        <Text color="danger">{getApiErrorMessage(mutation.error)}</Text>
      ) : null}
    </SettingsPage>
  );
}

export function LegalDocumentScreen() {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{ type?: string }>();
  const type = legalTypes.includes(params.type as LegalType)
    ? (params.type as LegalType)
    : null;
  const document = useQuery({
    queryKey: ["settings", "legal", type],
    queryFn: () => getLegalDocument(type as LegalType),
    enabled: Boolean(type),
    retry: (count, error) =>
      !(error instanceof ApiError && error.status === 404) && count < 1,
  });
  const consents = useQuery({
    queryKey: ["settings", "consents"],
    queryFn: getConsents,
  });
  const consent = document.data
    ? consents.data?.find(
        (item) => item.document.public_id === document.data.public_id,
      )
    : undefined;
  const canConsent =
    type === "PHOTO_DATA_CONSENT" || type === "CONSULTATION_DISCLAIMER";
  const mutation = useMutation({
    mutationFn: (accepted: boolean) =>
      updateConsent(document.data!.public_id, accepted),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", "consents"] }),
  });
  return (
    <SettingsPage title={document.data?.type_label || "Privacy & legal"}>
      {document.isLoading ? <LoadingIndicator /> : null}
      {!type ||
      (document.error instanceof ApiError && document.error.status === 404) ? (
        <Card style={{ gap: theme.spacing.sm, alignItems: "center" }}>
          <Feather name="file-text" size={32} color={theme.colors.textMuted} />
          <Text variant="heading">
            This document isn’t available right now.
          </Text>
          <Text color="muted" style={{ textAlign: "center" }}>
            Please check again later.
          </Text>
        </Card>
      ) : null}
      {document.isError &&
      !(document.error instanceof ApiError && document.error.status === 404) ? (
        <Text color="danger">{getApiErrorMessage(document.error)}</Text>
      ) : null}
      {document.data ? (
        <>
          <Card style={{ gap: theme.spacing.md }}>
            <View style={{ gap: 4 }}>
              <Text variant="overline" color="accent">
                VERSION {document.data.version}
              </Text>
              <Text variant="title">{document.data.title}</Text>
              <Text variant="caption" color="muted">
                Published{" "}
                {new Date(document.data.published_at).toLocaleDateString()}
              </Text>
            </View>
            <Divider />
            {document.data.body ? <Text>{document.data.body}</Text> : null}
            {document.data.attachment_path ? (
              <Button
                variant="secondary"
                onPress={() =>
                  void Linking.openURL(
                    legalFileUrl(document.data!.attachment_path!),
                  )
                }
              >
                Open {document.data.attachment_name || "uploaded document"}
              </Button>
            ) : null}
          </Card>
          {canConsent ? (
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Your choice</Text>
              <Text color="muted">
                {consent?.accepted
                  ? "You accepted this exact version. You can withdraw that consent here."
                  : "Review the full document before recording your consent."}
              </Text>
              <Button
                loading={mutation.isPending}
                variant={consent?.accepted ? "secondary" : "primary"}
                onPress={() => mutation.mutate(!consent?.accepted)}
              >
                {consent?.accepted
                  ? "Withdraw consent"
                  : "I consent to this version"}
              </Button>
              {mutation.isError ? (
                <Text variant="caption" color="danger">
                  {getApiErrorMessage(mutation.error)}
                </Text>
              ) : null}
            </Card>
          ) : null}
        </>
      ) : null}
    </SettingsPage>
  );
}
