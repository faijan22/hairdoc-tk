import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Image, Pressable, ScrollView, View } from "react-native";

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
import { privatePhotoUrl } from "@/services/api/consultations";
import {
  deleteProgressPhoto,
  getProgress,
  getProgressCheckIn,
  getProgressPhotos,
  getStaffProgress,
  getStaffProgressCheckIn,
  ProgressCategory,
  publishProgressFeedback,
  saveProgressFeedback,
  submitProgress,
  updateProgress,
  uploadProgressPhoto,
} from "@/services/api/progress";
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
        {staff ? "TK WORKSPACE" : "YOUR JOURNEY"}
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function Photos({
  title,
  photos,
  removable,
  onRemove,
}: {
  title: string;
  photos: {
    public_id: string;
    category_label: string;
    content_path: string | null;
  }[];
  removable?: boolean;
  onRemove?: (id: string) => void;
}) {
  const theme = useTheme();
  if (!photos.length) return null;
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <Text variant="heading">{title}</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: theme.spacing.sm }}
      >
        {photos.map((photo) => {
          const uri = privatePhotoUrl(photo.content_path);
          return (
            <Card
              key={photo.public_id}
              style={{
                width: 230,
                padding: theme.spacing.sm,
                gap: theme.spacing.sm,
              }}
            >
              {uri ? (
                <Image
                  source={{ uri }}
                  accessibilityLabel={photo.category_label}
                  resizeMode="cover"
                  style={{
                    width: "100%",
                    aspectRatio: 4 / 3,
                    borderRadius: theme.radius.md,
                    backgroundColor: theme.colors.surfaceMuted,
                  }}
                />
              ) : null}
              <Text variant="caption">{photo.category_label}</Text>
              {removable ? (
                <Button
                  variant="ghost"
                  onPress={() => onRemove?.(photo.public_id)}
                >
                  Remove
                </Button>
              ) : null}
            </Card>
          );
        })}
      </ScrollView>
    </View>
  );
}

function CheckInFields({
  summary,
  setSummary,
  wins,
  setWins,
  challenges,
  setChallenges,
  adherence,
  setAdherence,
  questions,
  setQuestions,
}: {
  summary: string;
  setSummary: (v: string) => void;
  wins: string;
  setWins: (v: string) => void;
  challenges: string;
  setChallenges: (v: string) => void;
  adherence: number | null;
  setAdherence: (v: number) => void;
  questions: string;
  setQuestions: (v: string) => void;
}) {
  const theme = useTheme();
  return (
    <>
      <TextField
        label="How has your hair or scalp changed?"
        value={summary}
        multiline
        maxLength={2000}
        style={{ minHeight: 120, textAlignVertical: "top" }}
        onChangeText={setSummary}
      />
      <TextField
        label="What is going well? (optional)"
        value={wins}
        multiline
        maxLength={2000}
        style={{ minHeight: 100, textAlignVertical: "top" }}
        onChangeText={setWins}
      />
      <TextField
        label="What has been difficult? (optional)"
        value={challenges}
        multiline
        maxLength={2000}
        style={{ minHeight: 100, textAlignVertical: "top" }}
        onChangeText={setChallenges}
      />
      <View style={{ gap: theme.spacing.sm }}>
        <Text variant="caption">How closely did you follow the plan?</Text>
        <View style={{ flexDirection: "row", gap: theme.spacing.xs }}>
          {[1, 2, 3, 4, 5].map((value) => (
            <Pressable
              key={value}
              accessibilityRole="radio"
              accessibilityState={{ selected: adherence === value }}
              onPress={() => setAdherence(value)}
              style={{
                flex: 1,
                minHeight: 44,
                alignItems: "center",
                justifyContent: "center",
                borderRadius: theme.radius.md,
                backgroundColor:
                  adherence === value
                    ? theme.colors.primaryMuted
                    : theme.colors.surfaceMuted,
              }}
            >
              <Text color={adherence === value ? "primary" : "muted"}>
                {value}
              </Text>
            </Pressable>
          ))}
        </View>
        <Text variant="caption" color="muted">
          1 means rarely; 5 means consistently.
        </Text>
      </View>
      <TextField
        label="Questions for TK (optional)"
        value={questions}
        multiline
        maxLength={2000}
        style={{ minHeight: 100, textAlignVertical: "top" }}
        onChangeText={setQuestions}
      />
    </>
  );
}

export function ClientProgressListScreen() {
  const theme = useTheme();
  const router = useRouter();
  const items = useQuery({ queryKey: ["progress"], queryFn: getProgress });
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Progress" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">See change over time.</Text>
          <Text color="muted">
            Your private check-ins, follow-up photos, and TK’s published
            feedback stay together.
          </Text>
        </View>
        {items.isLoading ? <LoadingIndicator /> : null}
        {items.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Progress could not load.</Text>
            <Text color="danger">{getApiErrorMessage(items.error)}</Text>
            <Button onPress={() => items.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {items.isSuccess && !items.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather
              name="trending-up"
              size={30}
              color={theme.colors.textMuted}
            />
            <Text variant="heading">No check-ins yet.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              Open a published Care Plan to start your first progress check-in.
            </Text>
            <Button
              variant="secondary"
              onPress={() => router.push("/plans" as Href)}
            >
              View care plans
            </Button>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {items.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
              <Text
                variant="overline"
                color={item.status === "REVIEWED" ? "primary" : "accent"}
              >
                CHECK-IN {item.sequence} · {item.status}
              </Text>
              <Text variant="heading">{item.service_name}</Text>
              <Text color="muted">
                {item.summary || "Continue your saved check-in."}
              </Text>
              <Button
                variant="secondary"
                onPress={() =>
                  router.push(`/progress/${item.public_id}` as Href)
                }
              >
                {item.status === "DRAFT"
                  ? "Continue check-in"
                  : "View check-in"}
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </Guard>
  );
}

export function ClientProgressDetailScreen() {
  const { checkInId } = useLocalSearchParams<{ checkInId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();
  const item = useQuery({
    queryKey: ["progress", checkInId],
    queryFn: () => getProgressCheckIn(checkInId),
    enabled: Boolean(checkInId),
  });
  const photoQuery = useQuery({
    queryKey: ["progress", checkInId, "photos"],
    queryFn: () => getProgressPhotos(checkInId),
    enabled: Boolean(checkInId) && item.data?.status === "DRAFT",
  });
  const [loaded, setLoaded] = useState("");
  const [summary, setSummary] = useState("");
  const [wins, setWins] = useState("");
  const [challenges, setChallenges] = useState("");
  const [adherence, setAdherence] = useState<number | null>(null);
  const [questions, setQuestions] = useState("");
  const [category, setCategory] = useState<ProgressCategory>("OTHER");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (!item.data || loaded === item.data.public_id) return;
    // Query data intentionally seeds this editable draft exactly once per check-in.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoaded(item.data.public_id);
    setSummary(item.data.summary);
    setWins(item.data.wins);
    setChallenges(item.data.challenges);
    setAdherence(item.data.routine_adherence);
    setQuestions(item.data.questions_for_tk);
  }, [item.data, loaded]);
  const payload = () => ({
    summary: summary.trim(),
    wins: wins.trim(),
    challenges: challenges.trim(),
    routine_adherence: adherence,
    questions_for_tk: questions.trim(),
  });
  const save = useMutation({
    mutationFn: () => updateProgress(checkInId, payload()),
    onSuccess: (data) => {
      queryClient.setQueryData(["progress", checkInId], data);
      setSaved(true);
    },
  });
  const upload = useMutation({
    mutationFn: (asset: { uri: string; fileName: string; mimeType: string }) =>
      uploadProgressPhoto(checkInId, asset, category),
    onSuccess: (data) =>
      queryClient.setQueryData(["progress", checkInId, "photos"], data),
  });
  const remove = useMutation({
    mutationFn: (photoId: string) => deleteProgressPhoto(checkInId, photoId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["progress", checkInId, "photos"],
      }),
  });
  const submit = useMutation({
    mutationFn: async () => {
      await updateProgress(checkInId, payload());
      return submitProgress(checkInId);
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(["progress", checkInId], data);
      await queryClient.invalidateQueries({ queryKey: ["progress"] });
    },
  });
  const choose = async (source: "camera" | "library") => {
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({
            mediaTypes: ["images"],
            quality: 1,
          })
        : await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ["images"],
            quality: 1,
            selectionLimit: 1,
          });
    if (result.canceled) return;
    const sourceAsset = result.assets[0];
    const longest = Math.max(sourceAsset.width, sourceAsset.height);
    const actions =
      longest > 2400
        ? [
            {
              resize:
                sourceAsset.width >= sourceAsset.height
                  ? { width: 2400 }
                  : { height: 2400 },
            },
          ]
        : [];
    const normalized = await manipulateAsync(sourceAsset.uri, actions, {
      compress: 0.88,
      format: SaveFormat.JPEG,
    });
    upload.mutate({
      uri: normalized.uri,
      fileName: "progress-photo.jpg",
      mimeType: "image/jpeg",
    });
  };
  if (!checkInId) return <Redirect href={"/progress" as Href} />;
  const draft = item.data?.status === "DRAFT";
  const photos = draft
    ? photoQuery.data?.photos || []
    : item.data?.photos || [];
  return (
    <Guard>
      <Screen keyboardAware contentStyle={{ gap: theme.spacing.xl }}>
        <Header title={`Check-in ${item.data?.sequence || ""}`} />
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.isError ? (
          <Card>
            <Text color="danger">{getApiErrorMessage(item.error)}</Text>
          </Card>
        ) : null}
        {item.data ? (
          draft ? (
            <>
              <View style={{ gap: theme.spacing.xs }}>
                <Text variant="display">Share what has changed.</Text>
                <Text color="muted">
                  Your answers and photos remain private between you and TK.
                </Text>
              </View>
              <CheckInFields
                summary={summary}
                setSummary={(v) => {
                  setSaved(false);
                  setSummary(v);
                }}
                wins={wins}
                setWins={(v) => {
                  setSaved(false);
                  setWins(v);
                }}
                challenges={challenges}
                setChallenges={(v) => {
                  setSaved(false);
                  setChallenges(v);
                }}
                adherence={adherence}
                setAdherence={(v) => {
                  setSaved(false);
                  setAdherence(v);
                }}
                questions={questions}
                setQuestions={(v) => {
                  setSaved(false);
                  setQuestions(v);
                }}
              />
              <Divider />
              <Card style={{ gap: theme.spacing.md }}>
                <Text variant="heading">Follow-up photos</Text>
                <Text color="muted">
                  Use a similar angle and lighting to your original photos for a
                  useful comparison.
                </Text>
                {photoQuery.data?.consent.required &&
                !photoQuery.data.consent.accepted ? (
                  <>
                    <Text color="danger">
                      Accept the current{" "}
                      {photoQuery.data.consent.document_title} before adding
                      photos.
                    </Text>
                    {photoQuery.data.consent.available ? (
                      <Button
                        variant="secondary"
                        onPress={() =>
                          router.push({
                            pathname: "/settings/legal/[type]",
                            params: { type: "PHOTO_DATA_CONSENT" },
                          })
                        }
                      >
                        Review consent
                      </Button>
                    ) : null}
                  </>
                ) : null}
                <View
                  style={{
                    flexDirection: "row",
                    flexWrap: "wrap",
                    gap: theme.spacing.xs,
                  }}
                >
                  {(
                    [
                      "FRONT",
                      "TOP",
                      "LEFT",
                      "RIGHT",
                      "BACK",
                      "CLOSE_UP",
                      "OTHER",
                    ] as ProgressCategory[]
                  ).map((value) => (
                    <Pressable
                      key={value}
                      onPress={() => setCategory(value)}
                      style={{
                        paddingHorizontal: theme.spacing.sm,
                        paddingVertical: theme.spacing.xs,
                        borderRadius: theme.radius.pill,
                        backgroundColor:
                          category === value
                            ? theme.colors.primaryMuted
                            : theme.colors.surfaceMuted,
                      }}
                    >
                      <Text
                        variant="caption"
                        color={category === value ? "primary" : "muted"}
                      >
                        {value.replace("_", " ")}
                      </Text>
                    </Pressable>
                  ))}
                </View>
                <Button
                  disabled={
                    !!photoQuery.data?.consent.required &&
                    !photoQuery.data.consent.accepted
                  }
                  loading={upload.isPending}
                  onPress={() => choose("camera")}
                >
                  Take photo
                </Button>
                <Button
                  variant="secondary"
                  disabled={
                    !!photoQuery.data?.consent.required &&
                    !photoQuery.data.consent.accepted
                  }
                  loading={upload.isPending}
                  onPress={() => choose("library")}
                >
                  Choose from library
                </Button>
                {upload.isError ? (
                  <Text color="danger">{getApiErrorMessage(upload.error)}</Text>
                ) : null}
              </Card>
              <Photos
                title="Added photos"
                photos={photos}
                removable
                onRemove={(id) => remove.mutate(id)}
              />
              {saved ? (
                <Text variant="bodyStrong" color="primary">
                  Check-in saved.
                </Text>
              ) : null}
              {save.isError || submit.isError ? (
                <Text color="danger">
                  {getApiErrorMessage(save.error || submit.error)}
                </Text>
              ) : null}
              <Button
                variant="secondary"
                disabled={!summary.trim()}
                loading={save.isPending}
                onPress={() => save.mutate()}
              >
                Save draft
              </Button>
              <Button
                disabled={!summary.trim() || !photos.length}
                loading={submit.isPending}
                onPress={() => submit.mutate()}
              >
                Submit to TK
              </Button>
            </>
          ) : (
            <>
              <Card style={{ gap: theme.spacing.sm }}>
                <Text
                  variant="overline"
                  color={item.data.status === "REVIEWED" ? "primary" : "accent"}
                >
                  {item.data.status}
                </Text>
                <Text variant="display">Your check-in</Text>
                <Text>{item.data.summary}</Text>
                {item.data.wins ? (
                  <>
                    <Text variant="caption" color="muted">
                      What is going well
                    </Text>
                    <Text>{item.data.wins}</Text>
                  </>
                ) : null}
                {item.data.challenges ? (
                  <>
                    <Text variant="caption" color="muted">
                      Challenges
                    </Text>
                    <Text>{item.data.challenges}</Text>
                  </>
                ) : null}
                {item.data.routine_adherence ? (
                  <Text color="muted">
                    Plan consistency: {item.data.routine_adherence} of 5
                  </Text>
                ) : null}
              </Card>
              <Photos
                title="Starting photos"
                photos={item.data.baseline_photos}
              />
              <Photos title="Follow-up photos" photos={item.data.photos} />
              <Card style={{ gap: theme.spacing.sm }}>
                <Text variant="heading">TK’s feedback</Text>
                {item.data.expert_feedback ? (
                  <Text>{item.data.expert_feedback}</Text>
                ) : (
                  <Text color="muted">
                    TK has received this check-in. Published feedback will
                    appear here.
                  </Text>
                )}
              </Card>
            </>
          )
        ) : null}
      </Screen>
    </Guard>
  );
}

export function StaffProgressListScreen() {
  const theme = useTheme();
  const router = useRouter();
  const items = useQuery({
    queryKey: ["staff", "progress"],
    queryFn: getStaffProgress,
  });
  return (
    <Guard staff>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Progress reviews" staff />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Follow-up from clients.</Text>
          <Text color="muted">
            Submitted check-ins and published feedback appear here.
          </Text>
        </View>
        {items.isLoading ? <LoadingIndicator /> : null}
        {items.isError ? (
          <Card>
            <Text color="danger">{getApiErrorMessage(items.error)}</Text>
          </Card>
        ) : null}
        {items.isSuccess && !items.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather
              name="trending-up"
              size={30}
              color={theme.colors.textMuted}
            />
            <Text variant="heading">No progress check-ins yet.</Text>
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {items.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.sm }}>
              <Text
                variant="overline"
                color={item.status === "REVIEWED" ? "primary" : "accent"}
              >
                {item.status} · CHECK-IN {item.sequence}
              </Text>
              <Text variant="heading">{item.client_name}</Text>
              <Text color="muted">{item.service_name}</Text>
              <Text>{item.summary}</Text>
              <Button
                variant="secondary"
                onPress={() =>
                  router.push(`/staff/progress/${item.public_id}` as Href)
                }
              >
                {item.status === "REVIEWED"
                  ? "View feedback"
                  : "Review check-in"}
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </Guard>
  );
}

export function StaffProgressDetailScreen() {
  const { checkInId } = useLocalSearchParams<{ checkInId: string }>();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const item = useQuery({
    queryKey: ["staff", "progress", checkInId],
    queryFn: () => getStaffProgressCheckIn(checkInId),
    enabled: Boolean(checkInId),
  });
  const [loaded, setLoaded] = useState("");
  const [feedback, setFeedback] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (item.data && loaded !== item.data.public_id) {
      // Query data intentionally seeds this editable review once per check-in.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoaded(item.data.public_id);
      setFeedback(item.data.expert_feedback);
    }
  }, [item.data, loaded]);
  const save = useMutation({
    mutationFn: () => saveProgressFeedback(checkInId, feedback.trim()),
    onSuccess: (data) => {
      queryClient.setQueryData(["staff", "progress", checkInId], data);
      setSaved(true);
    },
  });
  const publish = useMutation({
    mutationFn: async () => {
      await saveProgressFeedback(checkInId, feedback.trim());
      return publishProgressFeedback(checkInId);
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(["staff", "progress", checkInId], data);
      await queryClient.invalidateQueries({ queryKey: ["staff", "progress"] });
    },
  });
  if (!checkInId) return <Redirect href={"/staff/progress" as Href} />;
  const editable = item.data?.status === "SUBMITTED";
  return (
    <Guard staff>
      <Screen keyboardAware contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Progress review" staff />
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.isError ? (
          <Card>
            <Text color="danger">{getApiErrorMessage(item.error)}</Text>
          </Card>
        ) : null}
        {item.data ? (
          <>
            <Card style={{ gap: theme.spacing.sm }}>
              <Text variant="overline" color={editable ? "accent" : "primary"}>
                {item.data.status} · CHECK-IN {item.data.sequence}
              </Text>
              <Text variant="display">{item.data.client_name}</Text>
              <Text color="muted">{item.data.service_name}</Text>
              <Divider />
              <Text variant="caption" color="muted">
                Progress summary
              </Text>
              <Text>{item.data.summary}</Text>
              {item.data.wins ? (
                <>
                  <Text variant="caption" color="muted">
                    Wins
                  </Text>
                  <Text>{item.data.wins}</Text>
                </>
              ) : null}
              {item.data.challenges ? (
                <>
                  <Text variant="caption" color="muted">
                    Challenges
                  </Text>
                  <Text>{item.data.challenges}</Text>
                </>
              ) : null}
              {item.data.questions_for_tk ? (
                <>
                  <Text variant="caption" color="muted">
                    Questions for TK
                  </Text>
                  <Text>{item.data.questions_for_tk}</Text>
                </>
              ) : null}
              {item.data.routine_adherence ? (
                <Text color="muted">
                  Plan consistency: {item.data.routine_adherence} of 5
                </Text>
              ) : null}
            </Card>
            <Photos
              title="Starting photos"
              photos={item.data.baseline_photos}
            />
            <Photos title="Follow-up photos" photos={item.data.photos} />
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Feedback for client</Text>
              <TextField
                label="Private until published"
                value={feedback}
                editable={editable}
                multiline
                maxLength={4000}
                style={{ minHeight: 150, textAlignVertical: "top" }}
                onChangeText={(value) => {
                  setSaved(false);
                  setFeedback(value);
                }}
              />
              {saved ? (
                <Text variant="bodyStrong" color="primary">
                  Feedback draft saved.
                </Text>
              ) : null}
              {save.isError || publish.isError ? (
                <Text color="danger">
                  {getApiErrorMessage(save.error || publish.error)}
                </Text>
              ) : null}
              {editable ? (
                <>
                  <Button
                    variant="secondary"
                    disabled={!feedback.trim()}
                    loading={save.isPending}
                    onPress={() => save.mutate()}
                  >
                    Save feedback draft
                  </Button>
                  <Button
                    disabled={!feedback.trim()}
                    loading={publish.isPending}
                    onPress={() => publish.mutate()}
                  >
                    Publish feedback
                  </Button>
                  <Text variant="caption" color="muted">
                    Publishing makes this feedback visible to the client and
                    locks it.
                  </Text>
                </>
              ) : (
                <Text variant="caption" color="muted">
                  Published feedback is locked.
                </Text>
              )}
            </Card>
          </>
        ) : null}
      </Screen>
    </Guard>
  );
}
