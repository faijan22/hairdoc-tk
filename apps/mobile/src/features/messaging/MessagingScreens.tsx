import Feather from "@expo/vector-icons/Feather";
import {
  InfiniteData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AppState,
  FlatList,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  cancelAnimation,
  Easing,
  FadeInUp,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import { Button, Card, LoadingIndicator, Screen, Text } from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { getApiErrorMessage } from "@/features/auth/errors";
import { setActiveConversation } from "@/features/messaging/activeConversation";
import {
  deleteMessage,
  getConversation,
  getConversations,
  getMessages,
  getRealtimeTicket,
  hasRealtimeTransport,
  markConversationRead,
  Message,
  MessageImageAsset,
  parseRealtimeMessage,
  privateMessageImageUrl,
  realtimeUrl,
  sendMessage,
} from "@/services/api/messaging";
import { useTheme } from "@/theme/ThemeProvider";

function Guard({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
  return children;
}

function Header({ title, backHref }: { title: string; backHref?: Href }) {
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
        PRIVATE CARE
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function newClientMessageId() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
    /[xy]/g,
    (character) => {
      const random = Math.floor(Math.random() * 16);
      return (character === "x" ? random : (random & 3) | 8).toString(16);
    },
  );
}

function compactTime(value: string) {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString())
    return date.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ConversationListScreen() {
  const theme = useTheme();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const isStaff = Boolean(user?.is_staff);
  const conversations = useQuery({
    queryKey: ["conversations", user?.public_id],
    queryFn: getConversations,
    enabled: Boolean(user?.public_id),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Messages" backHref="/explore" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">
            {isStaff ? "Client conversations." : "Your conversation with TK."}
          </Text>
          <Text color="muted">
            {isStaff
              ? "One continuous private conversation with each client."
              : "Your private conversation with TK stays together across consultations."}
          </Text>
        </View>
        {conversations.isLoading ? <LoadingIndicator /> : null}
        {conversations.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Messages could not load.</Text>
            <Text color="danger">
              {getApiErrorMessage(conversations.error)}
            </Text>
            <Button onPress={() => conversations.refetch()}>Try again</Button>
          </Card>
        ) : null}
        {conversations.isSuccess && !conversations.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather
              name="message-circle"
              size={30}
              color={theme.colors.textMuted}
            />
            <Text variant="heading">
              {isStaff
                ? "No client conversations yet."
                : "No conversation yet."}
            </Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              {isStaff
                ? "A client's conversation will appear after their first appointment is confirmed."
                : "Your private conversation with TK will appear after your first appointment is confirmed."}
            </Text>
            <Button
              onPress={() =>
                router.push(
                  (isStaff ? "/staff/appointments" : "/consult") as Href,
                )
              }
            >
              {isStaff ? "View appointments" : "View consultations"}
            </Button>
          </Card>
        ) : null}
        {conversations.data?.length ? (
          <View
            style={{
              overflow: "hidden",
              borderRadius: theme.radius.lg,
              backgroundColor: theme.colors.surface,
              ...theme.elevation.card,
            }}
          >
            {conversations.data.map((item, index) => {
              const initial = item.other_member_name.trim().charAt(0) || "H";
              return (
                <Pressable
                  key={item.public_id}
                  accessibilityRole="button"
                  accessibilityLabel={`Open conversation with ${item.other_member_name}`}
                  onPress={() =>
                    router.push(`/messages/${item.public_id}` as Href)
                  }
                  style={({ pressed }) => ({
                    cursor: "pointer",
                    minHeight: 84,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: theme.spacing.sm,
                    paddingHorizontal: theme.spacing.md,
                    paddingVertical: theme.spacing.sm,
                    backgroundColor: pressed
                      ? theme.colors.surfaceMuted
                      : theme.colors.surface,
                    borderTopWidth: index ? 1 : 0,
                    borderTopColor: theme.colors.border,
                  })}
                >
                  <View
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 24,
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: theme.colors.primaryMuted,
                    }}
                  >
                    <Text variant="heading" color="primary">
                      {initial.toUpperCase()}
                    </Text>
                  </View>
                  <View style={{ flex: 1, minWidth: 0, gap: 2 }}>
                    <View
                      style={{
                        flexDirection: "row",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: theme.spacing.sm,
                      }}
                    >
                      <Text variant="bodyStrong" numberOfLines={1}>
                        {item.other_member_name}
                      </Text>
                      <Text variant="caption" color="muted">
                        {compactTime(
                          item.last_message?.created_at || item.updated_at,
                        )}
                      </Text>
                    </View>
                    <View
                      style={{
                        flexDirection: "row",
                        alignItems: "center",
                        gap: theme.spacing.xs,
                      }}
                    >
                      <Text
                        color={item.unread_count ? "default" : "muted"}
                        numberOfLines={1}
                        style={{ flex: 1 }}
                      >
                        {item.last_message?.body ||
                          (item.last_message?.attachment
                            ? "Photo"
                            : "Conversation ready")}
                      </Text>
                      {item.unread_count ? (
                        <View
                          accessibilityLabel={`${item.unread_count} unread messages`}
                          style={{
                            minWidth: 22,
                            height: 22,
                            paddingHorizontal: 6,
                            borderRadius: 11,
                            alignItems: "center",
                            justifyContent: "center",
                            backgroundColor: theme.colors.primary,
                          }}
                        >
                          <Text
                            variant="caption"
                            style={{
                              color: theme.colors.onPrimary,
                              fontSize: 11,
                              lineHeight: 14,
                            }}
                          >
                            {item.unread_count > 99 ? "99+" : item.unread_count}
                          </Text>
                        </View>
                      ) : null}
                    </View>
                  </View>
                </Pressable>
              );
            })}
          </View>
        ) : null}
      </Screen>
    </Guard>
  );
}

async function normalizeImage(
  asset: ImagePicker.ImagePickerAsset,
): Promise<MessageImageAsset> {
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
  const image = await manipulateAsync(asset.uri, actions, {
    compress: 0.88,
    format: SaveFormat.JPEG,
  });
  return {
    uri: image.uri,
    fileName: "message-image.jpg",
    mimeType: "image/jpeg",
    width: image.width,
    height: image.height,
  };
}

type ChatItem = Message & {
  optimistic?: boolean;
  failed?: boolean;
  localImageUri?: string;
};

type MessageDraft = {
  body: string;
  image: MessageImageAsset | null;
  clientMessageId: string;
  replyToPublicId?: string;
  replyTo?: Message["reply_to"];
};

type MessagePage = Awaited<ReturnType<typeof getMessages>>;
type MessagePages = InfiniteData<MessagePage, string | undefined>;

type PendingSocketMessage = {
  resolve: (message: Message) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
};

function putMessage(data: MessagePages | undefined, message: ChatItem) {
  if (!data)
    return {
      pages: [{ next: null, previous: null, results: [message] }],
      pageParams: [undefined],
    };
  let replaced = false;
  const pages = data.pages.map((page) => ({
    ...page,
    results: page.results.map((item) => {
      if (
        item.public_id === message.public_id ||
        item.client_message_id === message.client_message_id
      ) {
        replaced = true;
        return message;
      }
      return item;
    }),
  }));
  if (!replaced && pages[0])
    pages[0] = { ...pages[0], results: [message, ...pages[0].results] };
  return { ...data, pages };
}

function markMessageRead(data: MessagePages | undefined, messageId: string) {
  if (!data) return data;
  return {
    ...data,
    pages: data.pages.map((page) => ({
      ...page,
      results: page.results.map((message) =>
        message.public_id === messageId
          ? { ...message, status: "READ" as const }
          : message,
      ),
    })),
  };
}

function tombstoneMessage(data: MessagePages | undefined, messageId: string) {
  if (!data) return data;
  return {
    ...data,
    pages: data.pages.map((page) => ({
      ...page,
      results: page.results.map((message) =>
        message.public_id === messageId
          ? { ...message, body: "", attachment: null, deleted_for_everyone: true }
          : message.reply_to?.public_id === messageId
            ? { ...message, reply_to: { ...message.reply_to, body: "", has_attachment: false, deleted_for_everyone: true } }
            : message,
      ),
    })),
  };
}

function ChatMessage({
  message,
  mine,
  imageUri,
  onReply,
  onDelete,
  onRetry,
  onOpenImage,
}: {
  message: ChatItem;
  mine: boolean;
  imageUri?: string;
  onReply: () => void;
  onDelete: (mode: "self" | "everyone") => void;
  onRetry: () => void;
  onOpenImage: () => void;
}) {
  const theme = useTheme();
  const viewport = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const [actionsOpen, setActionsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<"self" | "everyone" | null>(null);
  const openActions = () => {
    if (message.optimistic || message.failed) return;
    Keyboard.dismiss();
    setConfirmDelete(null);
    setActionsOpen(true);
  };
  const closeActions = () => {
    setConfirmDelete(null);
    setActionsOpen(false);
  };
  const actionSheetWidth = Math.min(420, viewport.width - 24);
  return (
    <Animated.View
      entering={FadeInUp.duration(180)}
      style={{
        maxWidth: "82%",
        alignSelf: mine ? "flex-end" : "flex-start",
        gap: 2,
      }}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={message.attachment ? "Open private message image. Long press for actions." : "Message. Long press for actions."}
        delayLongPress={280}
        onLongPress={openActions}
        onPress={() => {
          if (message.attachment && imageUri) onOpenImage();
        }}
        style={{
          paddingHorizontal: 12,
          paddingVertical: 8,
          gap: theme.spacing.xs,
          borderRadius: 18,
          borderBottomRightRadius: mine ? 5 : 18,
          borderBottomLeftRadius: mine ? 18 : 5,
          backgroundColor: mine
            ? theme.colors.primaryMuted
            : theme.colors.surface,
        }}
      >
        {message.reply_to ? (
          <View style={{ borderLeftWidth: 3, borderLeftColor: theme.colors.primary, paddingLeft: 8, marginBottom: 3 }}>
            <Text variant="caption" color="primary">{message.reply_to.sender_name}</Text>
            <Text variant="caption" color="muted" numberOfLines={1}>
              {message.reply_to.deleted_for_everyone ? "Message deleted" : message.reply_to.body || "Photo"}
            </Text>
          </View>
        ) : null}
        {message.deleted_for_everyone ? (
          <Text color="muted">This message was deleted.</Text>
        ) : message.attachment ? (
          <Image
            source={{ uri: imageUri }}
            accessibilityLabel="Private message image"
            resizeMode="cover"
            style={{
              width: 240,
              maxWidth: "100%",
              aspectRatio: message.attachment.width / message.attachment.height,
              borderRadius: 13,
              backgroundColor: theme.colors.surfaceMuted,
            }}
          />
        ) : null}
        {message.body && !message.deleted_for_everyone ? <Text>{message.body}</Text> : null}
      </Pressable>
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: mine ? "flex-end" : "flex-start",
          gap: 4,
          paddingHorizontal: 4,
        }}
      >
        {!mine ? (
          <Text variant="caption" color="muted">
            {message.sender_name} ·
          </Text>
        ) : null}
        <Text variant="caption" color="muted">
          {new Date(message.created_at).toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          })}
        </Text>
        {mine ? <MessageReceipt message={message} /> : null}
      </View>
      {message.failed ? (
        <Pressable accessibilityRole="button" onPress={onRetry}>
          <Text variant="caption" color="danger">Not sent · Tap to retry</Text>
        </Pressable>
      ) : null}
      {actionsOpen ? (
        <Modal
          visible
          transparent
          animationType="fade"
          presentationStyle="overFullScreen"
          statusBarTranslucent
          onRequestClose={closeActions}
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close message actions"
            onPress={closeActions}
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              bottom: 0,
              left: 0,
              backgroundColor: "rgba(0, 0, 0, 0.12)",
            }}
          />
          <Animated.View
            entering={FadeInUp.duration(180)}
            accessibilityRole="menu"
            style={{
              position: "absolute",
              bottom: Math.max(insets.bottom, 12),
              left: (viewport.width - actionSheetWidth) / 2,
              width: actionSheetWidth,
              padding: 8,
              borderRadius: 24,
              backgroundColor: theme.colors.surface,
              borderWidth: 1,
              borderColor: theme.colors.border,
              shadowColor: "#000",
              shadowOpacity: 0.18,
              shadowRadius: 18,
              shadowOffset: { width: 0, height: 8 },
              elevation: 8,
            }}
          >
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: 10,
                margin: 4,
                marginBottom: 8,
                padding: 12,
                borderRadius: 16,
                backgroundColor: theme.colors.surfaceMuted,
              }}
            >
              {message.attachment && imageUri ? (
                <Image
                  source={{ uri: imageUri }}
                  accessibilityLabel="Selected message image"
                  resizeMode="cover"
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    backgroundColor: theme.colors.border,
                  }}
                />
              ) : null}
              <View style={{ flex: 1, gap: 2 }}>
                <Text variant="caption" color="primary">
                  {mine ? "You" : message.sender_name}
                </Text>
                <Text numberOfLines={2}>
                  {message.deleted_for_everyone
                    ? "This message was deleted."
                    : message.body || (message.attachment ? "Photo" : "Message")}
                </Text>
              </View>
            </View>
            {confirmDelete ? (
              <View style={{ gap: 12, padding: 8 }}>
                <Text variant="bodyStrong">
                  {confirmDelete === "everyone"
                    ? "Delete for everyone?"
                    : "Delete for you?"}
                </Text>
                <Text variant="caption" color="muted">
                  {confirmDelete === "everyone"
                    ? "This message will be replaced for both people."
                    : "This message will only disappear from your chat."}
                </Text>
                <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: 18 }}>
                  <Pressable accessibilityRole="button" onPress={() => setConfirmDelete(null)} hitSlop={8}>
                    <Text variant="caption">Cancel</Text>
                  </Pressable>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => {
                      onDelete(confirmDelete);
                      closeActions();
                    }}
                    hitSlop={8}
                  >
                    <Text variant="caption" color="danger">Delete</Text>
                  </Pressable>
                </View>
              </View>
            ) : (
              <>
                {!message.deleted_for_everyone ? (
                  <MessageAction
                    icon="corner-up-left"
                    label="Reply"
                    onPress={() => {
                      closeActions();
                      onReply();
                    }}
                  />
                ) : null}
                <MessageAction
                  icon="trash-2"
                  label="Delete for me"
                  danger
                  onPress={() => setConfirmDelete("self")}
                />
                {mine && !message.deleted_for_everyone ? (
                  <MessageAction
                    icon="trash"
                    label="Delete for everyone"
                    danger
                    onPress={() => setConfirmDelete("everyone")}
                  />
                ) : null}
              </>
            )}
          </Animated.View>
        </Modal>
      ) : null}
    </Animated.View>
  );
}

function MessageAction({
  icon,
  label,
  danger = false,
  onPress,
}: {
  icon: keyof typeof Feather.glyphMap;
  label: string;
  danger?: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="menuitem"
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: 50,
        paddingHorizontal: 10,
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        borderRadius: 12,
        backgroundColor: pressed ? theme.colors.surfaceMuted : "transparent",
      })}
    >
      <Feather
        name={icon}
        size={19}
        color={danger ? theme.colors.danger : theme.colors.text}
      />
      <Text color={danger ? "danger" : undefined}>{label}</Text>
    </Pressable>
  );
}

type ViewedImage = {
  uri: string;
  width: number;
  height: number;
};

function MessageImageViewer({
  image,
  onClose,
}: {
  image: ViewedImage;
  onClose: () => void;
}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const reduceMotion = useReducedMotion();
  const viewport = useWindowDimensions();
  const zoom = useSharedValue(1);
  const savedZoom = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedX = useSharedValue(0);
  const savedY = useSharedValue(0);
  const backdropOpacity = useSharedValue(0);
  const viewerOpacity = useSharedValue(0);
  const viewerScale = useSharedValue(0.96);
  const closingRef = useRef(false);

  const close = () => {
    if (closingRef.current) return;
    closingRef.current = true;
    if (reduceMotion) {
      onClose();
      return;
    }
    backdropOpacity.value = withTiming(0, { duration: 150 });
    viewerOpacity.value = withTiming(0, { duration: 120 });
    viewerScale.value = withTiming(0.97, { duration: 150 });
    setTimeout(onClose, 155);
  };

  const reveal = () => {
    if (reduceMotion) {
      backdropOpacity.value = 0.94;
      viewerOpacity.value = 1;
      viewerScale.value = 1;
      return;
    }
    backdropOpacity.value = withTiming(0.94, { duration: 160 });
    viewerOpacity.value = withTiming(1, { duration: 170 });
    viewerScale.value = withTiming(1, { duration: 210 });
  };

  const pinch = Gesture.Pinch()
    .onUpdate((event) => {
      zoom.value = Math.min(4, Math.max(1, savedZoom.value * event.scale));
    })
    .onEnd(() => {
      savedZoom.value = zoom.value;
      if (zoom.value <= 1.02) {
        zoom.value = withTiming(1);
        savedZoom.value = 1;
        translateX.value = withTiming(0);
        translateY.value = withTiming(0);
        savedX.value = 0;
        savedY.value = 0;
      }
    });
  const pan = Gesture.Pan()
    .onUpdate((event) => {
      if (zoom.value <= 1) return;
      const maxX = (viewport.width * (zoom.value - 1)) / 2;
      const maxY = (viewport.height * (zoom.value - 1)) / 2;
      translateX.value = Math.min(maxX, Math.max(-maxX, savedX.value + event.translationX));
      translateY.value = Math.min(maxY, Math.max(-maxY, savedY.value + event.translationY));
    })
    .onEnd(() => {
      savedX.value = translateX.value;
      savedY.value = translateY.value;
    });
  const gesture = Gesture.Simultaneous(pinch, pan);
  const backdropStyle = useAnimatedStyle(() => ({
    opacity: backdropOpacity.value,
  }));
  const imageStyle = useAnimatedStyle(() => ({
    opacity: viewerOpacity.value,
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: zoom.value * viewerScale.value },
    ],
  }));
  const controlsStyle = useAnimatedStyle(() => ({
    opacity: viewerOpacity.value,
  }));

  return (
    <Modal
      visible
      transparent
      animationType="none"
      presentationStyle="overFullScreen"
      statusBarTranslucent
      onRequestClose={close}
    >
      <View style={{ flex: 1, backgroundColor: "transparent" }}>
        <Animated.View
          pointerEvents="none"
          style={[
            {
              position: "absolute",
              top: 0,
              right: 0,
              bottom: 0,
              left: 0,
              backgroundColor: "#000",
            },
            backdropStyle,
          ]}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Close image viewer"
          onPress={close}
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
          }}
        />
        <GestureDetector gesture={gesture}>
          <Animated.View
            style={[
              {
                flex: 1,
                alignItems: "center",
                justifyContent: "center",
              },
              imageStyle,
            ]}
          >
            <Image
              source={{ uri: image.uri }}
              accessibilityLabel="Full-screen private message image"
              resizeMode="contain"
              onLoad={reveal}
              onError={reveal}
              style={{ width: viewport.width, height: viewport.height }}
            />
          </Animated.View>
        </GestureDetector>
        <Animated.View
          style={[
            {
              position: "absolute",
              top: Math.max(insets.top, 12),
              right: 16,
            },
            controlsStyle,
          ]}
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close image"
            onPress={close}
            hitSlop={12}
            style={({ pressed }) => ({
              width: 42,
              height: 42,
              borderRadius: 21,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(255, 255, 255, 0.14)",
              opacity: pressed ? 0.7 : 1,
            })}
          >
            <Feather name="x" size={24} color={theme.colors.onPrimary} />
          </Pressable>
        </Animated.View>
      </View>
    </Modal>
  );
}

function MessageReceipt({ message }: { message: ChatItem }) {
  const theme = useTheme();
  const read = message.status === "READ";
  const color = read ? theme.colors.primary : theme.colors.textMuted;
  return (
    <View
      accessibilityLabel={
        message.failed ? "Not sent" : message.optimistic ? "Sending" : read ? "Read" : "Sent"
      }
      style={{ width: 18, height: 15, position: "relative" }}
    >
      {message.failed ? (
        <Feather name="alert-circle" size={12} color={theme.colors.danger} />
      ) : message.optimistic ? (
        <Feather name="clock" size={12} color={color} />
      ) : (
        <>
          <Feather
            name="check"
            size={13}
            color={color}
            style={{ position: "absolute", left: read ? 0 : 4, top: 1 }}
          />
          {read ? (
            <Feather
              name="check"
              size={13}
              color={color}
              style={{ position: "absolute", left: 5, top: 1 }}
            />
          ) : null}
        </>
      )}
    </View>
  );
}

function TypingDot({ index }: { index: number }) {
  const theme = useTheme();
  const reduceMotion = useReducedMotion();
  const lift = useSharedValue(0);
  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: lift.value }],
  }));
  useEffect(() => {
    if (reduceMotion) return;
    // Reanimated SharedValues are intentionally mutable animation handles.
    // eslint-disable-next-line react-hooks/immutability
    lift.value = withDelay(
      index * 120,
      withRepeat(
        withSequence(
          withTiming(-3, {
            duration: 220,
            easing: Easing.out(Easing.quad),
          }),
          withTiming(0, {
            duration: 220,
            easing: Easing.in(Easing.quad),
          }),
          withTiming(0, { duration: 260 }),
        ),
        -1,
      ),
    );
    return () => cancelAnimation(lift);
  }, [index, lift, reduceMotion]);
  return (
    <Animated.View
      style={[
        {
          width: 6,
          height: 6,
          borderRadius: 3,
          backgroundColor: theme.colors.textMuted,
        },
        style,
      ]}
    />
  );
}

function TypingBubble({ name }: { name: string }) {
  const theme = useTheme();
  return (
    <Animated.View
      entering={FadeInUp.duration(150)}
      accessibilityLabel={`${name} is typing`}
      accessibilityLiveRegion="polite"
      style={{
        alignSelf: "flex-start",
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        marginBottom: theme.spacing.xs,
        paddingHorizontal: theme.spacing.md,
        minWidth: 58,
        height: 36,
        borderRadius: 18,
        borderBottomLeftRadius: 5,
        backgroundColor: theme.colors.surface,
      }}
    >
      {[0, 1, 2].map((index) => (
        <TypingDot key={index} index={index} />
      ))}
      <Text variant="caption" color="muted" style={{ marginLeft: 4 }}>{name} is typing</Text>
    </Animated.View>
  );
}

export function ConversationDetailScreen() {
  const { conversationId } = useLocalSearchParams<{ conversationId: string }>();
  const router = useRouter();
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const userId = user?.public_id;
  const listRef = useRef<FlatList<ChatItem>>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const peerPresenceIdsRef = useRef(new Set<string>());
  const appStateRef = useRef(AppState.currentState);
  const pendingSocketMessages = useRef(new Map<string, PendingSocketMessage>());
  const typingStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const typingRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const typingClearRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sentTypingRef = useRef(false);
  const imageUris = useRef(new Map<string, string>());
  const clientId = useRef(newClientMessageId());
  const bodyRef = useRef("");
  const [body, setBody] = useState("");
  const [image, setImage] = useState<MessageImageAsset | null>(null);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [localPending, setLocalPending] = useState<ChatItem[]>([]);
  const draftById = useRef(new Map<string, MessageDraft>());
  const [imageError, setImageError] = useState("");
  const [viewedImage, setViewedImage] = useState<ViewedImage | null>(null);
  const [typingName, setTypingName] = useState("");
  const [peerOnline, setPeerOnline] = useState(false);
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  const [realtime, setRealtime] = useState<"connecting" | "live" | "fallback">(
    "connecting",
  );
  const conversation = useQuery({
    queryKey: ["conversations", user?.public_id, conversationId],
    queryFn: () => getConversation(conversationId),
    enabled: Boolean(conversationId && user?.public_id),
    initialData: () => queryClient.getQueryData<Awaited<ReturnType<typeof getConversations>>>(["conversations", user?.public_id])
      ?.find((item) => item.public_id === conversationId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  const messages = useInfiniteQuery({
    queryKey: ["conversation-messages", user?.public_id, conversationId],
    queryFn: ({ pageParam }) => getMessages(conversationId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next || undefined,
    enabled: Boolean(conversationId && user?.public_id),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  // The API returns newest-first. An inverted list keeps index zero at the
  // visual bottom, so opening and receiving never starts at old history.
  const newestFirst = useMemo<ChatItem[]>(() => {
    const stored = messages.data?.pages.flatMap((page) => page.results) || [];
    const storedIds = new Set(stored.map((item) => item.client_message_id));
    return [...localPending.filter((item) => !storedIds.has(item.client_message_id)), ...stored]
      .sort((left, right) => right.created_at.localeCompare(left.created_at));
  }, [localPending, messages.data]);
  const latestMessageId = newestFirst[0]?.public_id;
  const latestIncomingMessageId = newestFirst[0]?.sender_public_id !== user?.public_id
    ? newestFirst[0]?.public_id : undefined;
  const refreshLatestMessages = useCallback(async () => {
    try {
      const latestPage = await getMessages(conversationId);
      queryClient.setQueryData<MessagePages>(
        ["conversation-messages", userId, conversationId],
        (current) =>
          current
            ? {
                ...current,
                pages: [latestPage, ...current.pages.slice(1)],
              }
            : current,
      );
    } catch { /* Keep the current timeline; the next reconnect can retry. */ }
  }, [conversationId, queryClient, userId]);
  const stopTyping = useCallback(() => {
    if (typingStopRef.current) clearTimeout(typingStopRef.current);
    typingStopRef.current = null;
    if (typingRefreshRef.current) clearInterval(typingRefreshRef.current);
    typingRefreshRef.current = null;
    if (
      sentTypingRef.current &&
      socketRef.current?.readyState === WebSocket.OPEN
    )
      socketRef.current.send(JSON.stringify({ type: "typing.stopped" }));
    sentTypingRef.current = false;
  }, []);
  const startTyping = useCallback(() => {
    const socket = socketRef.current;
    if (!bodyRef.current.trim() || socket?.readyState !== WebSocket.OPEN) return;
    if (!sentTypingRef.current) {
      socket.send(JSON.stringify({ type: "typing.started" }));
      sentTypingRef.current = true;
    }
    if (!typingRefreshRef.current)
      typingRefreshRef.current = setInterval(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN && sentTypingRef.current)
          socketRef.current.send(JSON.stringify({ type: "typing.started" }));
      }, 1800);
    if (typingStopRef.current) clearTimeout(typingStopRef.current);
    typingStopRef.current = setTimeout(stopTyping, 3000);
  }, [stopTyping]);
  const changeBody = (value: string) => {
    bodyRef.current = value;
    setBody(value);
    if (!value.trim()) {
      stopTyping();
      return;
    }
    startTyping();
  };
  useEffect(() => {
    if (!conversationId) return;
    const subscription = AppState.addEventListener("change", (state) => {
      const wasActive = appStateRef.current === "active";
      appStateRef.current = state;
      const socket = socketRef.current;
      if (state === "active") {
        if (!wasActive) void refreshLatestMessages();
        if (socket?.readyState === WebSocket.OPEN)
          socket.send(JSON.stringify({ type: "presence.active" }));
      } else {
        stopTyping();
        if (socket?.readyState === WebSocket.OPEN)
          socket.send(JSON.stringify({ type: "presence.inactive" }));
      }
    });
    return () => subscription.remove();
  }, [conversationId, refreshLatestMessages, stopTyping]);
  const sendTextOverSocket = useCallback(
    (text: string, messageId: string, replyToPublicId?: string) =>
      new Promise<Message>((resolve, reject) => {
        const socket = socketRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          reject(new Error("Realtime connection is unavailable."));
          return;
        }
        const timeout = setTimeout(() => {
          pendingSocketMessages.current.delete(messageId);
          reject(new Error("Realtime acknowledgement timed out."));
        }, 5000);
        pendingSocketMessages.current.set(messageId, {
          resolve,
          reject,
          timeout,
        });
        socket.send(
          JSON.stringify({
            type: "message.send",
            body: text,
            client_message_id: messageId,
            reply_to_public_id: replyToPublicId,
          }),
        );
      }),
    [],
  );
  const send = useMutation({
    mutationFn: async (draft: MessageDraft) => {
      if (!draft.image && socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          return await sendTextOverSocket(draft.body, draft.clientMessageId, draft.replyToPublicId);
        } catch {
          // The same client id makes this safe if the socket committed just
          // before disconnecting but its acknowledgement never arrived.
        }
      }
      return sendMessage(
        conversationId,
        draft.body,
        draft.clientMessageId,
        draft.image || undefined,
        draft.replyToPublicId,
      );
    },
    onMutate: (draft) => {
      stopTyping();
      draftById.current.set(draft.clientMessageId, draft);
      const optimistic: ChatItem = {
        public_id: draft.clientMessageId,
        conversation_public_id: conversationId,
        sender_public_id: user?.public_id || draft.clientMessageId,
        sender_name:
          [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
          user?.email ||
          "You",
        body: draft.body,
        status: "SENT",
        client_message_id: draft.clientMessageId,
        created_at: new Date().toISOString(),
        deleted_for_everyone: false,
        reply_to: draft.replyTo || null,
        attachment: draft.image
          ? {
              public_id: draft.clientMessageId,
              content_type: draft.image.mimeType || "image/jpeg",
              byte_size: 0,
              width: draft.image.width || 1,
              height: draft.image.height || 1,
              content_path: draft.image.uri,
            }
          : null,
        optimistic: true,
        localImageUri: draft.image?.uri,
      };
      setLocalPending((current) => [optimistic, ...current.filter((item) => item.client_message_id !== draft.clientMessageId)]);
      setBody("");
      bodyRef.current = "";
      setImage(null);
      setReplyTo(null);
      clientId.current = newClientMessageId();
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true }),
      );
    },
    onSuccess: (message) => {
      queryClient.setQueryData<MessagePages>(
        ["conversation-messages", user?.public_id, conversationId],
        (current) => putMessage(current, message),
      );
      setLocalPending((current) => current.filter((item) => item.client_message_id !== message.client_message_id));
      draftById.current.delete(message.client_message_id);
    },
    onError: (_error, draft) => {
      setLocalPending((current) => current.map((item) => item.client_message_id === draft.clientMessageId
        ? { ...item, failed: true, optimistic: false } : item));
    },
  });
  const remove = useMutation({
    mutationFn: ({ id, mode }: { id: string; mode: "self" | "everyone" }) => deleteMessage(conversationId, id, mode),
    onSuccess: ({ mode, message_public_id }) => {
      if (mode === "self") {
        queryClient.setQueryData<MessagePages>(["conversation-messages", user?.public_id, conversationId], (current) => current && ({
          ...current, pages: current.pages.map((page) => ({ ...page, results: page.results.filter((item) => item.public_id !== message_public_id) })),
        }));
      } else {
        queryClient.setQueryData<MessagePages>(["conversation-messages", user?.public_id, conversationId], (current) => tombstoneMessage(current, message_public_id));
      }
    },
  });

  useEffect(() => {
    setActiveConversation(conversationId || null);
    return () => setActiveConversation(null);
  }, [conversationId]);

  useEffect(() => {
    const show = Keyboard.addListener(
      Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow",
      () => {
        setKeyboardVisible(true);
        requestAnimationFrame(() =>
          listRef.current?.scrollToOffset({ offset: 0, animated: true }),
        );
      },
    );
    const hide = Keyboard.addListener(
      Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide",
      () => setKeyboardVisible(false),
    );
    return () => {
      stopTyping();
      if (typingClearRef.current) clearTimeout(typingClearRef.current);
      show.remove();
      hide.remove();
    };
  }, [stopTyping]);
  useEffect(() => {
    if (latestMessageId)
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: false }),
      );
  }, [latestMessageId]);
  useEffect(() => {
    if (latestIncomingMessageId)
      void markConversationRead(conversationId, latestIncomingMessageId)
        .catch(() => undefined);
  }, [conversationId, latestIncomingMessageId]);
  useEffect(() => {
    let stopped = false;
    const peerPresenceIds = peerPresenceIdsRef.current;
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    let readyTimer: ReturnType<typeof setTimeout> | undefined;
    let lastPongAt = Date.now();
    let failures = 0;
    let hasBeenReady = false;
    const rejectPendingSocketMessages = () => {
      pendingSocketMessages.current.forEach((pending) => {
        clearTimeout(pending.timeout);
        pending.reject(new Error("Realtime connection closed."));
      });
      pendingSocketMessages.current.clear();
    };
    const connect = async () => {
      try {
        setRealtime("connecting");
        peerPresenceIds.clear();
        setPeerOnline(false);
        if (!hasRealtimeTransport()) {
          setRealtime("fallback");
          return;
        }
        const issued = await getRealtimeTicket(conversationId);
        const url = realtimeUrl(issued.websocket_path, issued.ticket);
        if (!url) {
          setRealtime("fallback");
          return;
        }
        socket = new WebSocket(url);
        socketRef.current = socket;
        socket.onopen = () => {
          readyTimer = setTimeout(() => socket?.close(), 8000);
          heartbeat = setInterval(() => {
            if (socket?.readyState === WebSocket.OPEN && Date.now() - lastPongAt > 35_000) {
              socket.close();
            } else if (socket?.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: "ping" }));
            }
          }, 20_000);
        };
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(String(event.data));
            if (payload.type === "pong") {
              lastPongAt = Date.now();
            } else if (payload.type === "realtime.ready") {
              failures = 0;
              lastPongAt = Date.now();
              if (readyTimer) clearTimeout(readyTimer);
              setRealtime("live");
              if (appStateRef.current !== "active")
                socket?.send(JSON.stringify({ type: "presence.inactive" }));
              if (hasBeenReady) void refreshLatestMessages();
              hasBeenReady = true;
              if (bodyRef.current.trim() && socket?.readyState === WebSocket.OPEN) {
                startTyping();
              }
            } else if (payload.type === "conversation.typing") {
              if (payload.user_public_id !== user?.public_id) {
                setTypingName(payload.is_typing ? payload.user_name : "");
                if (typingClearRef.current)
                  clearTimeout(typingClearRef.current);
                if (payload.is_typing)
                  typingClearRef.current = setTimeout(
                    () => setTypingName(""),
                    5000,
                  );
              }
            } else if (payload.type === "conversation.presence") {
              if (
                payload.user_public_id !== user?.public_id &&
                typeof payload.connection_id === "string"
              ) {
                if (payload.online)
                  peerPresenceIds.add(payload.connection_id);
                else peerPresenceIds.delete(payload.connection_id);
                setPeerOnline(peerPresenceIds.size > 0);
              }
            } else if (payload.type === "message.created") {
              setTypingName("");
              const pending = pendingSocketMessages.current.get(
                payload.message?.client_message_id,
              );
              if (payload.message?.attachment_pending) {
                void refreshLatestMessages();
              } else {
                const message = parseRealtimeMessage(payload.message);
                queryClient.setQueryData<MessagePages>(
                  ["conversation-messages", user?.public_id, conversationId],
                  (current) => putMessage(current, message),
                );
                setLocalPending((current) => current.filter((item) => item.client_message_id !== message.client_message_id));
                if (pending) {
                  clearTimeout(pending.timeout);
                  pendingSocketMessages.current.delete(
                    message.client_message_id,
                  );
                  pending.resolve(message);
                }
              }
            } else if (payload.type === "message.deleted") {
              queryClient.setQueryData<MessagePages>(
                ["conversation-messages", user?.public_id, conversationId],
                (current) => tombstoneMessage(current, payload.message_public_id),
              );
            } else if (payload.type === "conversation.read") {
              queryClient.setQueryData<MessagePages>(
                ["conversation-messages", user?.public_id, conversationId],
                (current) =>
                  markMessageRead(current, payload.message_public_id),
              );
            } else if (payload.type === "message.rejected") {
              const pending = pendingSocketMessages.current.get(
                payload.client_message_id,
              );
              if (pending) {
                clearTimeout(pending.timeout);
                pendingSocketMessages.current.delete(payload.client_message_id);
                pending.reject(new Error("Message was not accepted."));
              }
            }
          } catch {
            /* REST remains the source of truth. */
          }
        };
        socket.onerror = () => {
          setRealtime("fallback");
          socket?.close();
        };
        socket.onclose = () => {
          if (readyTimer) clearTimeout(readyTimer);
          if (heartbeat) clearInterval(heartbeat);
          rejectPendingSocketMessages();
          if (socketRef.current === socket) socketRef.current = null;
          stopTyping();
          setTypingName("");
          peerPresenceIds.clear();
          setPeerOnline(false);
          if (!stopped) {
            setRealtime("fallback");
            retry = setTimeout(connect, Math.min(30_000, 2000 * 2 ** Math.min(failures++, 4)));
          }
        };
      } catch {
        if (!stopped) {
          setRealtime("fallback");
          retry = setTimeout(connect, Math.min(30_000, 2000 * 2 ** Math.min(failures++, 4)));
        }
      }
    };
    if (conversationId) void connect();
    return () => {
      stopped = true;
      if (retry) clearTimeout(retry);
      if (readyTimer) clearTimeout(readyTimer);
      if (heartbeat) clearInterval(heartbeat);
      rejectPendingSocketMessages();
      stopTyping();
      peerPresenceIds.clear();
      setPeerOnline(false);
      socketRef.current = null;
      socket?.close();
    };
  }, [conversationId, queryClient, refreshLatestMessages, startTyping, stopTyping, user?.public_id]);

  const chooseImage = async () => {
    setImageError("");
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setImageError("Allow photo-library access to attach an image.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsMultipleSelection: false,
      quality: 1,
    });
    if (!result.canceled) {
      try {
        setImage(await normalizeImage(result.assets[0]));
      } catch {
        setImageError("This image could not be prepared.");
      }
    }
  };
  if (!conversationId) return <Redirect href={"/messages" as Href} />;
  const canSend = Boolean(body.trim() || image);
  const submitMessage = () => {
    if (!canSend) return;
    send.mutate({
      body: body.trim(),
      image,
      clientMessageId: clientId.current,
      replyToPublicId: replyTo?.public_id,
      replyTo: replyTo ? {
        public_id: replyTo.public_id,
        sender_name: replyTo.sender_name,
        body: replyTo.body.slice(0, 120),
        deleted_for_everyone: replyTo.deleted_for_everyone,
        has_attachment: Boolean(replyTo.attachment),
      } : null,
    });
  };
  const imageUriFor = (message: ChatItem) => {
    if (!message.attachment) return undefined;
    if (message.localImageUri) return message.localImageUri;
    const key = message.attachment.public_id;
    const existing = imageUris.current.get(key);
    if (existing) return existing;
    const uri = privateMessageImageUrl(message.attachment.content_path);
    imageUris.current.set(key, uri);
    return uri;
  };

  return (
    <Guard>
      <>
        <SafeAreaView
          edges={["top", "left", "right"]}
          style={{ flex: 1, backgroundColor: theme.colors.background }}
        >
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <View
            style={{
              flex: 1,
              width: "100%",
              maxWidth: theme.layout.contentMaxWidth,
              alignSelf: "center",
            }}
          >
            <View
              style={{
                minHeight: 58,
                paddingHorizontal: theme.spacing.md,
                flexDirection: "row",
                alignItems: "center",
                borderBottomWidth: 1,
                borderBottomColor: theme.colors.border,
                backgroundColor: theme.colors.background,
              }}
            >
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Go back"
                onPress={() =>
                  router.canGoBack()
                    ? router.back()
                    : router.replace("/messages")
                }
                hitSlop={10}
                style={{
                  width: 40,
                  height: 40,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Feather
                  name="chevron-left"
                  size={theme.iconSize.md}
                  color={theme.colors.text}
                />
              </Pressable>
              <View style={{ flex: 1, paddingHorizontal: theme.spacing.xs }}>
                <Text variant="bodyStrong" numberOfLines={1}>
                  {conversation.data?.other_member_name || "Conversation"}
                </Text>
                <View
                  style={{ flexDirection: "row", alignItems: "center", gap: 5 }}
                >
                  <View
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: 3,
                      backgroundColor:
                        typingName || peerOnline
                          ? theme.colors.success
                          : theme.colors.textMuted,
                    }}
                  />
                  <Text variant="caption" color="muted">
                    {typingName
                      ? `${typingName} is typing…`
                      : peerOnline
                      ? "Online"
                      : realtime === "live"
                        ? "Offline"
                      : realtime === "connecting"
                        ? "Connecting…"
                        : "Reconnecting…"}
                  </Text>
                </View>
              </View>
            </View>
            <FlatList
              ref={listRef}
              data={newestFirst}
              inverted
              keyExtractor={(item) =>
                item.client_message_id || item.public_id
              }
              renderItem={({ item }) => (
                <ChatMessage
                  message={item}
                  mine={item.sender_public_id === user?.public_id}
                  imageUri={imageUriFor(item)}
                  onOpenImage={() => {
                    const uri = imageUriFor(item);
                    if (!uri || !item.attachment) return;
                    setViewedImage({
                      uri,
                      width: item.attachment.width,
                      height: item.attachment.height,
                    });
                  }}
                  onReply={() => { setReplyTo(item); listRef.current?.scrollToOffset({ offset: 0, animated: true }); }}
                  onDelete={(mode) => remove.mutate({ id: item.public_id, mode })}
                  onRetry={() => {
                    const draft = draftById.current.get(item.client_message_id);
                    if (draft) send.mutate(draft);
                  }}
                />
              )}
              contentContainerStyle={{
                flexGrow: 1,
                gap: theme.spacing.sm,
                paddingHorizontal: theme.spacing.md,
                paddingVertical: theme.spacing.sm,
              }}
              showsVerticalScrollIndicator={false}
              onEndReachedThreshold={0.3}
              onEndReached={() => {
                if (messages.hasNextPage && !messages.isFetching)
                  void messages.fetchNextPage();
              }}
              keyboardShouldPersistTaps="handled"
              keyboardDismissMode={
                Platform.OS === "ios" ? "interactive" : "on-drag"
              }
              ListFooterComponent={
                messages.isFetchingNextPage ? (
                  <LoadingIndicator />
                ) : undefined
              }
              ListEmptyComponent={
                messages.isLoading ? (
                  <LoadingIndicator />
                ) : messages.isError ? (
                  <View
                    style={{
                      flex: 1,
                      justifyContent: "center",
                      alignItems: "center",
                      gap: theme.spacing.sm,
                    }}
                  >
                    <Text variant="bodyStrong">
                      Conversation could not load.
                    </Text>
                    <Text color="danger">
                      {getApiErrorMessage(messages.error)}
                    </Text>
                    <Button
                      variant="secondary"
                      onPress={() => messages.refetch()}
                    >
                      Try again
                    </Button>
                  </View>
                ) : (
                  <View
                    style={{
                      flex: 1,
                      justifyContent: "center",
                      alignItems: "center",
                      padding: theme.spacing.xl,
                      gap: theme.spacing.xs,
                    }}
                  >
                    <Text variant="heading">Start the conversation.</Text>
                    <Text color="muted" style={{ textAlign: "center" }}>
                      Messages and images stay private to this consultation.
                    </Text>
                  </View>
                )
              }
            />
            {typingName ? (
              <View
                style={{
                  minHeight: 44,
                  justifyContent: "center",
                  paddingHorizontal: theme.spacing.md,
                  backgroundColor: theme.colors.background,
                }}
              >
                <TypingBubble name={typingName} />
              </View>
            ) : null}
            <View
              style={{
                borderTopWidth: 1,
                borderTopColor: theme.colors.border,
                paddingHorizontal: theme.spacing.sm,
                paddingTop: 6,
                paddingBottom: keyboardVisible ? 6 : Math.max(6, insets.bottom),
                backgroundColor: theme.colors.surface,
              }}
            >
              {replyTo ? (
                <View style={{ flexDirection: "row", alignItems: "center", borderLeftWidth: 3, borderLeftColor: theme.colors.primary, paddingHorizontal: 10, paddingVertical: 6, marginBottom: 6, backgroundColor: theme.colors.surfaceMuted }}>
                  <View style={{ flex: 1 }}>
                    <Text variant="caption" color="primary">Reply to {replyTo.sender_name}</Text>
                    <Text variant="caption" color="muted" numberOfLines={1}>{replyTo.body || "Photo"}</Text>
                  </View>
                  <Pressable accessibilityRole="button" accessibilityLabel="Cancel reply" onPress={() => setReplyTo(null)} hitSlop={10}>
                    <Feather name="x" size={18} color={theme.colors.textMuted} />
                  </Pressable>
                </View>
              ) : null}
              {image ? (
                <View style={{ width: 62, marginBottom: 6 }}>
                  <Image
                    source={{ uri: image.uri }}
                    accessibilityLabel="Selected message image"
                    style={{
                      width: 58,
                      height: 58,
                      borderRadius: theme.radius.sm,
                    }}
                  />
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Remove selected image"
                    onPress={() => setImage(null)}
                    style={{
                      position: "absolute",
                      right: -5,
                      top: -5,
                      width: 22,
                      height: 22,
                      borderRadius: 11,
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: theme.colors.text,
                    }}
                  >
                    <Feather name="x" size={14} color={theme.colors.surface} />
                  </Pressable>
                </View>
              ) : null}
              <View
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Attach image"
                  onPress={() => void chooseImage()}
                  style={({ pressed }) => ({
                    width: 44,
                    height: 44,
                    borderRadius: 22,
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: pressed
                      ? theme.colors.primaryMuted
                      : theme.colors.surfaceMuted,
                    opacity: 1,
                  })}
                >
                  <Feather
                    name="image"
                    size={20}
                    color={theme.colors.primary}
                  />
                </Pressable>
                <TextInput
                  accessibilityLabel="Message"
                  value={body}
                  onChangeText={changeBody}
                  onFocus={() => startTyping()}
                  onBlur={stopTyping}
                  multiline
                  maxLength={4000}
                  returnKeyType="send"
                  submitBehavior="submit"
                  onKeyPress={(event) => {
                    if (
                      Platform.OS === "web" &&
                      event.nativeEvent.key === "Enter"
                    ) {
                      event.preventDefault();
                      submitMessage();
                    }
                  }}
                  onSubmitEditing={
                    Platform.OS === "web" ? undefined : submitMessage
                  }
                  placeholder="Message…"
                  placeholderTextColor={theme.colors.textMuted}
                  selectionColor={theme.colors.primary}
                  cursorColor={theme.colors.primary}
                  style={[
                    theme.typography.body,
                    {
                      flex: 1,
                      minHeight: 44,
                      maxHeight: 112,
                      paddingHorizontal: theme.spacing.sm,
                      paddingVertical: 8,
                      color: theme.colors.text,
                      borderWidth: 1,
                      borderColor: theme.colors.border,
                      borderRadius: 22,
                      backgroundColor: theme.colors.background,
                      textAlignVertical: "center",
                    },
                  ]}
                />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Send message"
                  disabled={!canSend}
                  onPress={submitMessage}
                  style={({ pressed }) => ({
                    width: 44,
                    height: 44,
                    borderRadius: 22,
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: canSend
                      ? theme.colors.primary
                      : theme.colors.surfaceMuted,
                    opacity: pressed ? 0.75 : 1,
                  })}
                >
                  <Feather
                    name="send"
                    size={18}
                    color={canSend ? theme.colors.onPrimary : theme.colors.textMuted}
                  />
                </Pressable>
              </View>
              {imageError || remove.isError ? (
                <Text
                  variant="caption"
                  color="danger"
                  style={{ paddingTop: 4 }}
                >
                  {imageError || getApiErrorMessage(remove.error)}
                </Text>
              ) : null}
            </View>
          </View>
        </KeyboardAvoidingView>
        </SafeAreaView>
        {viewedImage ? (
          <MessageImageViewer
            image={viewedImage}
            onClose={() => setViewedImage(null)}
          />
        ) : null}
      </>
    </Guard>
  );
}
