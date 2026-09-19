import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { PropsWithChildren, useMemo, useState } from "react";
import { Control, Controller, useForm, useWatch } from "react-hook-form";
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
  answeredSectionPayload,
  lockedIntakePath,
  normalizeIntakeAnswers,
} from "@/features/consultations/intakeState";
import { ApiError } from "@/services/api/client";
import {
  completeIntake,
  ConsultationService,
  getAnswers,
  getConsultation,
  getConsultationService,
  getConsultationServices,
  getConsultations,
  getQuestionnaire,
  IntakeAnswers,
  IntakeQuestion,
  saveAnswers,
  startConsultation,
} from "@/services/api/consultations";
import { useTheme } from "@/theme/ThemeProvider";

type AnswerValues = Record<string, unknown>;

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

function intakeError(error: unknown) {
  if (
    error instanceof ApiError &&
    error.details &&
    typeof error.details === "object"
  ) {
    const root = error.details as Record<string, unknown>;
    const details =
      root.answers && typeof root.answers === "object"
        ? (root.answers as Record<string, unknown>)
        : root;
    for (const value of Object.values(details)) {
      if (Array.isArray(value) && value.length) return String(value[0]);
    }
  }
  return getApiErrorMessage(error);
}

function PageHeader({
  title,
  eyebrow,
  backHref,
}: {
  title: string;
  eyebrow?: string;
  backHref?: Href;
}) {
  const router = useRouter();
  const theme = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <View
        style={{ minHeight: 46, justifyContent: "center", paddingLeft: 54 }}
      >
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
        {eyebrow ? (
          <Text variant="overline" color="accent">
            {eyebrow}
          </Text>
        ) : null}
        <Text variant="title">{title}</Text>
      </View>
    </View>
  );
}

function ConsultationPage({
  title,
  eyebrow,
  backHref,
  children,
}: PropsWithChildren<{ title: string; eyebrow?: string; backHref?: Href }>) {
  const theme = useTheme();
  return (
    <Screen contentStyle={{ gap: theme.spacing.xl }}>
      <PageHeader title={title} eyebrow={eyebrow} backHref={backHref} />
      {children}
    </Screen>
  );
}

function AuthGuard({ children }: PropsWithChildren) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  return children;
}

function ServiceCard({
  service,
  onPress,
}: {
  service: ConsultationService;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={{ cursor: "pointer" }}
    >
      {({ pressed }) => (
        <Card style={{ gap: theme.spacing.md, opacity: pressed ? 0.88 : 1 }}>
          <View
            style={{
              flexDirection: "row",
              gap: theme.spacing.md,
              alignItems: "flex-start",
            }}
          >
            <View style={{ flex: 1, gap: theme.spacing.xs }}>
              <Text variant="heading">{service.name}</Text>
              <Text color="muted">{service.short_description}</Text>
            </View>
            <Feather
              name="arrow-up-right"
              size={theme.iconSize.md}
              color={theme.colors.primary}
            />
          </View>
          <Divider />
          <View
            style={{ flexDirection: "row", justifyContent: "space-between" }}
          >
            <Text variant="caption" color="muted">
              {service.duration_minutes} minutes
            </Text>
            <Text variant="bodyStrong" color="primary">
              {money(service.price_amount, service.currency)}
            </Text>
          </View>
        </Card>
      )}
    </Pressable>
  );
}

export function ConsultationCatalogueScreen() {
  const router = useRouter();
  const theme = useTheme();
  const auth = useAuthStore((state) => state.status);
  const services = useQuery({
    queryKey: ["consultations", "services"],
    queryFn: getConsultationServices,
    enabled: auth === "authenticated",
  });
  const cases = useQuery({
    queryKey: ["consultations", "cases"],
    queryFn: getConsultations,
    enabled: auth === "authenticated",
  });
  return (
    <AuthGuard>
      <ConsultationPage
        title="Consultations"
        eyebrow="PRIVATE GUIDANCE"
        backHref="/explore"
      >
        <View style={{ gap: theme.spacing.sm }}>
          <Text variant="display">Start with your story.</Text>
          <Text color="muted">
            Choose a consultation, then complete a private intake at your own
            pace. Your progress is saved.
          </Text>
        </View>
        {auth === "authenticated" && cases.data?.length ? (
          <View style={{ gap: theme.spacing.sm }}>
            <Text variant="heading">Your consultations</Text>
            {cases.data.map((item) => (
              <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
                <Text variant="bodyStrong">{item.service_name}</Text>
                <Text variant="caption" color="muted">
                  {item.status === "DRAFT"
                    ? "Intake in progress"
                    : item.status === "INTAKE_COMPLETE"
                      ? "Private photos are the next step"
                      : item.status === "PHOTOS_COMPLETE"
                        ? "Intake and photos submitted"
                        : "Cancelled"}
                </Text>
                {item.status !== "CANCELLED" ? (
                  <Button
                    variant="secondary"
                    onPress={() =>
                      router.push(
                        `/${item.status === "DRAFT" ? "consult/intake" : item.status === "INTAKE_COMPLETE" ? "consult/photos" : "consult/complete"}/${item.public_id}` as Href,
                      )
                    }
                  >
                    {item.status === "DRAFT"
                      ? "Resume intake"
                      : item.status === "INTAKE_COMPLETE"
                        ? "Add private photos"
                        : "View status"}
                  </Button>
                ) : null}
              </Card>
            ))}
          </View>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          <Text variant="heading">Choose a service</Text>
          {services.isLoading ? <LoadingIndicator /> : null}
          {services.isError ? (
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Consultations could not load.</Text>
              <Text color="muted">
                Check the local backend connection, then try again.
              </Text>
              <Button onPress={() => services.refetch()}>Try again</Button>
            </Card>
          ) : null}
          {services.data?.map((service) => (
            <ServiceCard
              key={service.public_id}
              service={service}
              onPress={() =>
                router.push({
                  pathname: "/consult/[serviceId]",
                  params: { serviceId: service.public_id },
                })
              }
            />
          ))}
          {services.isSuccess && !services.data.length ? (
            <Card style={{ gap: theme.spacing.sm, alignItems: "center" }}>
              <Feather
                name="calendar"
                size={32}
                color={theme.colors.textMuted}
              />
              <Text variant="heading">
                No consultations are available right now.
              </Text>
              <Text color="muted" style={{ textAlign: "center" }}>
                Please check again later or contact TK for availability.
              </Text>
            </Card>
          ) : null}
        </View>
      </ConsultationPage>
    </AuthGuard>
  );
}

export function ConsultationServiceScreen() {
  const { serviceId } = useLocalSearchParams<{ serviceId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const auth = useAuthStore((state) => state.status);
  const service = useQuery({
    queryKey: ["consultations", "service", serviceId],
    queryFn: () => getConsultationService(serviceId),
    enabled: Boolean(serviceId) && auth === "authenticated",
  });
  const mutation = useMutation({
    mutationFn: () =>
      startConsultation(
        serviceId,
        Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      ),
    onSuccess: (item) =>
      router.replace({
        pathname: "/consult/intake/[caseId]",
        params: { caseId: item.public_id },
      }),
  });
  const begin = () => mutation.mutate();
  return (
    <AuthGuard>
      <ConsultationPage
        title={service.data?.name || "Consultation"}
        eyebrow="SERVICE DETAILS"
      >
        {service.isLoading ? <LoadingIndicator /> : null}
        {service.isError ? (
          <Text color="danger">{getApiErrorMessage(service.error)}</Text>
        ) : null}
        {service.data ? (
          <>
            <Card style={{ gap: theme.spacing.lg }}>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <View>
                  <Text variant="overline" color="accent">
                    DURATION
                  </Text>
                  <Text variant="heading">
                    {service.data.duration_minutes} minutes
                  </Text>
                </View>
                <View style={{ alignItems: "flex-end" }}>
                  <Text variant="overline" color="accent">
                    PRICE
                  </Text>
                  <Text variant="heading">
                    {money(service.data.price_amount, service.data.currency)}
                  </Text>
                </View>
              </View>
              <Divider />
              <Text>{service.data.description}</Text>
            </Card>
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Before you begin</Text>
              <Text color="muted">
                Your answers save as a private draft. The service, price,
                hair-profile snapshot, and questionnaire version are locked when
                you start.
              </Text>
              <Button loading={mutation.isPending} onPress={begin}>
                {auth === "authenticated"
                  ? "Start private intake"
                  : "Sign in to start"}
              </Button>
              {mutation.isError ? (
                <Text variant="caption" color="danger">
                  {intakeError(mutation.error)}
                </Text>
              ) : null}
            </Card>
          </>
        ) : null}
      </ConsultationPage>
    </AuthGuard>
  );
}

function visible(question: IntakeQuestion, values: AnswerValues) {
  if (!question.show_if_question_key) return true;
  const current = values[question.show_if_question_key];
  const expected = question.show_if_value.toLowerCase();
  return Array.isArray(current)
    ? current.some((item) => String(item).toLowerCase() === expected)
    : String(current).toLowerCase() === expected;
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
      style={({ pressed }) => ({
        cursor: "pointer",
        minHeight: 48,
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.sm,
        padding: theme.spacing.md,
        borderWidth: 1,
        borderColor: selected ? theme.colors.primary : theme.colors.border,
        borderRadius: theme.radius.md,
        backgroundColor: selected
          ? theme.colors.surfaceMuted
          : theme.colors.surface,
        opacity: pressed ? 0.85 : 1,
      })}
    >
      <Feather
        name={selected ? "check-circle" : "circle"}
        size={theme.iconSize.sm}
        color={selected ? theme.colors.primary : theme.colors.textMuted}
      />
      <Text variant="bodyStrong">{label}</Text>
    </Pressable>
  );
}

function QuestionField({
  question,
  control,
}: {
  question: IntakeQuestion;
  control: Control<AnswerValues>;
}) {
  const theme = useTheme();
  return (
    <Controller
      control={control}
      name={question.key}
      render={({ field }) => (
        <View style={{ gap: theme.spacing.sm }}>
          <View style={{ gap: 2 }}>
            <Text variant="bodyStrong">
              {question.prompt}
              {question.required ? " *" : ""}
            </Text>
            {question.help_text ? (
              <Text variant="caption" color="muted">
                {question.help_text}
              </Text>
            ) : null}
          </View>
          {question.type === "SHORT_TEXT" ||
          question.type === "LONG_TEXT" ||
          question.type === "DATE" ? (
            <TextField
              label={question.type === "DATE" ? "YYYY-MM-DD" : "Your answer"}
              value={typeof field.value === "string" ? field.value : ""}
              placeholder={question.placeholder || undefined}
              maxLength={question.max_length || undefined}
              onBlur={field.onBlur}
              onChangeText={field.onChange}
              multiline={question.type === "LONG_TEXT"}
              style={
                question.type === "LONG_TEXT"
                  ? {
                      minHeight: 120,
                      paddingVertical: 12,
                      textAlignVertical: "top",
                    }
                  : undefined
              }
            />
          ) : null}
          {question.type === "BOOLEAN" ? (
            <View style={{ gap: theme.spacing.xs }}>
              {[
                [true, "Yes"],
                [false, "No"],
              ].map(([value, label]) => (
                <Choice
                  key={String(value)}
                  label={String(label)}
                  selected={field.value === value}
                  onPress={() => field.onChange(value)}
                />
              ))}
            </View>
          ) : null}
          {question.type === "SINGLE_CHOICE" ? (
            <View style={{ gap: theme.spacing.xs }}>
              {question.options.map((option) => (
                <Choice
                  key={option.value}
                  label={option.label}
                  selected={field.value === option.value}
                  onPress={() => field.onChange(option.value)}
                />
              ))}
            </View>
          ) : null}
          {question.type === "MULTI_CHOICE" ? (
            <View style={{ gap: theme.spacing.xs }}>
              {question.options.map((option) => {
                const selected =
                  Array.isArray(field.value) &&
                  field.value.includes(option.value);
                return (
                  <Choice
                    key={option.value}
                    label={option.label}
                    selected={selected}
                    onPress={() => {
                      const values = Array.isArray(field.value)
                        ? field.value
                        : [];
                      field.onChange(
                        selected
                          ? values.filter((item) => item !== option.value)
                          : [...values, option.value],
                      );
                    }}
                  />
                );
              })}
            </View>
          ) : null}
        </View>
      )}
    />
  );
}

export function ConsultationIntakeScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const [sectionIndex, setSectionIndex] = useState(0);
  const [saved, setSaved] = useState(false);
  const questionnaire = useQuery({
    queryKey: ["consultations", caseId, "questionnaire"],
    queryFn: () => getQuestionnaire(caseId),
    enabled: Boolean(caseId),
  });
  const answers = useQuery({
    queryKey: ["consultations", caseId, "answers"],
    queryFn: () => getAnswers(caseId),
    enabled: Boolean(caseId),
  });
  const hydratedAnswers = useMemo(
    () =>
      normalizeIntakeAnswers(
        questionnaire.data?.questions ?? [],
        answers.data?.answers ?? {},
      ),
    [answers.data?.answers, questionnaire.data?.questions],
  );
  const {
    control,
    handleSubmit,
    reset,
  } = useForm<AnswerValues>({
    defaultValues: {},
    values: hydratedAnswers,
    resetOptions: { keepDirtyValues: true },
  });
  const values = useWatch({ control }) as AnswerValues;
  const sections = useMemo(
    () =>
      Array.from(
        new Set(
          questionnaire.data?.questions.map((item) => item.section) || [],
        ),
      ),
    [questionnaire.data],
  );
  const section = sections[sectionIndex];
  const questions =
    questionnaire.data?.questions.filter(
      (item) => item.section === section && visible(item, values),
    ) || [];
  const mutation = useMutation({
    mutationFn: (input: { question_key: string; value: unknown }[]) =>
      saveAnswers(caseId, input),
    onSuccess: (data) => {
      reset(
        normalizeIntakeAnswers(
          questionnaire.data?.questions ?? [],
          data.answers,
        ),
      );
      queryClient.setQueryData(["consultations", caseId, "answers"], data);
      setSaved(true);
    },
  });
  const proceed = handleSubmit(async (formValues) => {
    const payload = answeredSectionPayload(questions, formValues);
    if (payload.length) await mutation.mutateAsync(payload);
    else setSaved(true);
    if (sectionIndex < sections.length - 1) {
      setSectionIndex((value) => value + 1);
      setSaved(false);
    } else
      router.push({ pathname: "/consult/review/[caseId]", params: { caseId } });
  });
  if (!caseId) return <Redirect href={"/consult" as Href} />;
  const lockedPath = answers.data
    ? lockedIntakePath(answers.data.status, caseId)
    : null;
  if (lockedPath) return <Redirect href={lockedPath as Href} />;
  return (
    <AuthGuard>
      <ConsultationPage
        title={questionnaire.data?.title || "Private intake"}
        eyebrow={
          sections.length
            ? `STEP ${sectionIndex + 1} OF ${sections.length}`
            : "PRIVATE INTAKE"
        }
      >
        {questionnaire.isLoading || answers.isLoading ? (
          <LoadingIndicator />
        ) : null}
        {questionnaire.isError || answers.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Your intake could not load.</Text>
            <Text color="danger">
              {getApiErrorMessage(questionnaire.error || answers.error)}
            </Text>
            <Button
              onPress={() => {
                questionnaire.refetch();
                answers.refetch();
              }}
            >
              Try again
            </Button>
          </Card>
        ) : null}
        {questionnaire.data && answers.data ? (
          <>
            <View style={{ gap: theme.spacing.xs }}>
              <Text variant="heading">{section}</Text>
              <Text color="muted">{questionnaire.data.introduction}</Text>
              <View
                style={{
                  height: 5,
                  borderRadius: 99,
                  backgroundColor: theme.colors.border,
                  overflow: "hidden",
                }}
              >
                <View
                  style={{
                    height: "100%",
                    width: `${((sectionIndex + 1) / sections.length) * 100}%`,
                    backgroundColor: theme.colors.accent,
                  }}
                />
              </View>
            </View>
            <Card style={{ gap: theme.spacing.xl }}>
              {questions.map((question) => (
                <QuestionField
                  key={question.key}
                  question={question}
                  control={control}
                />
              ))}
            </Card>
            {saved ? (
              <View
                accessibilityLiveRegion="polite"
                style={{
                  flexDirection: "row",
                  gap: theme.spacing.xs,
                  alignItems: "center",
                }}
              >
                <Feather
                  name="check-circle"
                  size={theme.iconSize.sm}
                  color={theme.colors.success}
                />
                <Text variant="caption" color="primary">
                  Progress saved securely.
                </Text>
              </View>
            ) : null}
            {mutation.isError ? (
              <Text color="danger">{intakeError(mutation.error)}</Text>
            ) : null}
            <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              {sectionIndex ? (
                <Button
                  style={{ flex: 1 }}
                  variant="secondary"
                  onPress={() => {
                    setSectionIndex((value) => value - 1);
                    setSaved(false);
                  }}
                >
                  Previous
                </Button>
              ) : null}
              <Button
                style={{ flex: 1 }}
                loading={mutation.isPending}
                onPress={proceed}
              >
                {sectionIndex === sections.length - 1
                  ? "Save and review"
                  : "Save and continue"}
              </Button>
            </View>
          </>
        ) : null}
      </ConsultationPage>
    </AuthGuard>
  );
}

function answerLabel(question: IntakeQuestion, value: unknown) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value))
    return value
      .map(
        (item) =>
          question.options.find((option) => option.value === item)?.label ||
          String(item),
      )
      .join(", ");
  if (typeof value === "string")
    return (
      question.options.find((option) => option.value === value)?.label || value
    );
  return value == null || value === "" ? "Not answered" : String(value);
}

export function ConsultationReviewScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const questionnaire = useQuery({
    queryKey: ["consultations", caseId, "questionnaire"],
    queryFn: () => getQuestionnaire(caseId),
    enabled: Boolean(caseId),
  });
  const answers = useQuery({
    queryKey: ["consultations", caseId, "answers"],
    queryFn: () => getAnswers(caseId),
    enabled: Boolean(caseId),
  });
  const item = useQuery({
    queryKey: ["consultations", caseId],
    queryFn: () => getConsultation(caseId),
    enabled: Boolean(caseId),
  });
  const submit = useMutation({
    mutationFn: () => completeIntake(caseId),
    onSuccess: (data) => {
      queryClient.setQueryData(["consultations", caseId], data);
      queryClient.setQueryData<IntakeAnswers>(
        ["consultations", caseId, "answers"],
        (current) => (current ? { ...current, status: data.status } : current),
      );
      queryClient.invalidateQueries({ queryKey: ["consultations", "cases"] });
      router.replace({
        pathname: "/consult/complete/[caseId]",
        params: { caseId },
      });
    },
  });
  const lockedPath = item.data
    ? lockedIntakePath(item.data.status, caseId)
    : null;
  if (lockedPath) return <Redirect href={lockedPath as Href} />;
  return (
    <AuthGuard>
      <ConsultationPage title="Review your intake" eyebrow="FINAL CHECK">
        {questionnaire.isLoading || answers.isLoading || item.isLoading ? (
          <LoadingIndicator />
        ) : null}
        {questionnaire.data && answers.data && item.data ? (
          <>
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">{item.data.service_name}</Text>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <Text variant="caption" color="muted">
                  {item.data.duration_minutes} minutes
                </Text>
                <Text variant="bodyStrong">
                  {money(item.data.price_amount, item.data.currency)}
                </Text>
              </View>
              <Divider />
              <Text variant="caption" color="muted">
                {item.data.questionnaire_version
                  ? `Questionnaire version ${item.data.questionnaire_version} · `
                  : ""}
                {item.data.timezone_snapshot}
              </Text>
            </Card>
            <View style={{ gap: theme.spacing.md }}>
              {questionnaire.data.questions
                .filter((question) => visible(question, answers.data.answers))
                .map((question) => (
                  <Card key={question.key} style={{ gap: theme.spacing.xs }}>
                    <Text variant="caption" color="muted">
                      {question.prompt}
                    </Text>
                    <Text variant="bodyStrong">
                      {answerLabel(
                        question,
                        answers.data.answers[question.key],
                      )}
                    </Text>
                  </Card>
                ))}
            </View>
            <Button
              variant="secondary"
              onPress={() =>
                router.replace({
                  pathname: "/consult/intake/[caseId]",
                  params: { caseId },
                })
              }
            >
              Edit answers
            </Button>
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Complete this intake?</Text>
              <Text color="muted">
                After completion, these answers become read-only. Private photo
                uploads are the next step.
              </Text>
              {submit.isError ? (
                <Text color="danger">
                  {intakeError(submit.error)} Return to the intake and complete
                  any required answer.
                </Text>
              ) : null}
              <Button
                loading={submit.isPending}
                onPress={() => submit.mutate()}
              >
                Complete intake
              </Button>
            </Card>
          </>
        ) : null}
      </ConsultationPage>
    </AuthGuard>
  );
}

export function ConsultationCompleteScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const item = useQuery({
    queryKey: ["consultations", caseId],
    queryFn: () => getConsultation(caseId),
    enabled: Boolean(caseId),
  });
  const photosComplete = item.data?.status === "PHOTOS_COMPLETE";
  return (
    <AuthGuard>
      <ConsultationPage
        title={photosComplete ? "Consultation submitted" : "Intake saved"}
        eyebrow={photosComplete ? "READY TO BOOK" : "READY FOR PHOTOS"}
        backHref={"/consult" as Href}
      >
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.data ? (
          <Card style={{ gap: theme.spacing.lg, alignItems: "center" }}>
            <View
              style={{
                width: 64,
                height: 64,
                borderRadius: 32,
                backgroundColor: theme.colors.surfaceMuted,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Feather name="check" size={32} color={theme.colors.success} />
            </View>
            <Text variant="title" style={{ textAlign: "center" }}>
              {photosComplete
                ? "Everything is with TK."
                : "Your story is ready."}
            </Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              {photosComplete
                ? `Your ${item.data.service_name} intake and private photos are available in TK’s app workspace. You can now choose an appointment.`
                : `Your ${item.data.service_name} intake is saved securely. Add your private photos before booking.`}
            </Text>
            <Divider />
            {photosComplete ? (
              <>
                <Button
                  style={{ alignSelf: "stretch" }}
                  onPress={() => router.push(`/book/${caseId}` as Href)}
                >
                  Choose an appointment
                </Button>
                <Button
                  style={{ alignSelf: "stretch" }}
                  variant="secondary"
                  onPress={() => router.push("/appointments" as Href)}
                >
                  My appointments
                </Button>
              </>
            ) : (
              <Button
                style={{ alignSelf: "stretch" }}
                onPress={() => router.push(`/consult/photos/${caseId}` as Href)}
              >
                Add private photos
              </Button>
            )}
            <Button
              style={{ alignSelf: "stretch" }}
              variant="ghost"
              onPress={() => router.replace("/consult" as Href)}
            >
              Back to consultations
            </Button>
          </Card>
        ) : null}
        {item.isError ? (
          <Text color="danger">{getApiErrorMessage(item.error)}</Text>
        ) : null}
      </ConsultationPage>
    </AuthGuard>
  );
}
