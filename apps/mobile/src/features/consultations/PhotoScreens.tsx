import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Image, Modal, Pressable, View } from "react-native";

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
import { ApiError } from "@/services/api/client";
import {
  completeConsultationPhotos,
  ConsultationPhoto,
  ConsultationPhotoCategory,
  deleteConsultationPhoto,
  getConsultationPhotos,
  privatePhotoUrl,
  uploadConsultationPhoto,
} from "@/services/api/consultations";
import { useTheme } from "@/theme/ThemeProvider";

const categories: { value: ConsultationPhotoCategory; label: string }[] = [
  { value: "FRONT", label: "Front hairline" },
  { value: "TOP", label: "Top / parting" },
  { value: "LEFT", label: "Left side" },
  { value: "RIGHT", label: "Right side" },
  { value: "BACK", label: "Back" },
  { value: "CLOSE_UP", label: "Concern close-up" },
  { value: "OTHER", label: "Other" },
];

type UploadAsset = { uri: string; fileName: string; mimeType: string };

function photoError(error: unknown) {
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

async function normalizeAsset(
  asset: ImagePicker.ImagePickerAsset,
): Promise<UploadAsset> {
  const longest = Math.max(asset.width, asset.height);
  const actions =
    longest > 2400
      ? [
          {
            resize:
              asset.width >= asset.height ? { width: 2400 } : { height: 2400 },
          },
        ]
      : [];
  const normalized = await manipulateAsync(asset.uri, actions, {
    compress: 0.88,
    format: SaveFormat.JPEG,
  });
  return {
    uri: normalized.uri,
    fileName: "consultation-photo.jpg",
    mimeType: "image/jpeg",
  };
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
        PRIVATE CONSULTATION
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function CategoryPicker({
  value,
  onChange,
}: {
  value: ConsultationPhotoCategory;
  onChange: (value: ConsultationPhotoCategory) => void;
}) {
  const theme = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <Text variant="bodyStrong">What will this photo show?</Text>
      <View
        style={{
          flexDirection: "row",
          flexWrap: "wrap",
          gap: theme.spacing.xs,
        }}
      >
        {categories.map((item) => (
          <Pressable
            key={item.value}
            accessibilityRole="radio"
            accessibilityState={{ selected: value === item.value }}
            onPress={() => onChange(item.value)}
            style={{
              cursor: "pointer",
              paddingHorizontal: theme.spacing.md,
              paddingVertical: theme.spacing.sm,
              borderRadius: theme.radius.pill,
              borderWidth: 1,
              borderColor:
                value === item.value
                  ? theme.colors.primary
                  : theme.colors.border,
              backgroundColor:
                value === item.value
                  ? theme.colors.surfaceMuted
                  : theme.colors.surface,
            }}
          >
            <Text
              variant="caption"
              color={value === item.value ? "primary" : "default"}
            >
              {item.label}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function PhotoCard({
  photo,
  editable,
  onRemove,
}: {
  photo: ConsultationPhoto;
  editable: boolean;
  onRemove: () => void;
}) {
  const theme = useTheme();
  const uri = privatePhotoUrl(photo.content_path);
  return (
    <Card
      style={{
        gap: theme.spacing.sm,
        padding: theme.spacing.sm,
        width: "100%",
      }}
    >
      {uri ? (
        <Image
          source={{ uri }}
          accessibilityLabel={`${photo.category_label} consultation photo`}
          resizeMode="cover"
          style={{
            width: "100%",
            aspectRatio: 4 / 3,
            borderRadius: theme.radius.md,
            backgroundColor: theme.colors.surfaceMuted,
          }}
        />
      ) : null}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: theme.spacing.sm,
        }}
      >
        <View style={{ flex: 1 }}>
          <Text variant="bodyStrong">{photo.category_label}</Text>
          <Text variant="caption" color="muted">
            {Math.max(1, Math.round(photo.byte_size / 1024))} KB · {photo.width}
            ×{photo.height}
          </Text>
        </View>
        {editable ? (
          <Button variant="ghost" onPress={onRemove}>
            Remove
          </Button>
        ) : null}
      </View>
    </Card>
  );
}

export function ConsultationPhotosScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const auth = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const [category, setCategory] = useState<ConsultationPhotoCategory>("FRONT");
  const [uploadStatus, setUploadStatus] = useState("");
  const [failedAsset, setFailedAsset] = useState<UploadAsset | null>(null);
  const [removePhoto, setRemovePhoto] = useState<ConsultationPhoto | null>(
    null,
  );
  const photos = useQuery({
    queryKey: ["consultations", caseId, "photos"],
    queryFn: () => getConsultationPhotos(caseId),
    enabled: auth === "authenticated" && !user?.is_staff && Boolean(caseId),
  });
  const upload = useMutation({
    mutationFn: (asset: UploadAsset) =>
      uploadConsultationPhoto(caseId, asset, category),
    onSuccess: (data) => {
      queryClient.setQueryData(["consultations", caseId, "photos"], data);
      setFailedAsset(null);
      setUploadStatus("Photo uploaded securely.");
    },
    onError: () => setUploadStatus(""),
  });
  const remove = useMutation({
    mutationFn: (photoId: string) => deleteConsultationPhoto(caseId, photoId),
    onSuccess: async () => {
      setRemovePhoto(null);
      await photos.refetch();
      setUploadStatus("Photo removed.");
    },
  });
  const complete = useMutation({
    mutationFn: () => completeConsultationPhotos(caseId),
    onSuccess: async (item) => {
      queryClient.setQueryData(["consultations", caseId], item);
      await queryClient.invalidateQueries({
        queryKey: ["consultations", "cases"],
      });
      router.replace({
        pathname: "/consult/complete/[caseId]",
        params: { caseId },
      });
    },
  });

  const choose = async (source: "camera" | "library") => {
    setUploadStatus("");
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setUploadStatus(
        `Allow ${source === "camera" ? "camera" : "photo library"} access to continue.`,
      );
      return;
    }
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({
            mediaTypes: ["images"],
            quality: 1,
          })
        : await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ["images"],
            allowsMultipleSelection: true,
            selectionLimit: Math.max(
              1,
              (photos.data?.max_photos || 8) -
                (photos.data?.photos.length || 0),
            ),
            quality: 1,
          });
    if (result.canceled) return;
    for (let index = 0; index < result.assets.length; index += 1) {
      try {
        setUploadStatus(
          `Preparing and uploading ${index + 1} of ${result.assets.length}…`,
        );
        const asset = await normalizeAsset(result.assets[index]);
        await upload.mutateAsync(asset);
      } catch {
        const asset = await normalizeAsset(result.assets[index]).catch(
          () => null,
        );
        setFailedAsset(asset);
        setUploadStatus("");
        break;
      }
    }
  };

  if (!caseId) return <Redirect href={"/consult" as Href} />;
  if (auth === "bootstrapping") return <LoadingIndicator />;
  if (auth !== "authenticated") return <Redirect href="/auth/sign-in" />;
  if (user?.is_staff) return <Redirect href="/staff/consultations" />;
  const overview = photos.data;
  return (
    <Screen contentStyle={{ gap: theme.spacing.xl }}>
      <Header title="Private photos" />
      <View style={{ gap: theme.spacing.sm }}>
        <Text variant="display">Help TK see the full picture.</Text>
        <Text color="muted">
          Use natural light, keep hair dry and product-free where possible, and
          avoid filters. Add clear angles that show your concern.
        </Text>
      </View>
      {photos.isLoading ? <LoadingIndicator /> : null}
      {photos.isError ? (
        <Card style={{ gap: theme.spacing.md }}>
          <Text variant="heading">Your private photos could not load.</Text>
          <Text color="danger">{getApiErrorMessage(photos.error)}</Text>
          <Button onPress={() => photos.refetch()}>Try again</Button>
        </Card>
      ) : null}
      {overview ? (
        <>
          {overview.consent.required ? (
            <Card style={{ gap: theme.spacing.md }}>
              <View
                style={{
                  flexDirection: "row",
                  gap: theme.spacing.sm,
                  alignItems: "center",
                }}
              >
                <Feather
                  name={overview.consent.accepted ? "shield" : "alert-circle"}
                  size={theme.iconSize.md}
                  color={
                    overview.consent.accepted
                      ? theme.colors.success
                      : theme.colors.accent
                  }
                />
                <View style={{ flex: 1 }}>
                  <Text variant="bodyStrong">
                    {overview.consent.document_title}
                    {overview.consent.document_version
                      ? ` · v${overview.consent.document_version}`
                      : ""}
                  </Text>
                  <Text variant="caption" color="muted">
                    {overview.consent.accepted
                      ? "Your current consent is active."
                      : overview.consent.available
                        ? "Review and accept the current consent before uploading."
                        : "Photo consent is not available right now. Contact HairDoc TK before uploading."}
                  </Text>
                </View>
              </View>
              {!overview.consent.accepted && overview.consent.available ? (
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
              <Button variant="ghost" onPress={() => photos.refetch()}>
                Refresh consent
              </Button>
            </Card>
          ) : null}
          <View style={{ gap: theme.spacing.sm }}>
            <View
              style={{ flexDirection: "row", justifyContent: "space-between" }}
            >
              <Text variant="heading">Your photos</Text>
              <Text variant="caption" color="muted">
                {overview.photos.length} of {overview.max_photos}
              </Text>
            </View>
            {overview.photos.length ? (
              overview.photos.map((photo) => (
                <PhotoCard
                  key={photo.public_id}
                  photo={photo}
                  editable={overview.editable}
                  onRemove={() => setRemovePhoto(photo)}
                />
              ))
            ) : (
              <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
                <Feather
                  name="camera"
                  size={32}
                  color={theme.colors.textMuted}
                />
                <Text variant="bodyStrong">No photos added yet.</Text>
                <Text color="muted" style={{ textAlign: "center" }}>
                  Start with front, top, and the area you are most concerned
                  about.
                </Text>
              </Card>
            )}
          </View>
          {overview.editable ? (
            <Card style={{ gap: theme.spacing.md }}>
              <CategoryPicker value={category} onChange={setCategory} />
              <Divider />
              <View style={{ gap: theme.spacing.sm }}>
                <Button
                  disabled={
                    (overview.consent.required && !overview.consent.accepted) ||
                    overview.photos.length >= overview.max_photos
                  }
                  loading={upload.isPending}
                  onPress={() => choose("camera")}
                >
                  <Feather
                    name="camera"
                    size={theme.iconSize.sm}
                    color={theme.colors.onPrimary}
                  />{" "}
                  Take a photo
                </Button>
                <Button
                  variant="secondary"
                  disabled={
                    (overview.consent.required && !overview.consent.accepted) ||
                    overview.photos.length >= overview.max_photos
                  }
                  loading={upload.isPending}
                  onPress={() => choose("library")}
                >
                  <Feather
                    name="image"
                    size={theme.iconSize.sm}
                    color={theme.colors.primary}
                  />{" "}
                  Choose from library
                </Button>
              </View>
              {uploadStatus ? (
                <View accessibilityLiveRegion="polite">
                  <Text variant="bodyStrong" color="primary">
                    {uploadStatus}
                  </Text>
                </View>
              ) : null}
              {upload.isError ? (
                <Text color="danger">{photoError(upload.error)}</Text>
              ) : null}
              {failedAsset ? (
                <Button
                  variant="secondary"
                  loading={upload.isPending}
                  onPress={() => upload.mutate(failedAsset)}
                >
                  Retry failed photo
                </Button>
              ) : null}
            </Card>
          ) : null}
          {overview.editable ? (
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="heading">Ready to share with TK?</Text>
              <Text color="muted">
                Check every image first. After submission, the photo set becomes
                read-only and appears in TK’s private app workspace.
              </Text>
              {complete.isError ? (
                <Text color="danger">{photoError(complete.error)}</Text>
              ) : null}
              <Button
                disabled={!overview.photos.length}
                loading={complete.isPending}
                onPress={() => complete.mutate()}
              >
                Submit photos securely
              </Button>
            </Card>
          ) : (
            <Card style={{ gap: theme.spacing.sm }}>
              <Text variant="heading">Photos submitted securely.</Text>
              <Text color="muted">
                TK can now review this intake and photo set in the private staff
                workspace.
              </Text>
            </Card>
          )}
        </>
      ) : null}
      <Modal
        transparent
        animationType="fade"
        visible={Boolean(removePhoto)}
        onRequestClose={() => setRemovePhoto(null)}
      >
        <View
          style={{
            flex: 1,
            justifyContent: "center",
            alignItems: "center",
            padding: theme.spacing.lg,
            backgroundColor: "rgba(0,0,0,0.55)",
          }}
        >
          <Card style={{ width: "100%", maxWidth: 440, gap: theme.spacing.md }}>
            <Text variant="title">Remove this photo?</Text>
            <Text color="muted">
              It will be deleted from this consultation and local private
              storage.
            </Text>
            <Button
              variant="secondary"
              disabled={remove.isPending}
              onPress={() => setRemovePhoto(null)}
            >
              Keep photo
            </Button>
            <Button
              loading={remove.isPending}
              onPress={() =>
                removePhoto && remove.mutate(removePhoto.public_id)
              }
            >
              Remove photo
            </Button>
            {remove.isError ? (
              <Text color="danger">{photoError(remove.error)}</Text>
            ) : null}
          </Card>
        </View>
      </Modal>
    </Screen>
  );
}
