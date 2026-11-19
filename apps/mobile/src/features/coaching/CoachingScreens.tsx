import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Linking, Pressable, View } from "react-native";

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
  CoachingCategory,
  CoachingPlanInput,
  getPlan,
  getPlans,
  getStaffPlan,
  publishStaffPlan,
  updateStaffPlan,
} from "@/services/api/coaching";
import { createProgress } from "@/services/api/progress";
import { useTheme } from "@/theme/ThemeProvider";

function Guard({
  staff = false,
  children,
}: {
  staff?: boolean;
  children: React.ReactNode;
}) {
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  if (staff && !user?.is_staff) return <Redirect href="/explore" />;
  if (!staff && user?.is_staff) return <Redirect href="/explore" />;
  return children;
}

function Header({ title, staff = false }: { title: string; staff?: boolean }) {
  const router = useRouter();
  const theme = useTheme();
  return (
    <View style={{ minHeight: 48, justifyContent: "center", paddingLeft: 54 }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go back"
        onPress={() =>
          router.canGoBack() ? router.back() : router.replace("/explore")
        }
        style={({ pressed }) => ({
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
        {staff ? "TK WORKSPACE" : "YOUR GUIDANCE"}
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function dateLabel(value: string | null) {
  return value
    ? new Date(value).toLocaleDateString(undefined, {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "Draft";
}

function LinkifiedText({ value }: { value: string }) {
  const theme = useTheme();
  return (
    <Text>
      {value.split(/(https?:\/\/[^\s]+)/gi).map((part, index) => {
        if (!/^https?:\/\//i.test(part)) return part;
        const match = part.match(/^(.*?)([.,!?;:]*)$/);
        const url = match?.[1] || part;
        const suffix = match?.[2] || "";
        return (
          <Text key={`${url}-${index}`}>
            <Text
              accessibilityRole="link"
              onPress={() => void Linking.openURL(url)}
              style={{
                color: theme.colors.primary,
                textDecorationLine: "underline",
              }}
            >
              {url}
            </Text>
            {suffix}
          </Text>
        );
      })}
    </Text>
  );
}

export function ClientPlanListScreen() {
  const theme = useTheme();
  const router = useRouter();
  const plans = useQuery({
    queryKey: ["coaching", "plans"],
    queryFn: getPlans,
  });
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Care plans" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Guidance you can return to.</Text>
          <Text color="muted">
            Published recommendations from TK stay organised by consultation and
            version.
          </Text>
        </View>
        {plans.isLoading ? <LoadingIndicator /> : null}
        {plans.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Your plans could not load.</Text>
            <Text color="danger">{getApiErrorMessage(plans.error)}</Text>
            <Button onPress={() => plans.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {plans.isSuccess && !plans.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather
              name="clipboard"
              size={30}
              color={theme.colors.textMuted}
            />
            <Text variant="heading">No care plan yet.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              After TK publishes guidance for your consultation, it will appear
              here.
            </Text>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {plans.data?.map((plan) => (
            <Card key={plan.public_id} style={{ gap: theme.spacing.sm }}>
              <Text variant="overline" color="accent">
                VERSION {plan.version} · {dateLabel(plan.published_at)}
              </Text>
              <Text variant="heading">{plan.title}</Text>
              <Text color="muted">{plan.service_name}</Text>
              {plan.summary ? <Text>{plan.summary}</Text> : null}
              <Button
                variant="secondary"
                onPress={() => router.push(`/plans/${plan.public_id}` as Href)}
              >
                Open care plan
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </Guard>
  );
}

export function ClientPlanDetailScreen() {
  const { planId } = useLocalSearchParams<{ planId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const plan = useQuery({
    queryKey: ["coaching", "plan", planId],
    queryFn: () => getPlan(planId),
    enabled: Boolean(planId),
  });
  const startCheckIn = useMutation({
    mutationFn: () => createProgress(plan.data!.case_public_id),
    onSuccess: (checkIn) =>
      router.push(`/progress/${checkIn.public_id}` as Href),
  });
  if (!planId) return <Redirect href={"/plans" as Href} />;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Care plan" />
        {plan.isLoading ? <LoadingIndicator /> : null}
        {plan.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">This plan could not load.</Text>
            <Text color="danger">{getApiErrorMessage(plan.error)}</Text>
            <Button onPress={() => plan.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {plan.data ? (
          <>
            <Card style={{ gap: theme.spacing.sm }}>
              <Text variant="overline" color="accent">
                {plan.data.service_name} · VERSION {plan.data.version}
              </Text>
              <Text variant="display">{plan.data.title}</Text>
              {plan.data.summary ? (
                <Text color="muted">{plan.data.summary}</Text>
              ) : null}
              <Text variant="caption" color="muted">
                Published {dateLabel(plan.data.published_at)}
              </Text>
            </Card>
            <View style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Your plan</Text>
              {plan.data.sections.map((section) => (
                <Card key={section.public_id} style={{ gap: theme.spacing.sm }}>
                  <Text variant="heading">{section.title}</Text>
                  <LinkifiedText value={section.body} />
                </Card>
              ))}
            </View>
            {plan.data.recommendations.length ? (
              <View style={{ gap: theme.spacing.md }}>
                <Text variant="heading">Recommendations</Text>
                {plan.data.recommendations.map((item) => (
                  <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
                    <Text variant="overline" color="accent">
                      {item.category_label}
                    </Text>
                    <Text variant="heading">{item.title}</Text>
                    <LinkifiedText value={item.guidance} />
                    {item.external_url ? (
                      <Button
                        variant="secondary"
                        onPress={() => Linking.openURL(item.external_url)}
                      >
                        Open resource
                      </Button>
                    ) : null}
                  </Card>
                ))}
              </View>
            ) : null}
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Ready to check in?</Text>
              <Text color="muted">
                Record what changed, add comparable photos, and send it
                privately to TK.
              </Text>
              {startCheckIn.isError ? (
                <Text color="danger">
                  {getApiErrorMessage(startCheckIn.error)}
                </Text>
              ) : null}
              <Button
                loading={startCheckIn.isPending}
                onPress={() => startCheckIn.mutate()}
              >
                Start progress check-in
              </Button>
            </Card>
          </>
        ) : null}
      </Screen>
    </Guard>
  );
}

type SectionDraft = { key: string; title: string; body: string };
type RecommendationDraft = {
  key: string;
  category: CoachingCategory;
  title: string;
  guidance: string;
  external_url: string;
};
const categories: { value: CoachingCategory; label: string }[] = [
  { value: "ROUTINE", label: "Routine" },
  { value: "PRODUCT", label: "Product" },
  { value: "LIFESTYLE", label: "Lifestyle" },
  { value: "FOLLOW_UP", label: "Follow-up" },
  { value: "RESOURCE", label: "Resource" },
];

export function StaffPlanEditorScreen() {
  const { planId } = useLocalSearchParams<{ planId: string }>();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const plan = useQuery({
    queryKey: ["staff", "coaching", "plan", planId],
    queryFn: () => getStaffPlan(planId),
    enabled: Boolean(planId),
  });
  const [loadedId, setLoadedId] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [sections, setSections] = useState<SectionDraft[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationDraft[]>(
    [],
  );
  const [saved, setSaved] = useState(false);
  const [publishedNow, setPublishedNow] = useState(false);
  useEffect(() => {
    if (!plan.data || loadedId === plan.data.public_id) return;
    // Query data intentionally seeds this editable draft exactly once per plan.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadedId(plan.data.public_id);
    setTitle(plan.data.title);
    setSummary(plan.data.summary);
    setSections(
      plan.data.sections.length
        ? plan.data.sections.map((item) => ({
            key: item.public_id,
            title: item.title,
            body: item.body,
          }))
        : [{ key: "initial", title: "", body: "" }],
    );
    setRecommendations(
      plan.data.recommendations.map((item) => ({
        key: item.public_id,
        category: item.category,
        title: item.title,
        guidance: item.guidance,
        external_url: item.external_url,
      })),
    );
  }, [loadedId, plan.data]);
  const input = (): CoachingPlanInput => ({
    title: title.trim(),
    summary: summary.trim(),
    sections: sections.map(({ title: sectionTitle, body }) => ({
      title: sectionTitle.trim(),
      body: body.trim(),
    })),
    recommendations: recommendations.map(
      ({ category, title: recommendationTitle, guidance, external_url }) => ({
        category,
        title: recommendationTitle.trim(),
        guidance: guidance.trim(),
        external_url: external_url.trim(),
      }),
    ),
  });
  const validation = !title.trim()
    ? "Add a plan title."
    : sections.some((item) => !item.title.trim() || !item.body.trim())
      ? "Complete every guidance section."
      : recommendations.some(
            (item) => !item.title.trim() || !item.guidance.trim(),
          )
        ? "Complete every recommendation."
        : "";
  const save = useMutation({
    mutationFn: () => updateStaffPlan(planId, input()),
    onSuccess: async (data) => {
      queryClient.setQueryData(["staff", "coaching", "plan", planId], data);
      setSaved(true);
      await queryClient.invalidateQueries({
        queryKey: ["staff", "coaching", "case", data.case_public_id],
      });
    },
  });
  const publish = useMutation({
    mutationFn: async () => {
      await updateStaffPlan(planId, input());
      return publishStaffPlan(planId);
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(["staff", "coaching", "plan", planId], data);
      setPublishedNow(true);
      await queryClient.invalidateQueries({
        queryKey: ["staff", "coaching", "case", data.case_public_id],
      });
      await queryClient.invalidateQueries({ queryKey: ["coaching", "plans"] });
    },
  });
  if (!planId) return <Redirect href="/staff/consultations" />;
  const editable = plan.data?.status === "DRAFT";
  return (
    <Guard staff>
      <Screen keyboardAware contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Care plan" staff />
        {plan.isLoading ? <LoadingIndicator /> : null}
        {plan.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">This care plan could not load.</Text>
            <Text color="danger">{getApiErrorMessage(plan.error)}</Text>
            <Button onPress={() => plan.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {plan.data ? (
          <>
            <Card style={{ gap: theme.spacing.xs }}>
              <Text variant="overline" color={editable ? "accent" : "primary"}>
                {editable ? "DRAFT" : "PUBLISHED"} · VERSION {plan.data.version}
              </Text>
              <Text variant="heading">{plan.data.client_name}</Text>
              <Text color="muted">{plan.data.service_name}</Text>
              {!editable ? (
                <Text variant="caption" color="muted">
                  Published plans are locked. Create another version from the
                  client review when guidance changes.
                </Text>
              ) : null}
            </Card>
            {!editable ? (
              <Card
                style={{
                  gap: theme.spacing.sm,
                  borderColor: theme.colors.primary,
                  backgroundColor: theme.colors.primaryMuted,
                }}
              >
                <View
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    gap: theme.spacing.sm,
                  }}
                >
                  <Feather
                    name="check-circle"
                    size={theme.iconSize.md}
                    color={theme.colors.primary}
                  />
                  <Text variant="heading" color="primary">
                    {publishedNow ? "Published successfully" : "Published to client"}
                  </Text>
                </View>
                <Text>
                  {plan.data.client_name} can now open this plan. An in-app
                  notification links directly to it, and the published version
                  is locked against accidental edits.
                </Text>
              </Card>
            ) : null}
            <TextField
              label="Plan title"
              value={title}
              editable={editable}
              maxLength={180}
              onChangeText={(value) => {
                setSaved(false);
                setTitle(value);
              }}
            />
            <TextField
              label="Short summary (optional)"
              value={summary}
              editable={editable}
              multiline
              maxLength={500}
              onChangeText={(value) => {
                setSaved(false);
                setSummary(value);
              }}
            />
            <View style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Guidance sections</Text>
              {sections.map((section, index) => (
                <Card key={section.key} style={{ gap: theme.spacing.md }}>
                  <Text variant="overline" color="accent">
                    SECTION {index + 1}
                  </Text>
                  {editable ? (
                    <>
                      <TextField
                        label="Heading"
                        value={section.title}
                        maxLength={160}
                        onChangeText={(value) => {
                          setSaved(false);
                          setSections((items) =>
                            items.map((item) =>
                              item.key === section.key
                                ? { ...item, title: value }
                                : item,
                            ),
                          );
                        }}
                      />
                      <TextField
                        label="Guidance"
                        value={section.body}
                        multiline
                        maxLength={4000}
                        style={{ minHeight: 130, textAlignVertical: "top" }}
                        onChangeText={(value) => {
                          setSaved(false);
                          setSections((items) =>
                            items.map((item) =>
                              item.key === section.key
                                ? { ...item, body: value }
                                : item,
                            ),
                          );
                        }}
                      />
                    </>
                  ) : (
                    <View style={{ gap: theme.spacing.sm }}>
                      <Text variant="heading">{section.title}</Text>
                      <LinkifiedText value={section.body} />
                    </View>
                  )}
                  {editable && sections.length > 1 ? (
                    <Button
                      variant="ghost"
                      onPress={() =>
                        setSections((items) =>
                          items.filter((item) => item.key !== section.key),
                        )
                      }
                    >
                      Remove section
                    </Button>
                  ) : null}
                </Card>
              ))}
              {editable ? (
                <Button
                  variant="secondary"
                  onPress={() =>
                    setSections((items) => [
                      ...items,
                      { key: `section-${Date.now()}`, title: "", body: "" },
                    ])
                  }
                >
                  Add guidance section
                </Button>
              ) : null}
            </View>
            {editable || recommendations.length ? <Divider /> : null}
            {editable || recommendations.length ? (
              <View style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Recommendations</Text>
              {recommendations.map((item, index) => (
                <Card key={item.key} style={{ gap: theme.spacing.md }}>
                  <Text variant="overline" color="accent">
                    RECOMMENDATION {index + 1}
                  </Text>
                  <View
                    style={{
                      flexDirection: "row",
                      flexWrap: "wrap",
                      gap: theme.spacing.xs,
                    }}
                  >
                    {categories.map((category) => (
                      <Pressable
                        key={category.value}
                        disabled={!editable}
                        onPress={() => {
                          setSaved(false);
                          setRecommendations((items) =>
                            items.map((current) =>
                              current.key === item.key
                                ? { ...current, category: category.value }
                                : current,
                            ),
                          );
                        }}
                        style={{
                          paddingHorizontal: theme.spacing.sm,
                          paddingVertical: theme.spacing.xs,
                          borderRadius: theme.radius.pill,
                          backgroundColor:
                            item.category === category.value
                              ? theme.colors.primaryMuted
                              : theme.colors.surfaceMuted,
                        }}
                      >
                        <Text
                          variant="caption"
                          color={
                            item.category === category.value
                              ? "primary"
                              : "muted"
                          }
                        >
                          {category.label}
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                  <TextField
                    label="Title"
                    value={item.title}
                    editable={editable}
                    maxLength={160}
                    onChangeText={(value) => {
                      setSaved(false);
                      setRecommendations((items) =>
                        items.map((current) =>
                          current.key === item.key
                            ? { ...current, title: value }
                            : current,
                        ),
                      );
                    }}
                  />
                  <TextField
                    label="Instructions"
                    value={item.guidance}
                    editable={editable}
                    multiline
                    maxLength={2000}
                    style={{ minHeight: 100, textAlignVertical: "top" }}
                    onChangeText={(value) => {
                      setSaved(false);
                      setRecommendations((items) =>
                        items.map((current) =>
                          current.key === item.key
                            ? { ...current, guidance: value }
                            : current,
                        ),
                      );
                    }}
                  />
                  <TextField
                    label="Optional web link"
                    value={item.external_url}
                    editable={editable}
                    autoCapitalize="none"
                    keyboardType="url"
                    onChangeText={(value) => {
                      setSaved(false);
                      setRecommendations((items) =>
                        items.map((current) =>
                          current.key === item.key
                            ? { ...current, external_url: value }
                            : current,
                        ),
                      );
                    }}
                  />
                  {editable ? (
                    <Button
                      variant="ghost"
                      onPress={() => {
                        setSaved(false);
                        setRecommendations((items) =>
                          items.filter((current) => current.key !== item.key),
                        );
                      }}
                    >
                      Remove recommendation
                    </Button>
                  ) : null}
                </Card>
              ))}
              {editable ? (
                <Button
                  variant="secondary"
                  onPress={() => {
                    setSaved(false);
                    setRecommendations((items) => [
                      ...items,
                      {
                        key: `recommendation-${Date.now()}`,
                        category: "ROUTINE",
                        title: "",
                        guidance: "",
                        external_url: "",
                      },
                    ]);
                  }}
                >
                  Add recommendation
                </Button>
              ) : null}
              </View>
            ) : null}
            {editable ? (
              <View style={{ gap: theme.spacing.sm }}>
                {validation ? <Text color="danger">{validation}</Text> : null}
                {saved ? (
                  <Text variant="bodyStrong" color="primary">
                    Draft saved.
                  </Text>
                ) : null}
                {save.isError || publish.isError ? (
                  <Text color="danger">
                    {getApiErrorMessage(save.error || publish.error)}
                  </Text>
                ) : null}
                <Button
                  variant="secondary"
                  disabled={Boolean(validation)}
                  loading={save.isPending}
                  onPress={() => save.mutate()}
                >
                  Save draft
                </Button>
                <Button
                  disabled={Boolean(validation)}
                  loading={publish.isPending}
                  onPress={() => publish.mutate()}
                >
                  Publish to client
                </Button>
                <Text
                  variant="caption"
                  color="muted"
                  style={{ textAlign: "center" }}
                >
                  Publishing locks this version and makes it visible to this
                  client.
                </Text>
              </View>
            ) : null}
          </>
        ) : null}
      </Screen>
    </Guard>
  );
}
