import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { Image, Pressable, View } from "react-native";

import {
  Button,
  Card,
  Divider,
  LoadingIndicator,
  Screen,
  Text,
} from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getApiErrorMessage } from "@/features/auth/errors";
import { createStaffPlan, getStaffCasePlans } from "@/services/api/coaching";
import {
  getStaffConsultation,
  getStaffConsultations,
  privatePhotoUrl,
} from "@/services/api/consultations";
import { useTheme } from "@/theme/ThemeProvider";

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

function displayValue(value: unknown) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return value == null || value === "" ? "Not answered" : String(value);
}

const hairLabels: Record<string, string> = {
  hair_texture: "Hair texture",
  scalp_type: "Scalp type",
  concerns: "Concerns",
  goals: "Goals",
  current_routine: "Current routine",
};

export function StaffConsultationListScreen() {
  const router = useRouter();
  const theme = useTheme();
  const cases = useQuery({
    queryKey: ["staff", "consultations"],
    queryFn: () => getStaffConsultations(),
  });
  return (
    <StaffGuard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Consultation workspace" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Ready for review.</Text>
          <Text color="muted">
            Only clients who completed their intake and submitted their private
            photos appear here.
          </Text>
        </View>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
          <Button
            style={{ flex: 1 }}
            variant="secondary"
            onPress={() => router.push("/staff/availability" as Href)}
          >
            Availability
          </Button>
          <Button
            style={{ flex: 1 }}
            variant="secondary"
            onPress={() => router.push("/staff/appointments" as Href)}
          >
            Appointments
          </Button>
        </View>
        <Button
          variant="secondary"
          onPress={() => router.push("/staff/progress" as Href)}
        >
          Progress check-ins
        </Button>
        {cases.isLoading ? <LoadingIndicator /> : null}
        {cases.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">The review queue could not load.</Text>
            <Text color="danger">{getApiErrorMessage(cases.error)}</Text>
            <Button onPress={() => cases.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {cases.isSuccess && !cases.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather name="inbox" size={32} color={theme.colors.textMuted} />
            <Text variant="heading">Nothing is waiting.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              Submitted consultation photo sets will appear here.
            </Text>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {cases.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.md }}>
              <View style={{ gap: theme.spacing.xs }}>
                <Text variant="overline" color="accent">
                  {item.photo_count}{" "}
                  {item.photo_count === 1 ? "PHOTO" : "PHOTOS"}
                </Text>
                <Text variant="heading">{item.client_name}</Text>
                <Text color="muted">{item.service_name}</Text>
                <Text variant="caption" color="muted">
                  Submitted{" "}
                  {new Date(item.photos_completed_at).toLocaleString()}
                </Text>
              </View>
              <Button
                variant="secondary"
                onPress={() =>
                  router.push(`/staff/consultations/${item.public_id}` as Href)
                }
              >
                Review consultation
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </StaffGuard>
  );
}

export function StaffConsultationDetailScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const item = useQuery({
    queryKey: ["staff", "consultations", caseId],
    queryFn: () => getStaffConsultation(caseId),
    enabled: Boolean(caseId),
  });
  const plans = useQuery({
    queryKey: ["staff", "coaching", "case", caseId],
    queryFn: () => getStaffCasePlans(caseId),
    enabled: Boolean(caseId),
  });
  const createPlan = useMutation({
    mutationFn: () => createStaffPlan(caseId),
    onSuccess: async (plan) => {
      await queryClient.invalidateQueries({
        queryKey: ["staff", "coaching", "case", caseId],
      });
      router.push(`/staff/plans/${plan.public_id}` as Href);
    },
  });
  if (!caseId) return <Redirect href={"/staff/consultations" as Href} />;
  return (
    <StaffGuard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Client review" />
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">This consultation could not load.</Text>
            <Text color="danger">{getApiErrorMessage(item.error)}</Text>
            <Button onPress={() => item.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {item.data ? (
          <>
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="overline" color="accent">
                {item.data.service_name}
              </Text>
              <Text variant="title">
                {`${item.data.client.first_name} ${item.data.client.last_name}`.trim() ||
                  item.data.client.email}
              </Text>
              <Text color="muted">
                {item.data.client.email}
                {item.data.client.phone ? ` · ${item.data.client.phone}` : ""}
              </Text>
              <Divider />
              <Text variant="caption" color="muted">
                Client timezone: {item.data.timezone_snapshot} · Submitted{" "}
                {new Date(item.data.photos_completed_at).toLocaleString()}
              </Text>
            </Card>
            <View style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Care plan</Text>
              {plans.isLoading ? <LoadingIndicator /> : null}
              {plans.isError ? (
                <Text color="danger">{getApiErrorMessage(plans.error)}</Text>
              ) : null}
              {plans.data?.map((plan) => (
                <Card key={plan.public_id} style={{ gap: theme.spacing.sm }}>
                  <Text
                    variant="overline"
                    color={plan.status === "DRAFT" ? "accent" : "primary"}
                  >
                    {plan.status} · VERSION {plan.version}
                  </Text>
                  <Text variant="bodyStrong">{plan.title}</Text>
                  <Button
                    variant="secondary"
                    onPress={() =>
                      router.push(`/staff/plans/${plan.public_id}` as Href)
                    }
                  >
                    {plan.status === "DRAFT" ? "Continue draft" : "View plan"}
                  </Button>
                </Card>
              ))}
              {!plans.isLoading &&
              !plans.data?.some((plan) => plan.status === "DRAFT") ? (
                <Button
                  loading={createPlan.isPending}
                  onPress={() => createPlan.mutate()}
                >
                  {plans.data?.length
                    ? "Create updated version"
                    : "Create care plan"}
                </Button>
              ) : null}
              {createPlan.isError ? (
                <Text color="danger">
                  {getApiErrorMessage(createPlan.error)}
                </Text>
              ) : null}
            </View>
            <View style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Hair profile at intake</Text>
              <Card style={{ gap: theme.spacing.md }}>
                {Object.entries(item.data.hair_profile_snapshot).length ? (
                  Object.entries(item.data.hair_profile_snapshot).map(
                    ([key, value]) => (
                      <View key={key} style={{ gap: 2 }}>
                        <Text variant="caption" color="muted">
                          {hairLabels[key] || key}
                        </Text>
                        <Text variant="bodyStrong">{displayValue(value)}</Text>
                      </View>
                    ),
                  )
                ) : (
                  <Text color="muted">
                    No reusable hair-profile details were provided.
                  </Text>
                )}
              </Card>
            </View>
            <View style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Private intake</Text>
              {item.data.answers.map((answer, index) => (
                <Card
                  key={`${answer.question}-${index}`}
                  style={{ gap: theme.spacing.xs }}
                >
                  <Text variant="overline" color="accent">
                    {answer.section}
                  </Text>
                  <Text variant="caption" color="muted">
                    {answer.question}
                  </Text>
                  <Text variant="bodyStrong">
                    {displayValue(answer.display_value)}
                  </Text>
                </Card>
              ))}
            </View>
            <View style={{ gap: theme.spacing.sm }}>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <Text variant="heading">Consultation photos</Text>
                <Text variant="caption" color="muted">
                  {item.data.photos.length}
                </Text>
              </View>
              {!item.data.photo_consent_active ? (
                <Card style={{ gap: theme.spacing.sm }}>
                  <Text variant="bodyStrong" color="danger">
                    Photo access paused
                  </Text>
                  <Text color="muted">
                    The client withdrew photo consent. Images cannot be opened
                    in the staff workspace.
                  </Text>
                </Card>
              ) : null}
              {item.data.photos.map((photo) => {
                const uri = privatePhotoUrl(photo.content_path);
                return (
                  <Card
                    key={photo.public_id}
                    style={{ padding: theme.spacing.sm, gap: theme.spacing.sm }}
                  >
                    {uri ? (
                      <Image
                        source={{ uri }}
                        accessibilityLabel={`${photo.category_label} client photo`}
                        resizeMode="contain"
                        style={{
                          width: "100%",
                          aspectRatio: 4 / 3,
                          borderRadius: theme.radius.md,
                          backgroundColor: theme.colors.surfaceMuted,
                        }}
                      />
                    ) : null}
                    <Text variant="bodyStrong">{photo.category_label}</Text>
                  </Card>
                );
              })}
            </View>
          </>
        ) : null}
      </Screen>
    </StaffGuard>
  );
}
