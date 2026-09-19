import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { Href, useRouter } from "expo-router";
import { ComponentProps, PropsWithChildren, useMemo } from "react";
import {
  Linking,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";
import Animated, {
  FadeInDown,
  useReducedMotion,
} from "react-native-reanimated";

import {
  Button,
  Card,
  Divider,
  LoadingIndicator,
  Screen,
  Text,
} from "@/components/ui";
import { useAuthStore } from "@/features/auth/authStore";
import { PublicLandingScreen } from "@/features/content/PublicLandingScreen";
import { NotificationBell } from "@/features/notifications/NotificationBell";
import {
  ConsultationService,
  getStaffConsultations,
} from "@/services/api/consultations";
import { ContentItem } from "@/services/api/content";
import { getHome } from "@/services/api/home";
import { motion } from "@/theme/motion";
import { useTheme } from "@/theme/ThemeProvider";

type FeatherName = ComponentProps<typeof Feather>["name"];

const typeLabel: Record<ContentItem["type"], string> = {
  TEDX: "Watch TK",
  BOOK: "TK’s book",
  PRODUCT: "Hair care",
  RESOURCE: "Resource",
  ARTICLE: "Learn",
  PROMOTION: "Featured",
};

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

function SectionEntrance({
  index,
  children,
}: PropsWithChildren<{ index: number }>) {
  const reduceMotion = useReducedMotion();
  return (
    <Animated.View
      entering={FadeInDown.delay(reduceMotion ? 0 : index * 65).duration(
        reduceMotion ? 0 : motion.duration.normal,
      )}
    >
      {children}
    </Animated.View>
  );
}

function QuickAction({
  icon,
  label,
  description,
  onPress,
  wide,
}: {
  icon: FeatherName;
  label: string;
  description: string;
  onPress: () => void;
  wide: boolean;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => ({
        cursor: "pointer",
        width: wide ? "31.5%" : "48%",
        minHeight: 116,
        padding: 18,
        gap: theme.spacing.sm,
        borderRadius: theme.radius.lg,
        backgroundColor: pressed
          ? theme.colors.primaryMuted
          : theme.colors.surface,
        transform: [{ scale: pressed ? 0.985 : 1 }],
      })}
    >
      <View
        style={{
          width: 38,
          height: 38,
          borderRadius: theme.radius.md,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.primaryMuted,
        }}
      >
        <Feather name={icon} size={19} color={theme.colors.primary} />
      </View>
      <View style={{ gap: 2 }}>
        <Text variant="bodyStrong">{label}</Text>
        <Text variant="caption" color="muted">
          {description}
        </Text>
      </View>
    </Pressable>
  );
}

function ServicePreview({
  service,
  wide,
  onPress,
}: {
  service: ConsultationService;
  wide: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`View ${service.name}`}
      onPress={onPress}
      style={({ pressed }) => ({
        width: wide ? "48.5%" : "100%",
        cursor: "pointer",
        opacity: pressed ? 0.86 : 1,
      })}
    >
      <Card style={{ minHeight: 168, gap: theme.spacing.md }}>
        <View
          style={{
            flexDirection: "row",
            alignItems: "flex-start",
            gap: theme.spacing.sm,
          }}
        >
          <View style={{ flex: 1, gap: theme.spacing.xs }}>
            <Text variant="overline" color="accent">
              PRIVATE CONSULTATION
            </Text>
            <Text variant="heading">{service.name}</Text>
          </View>
          <Feather
            name="arrow-up-right"
            size={theme.iconSize.md}
            color={theme.colors.primary}
          />
        </View>
        <Text color="muted">{service.short_description}</Text>
        <Divider />
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Text variant="caption" color="muted">
            {service.duration_minutes} minutes
          </Text>
          <Text variant="bodyStrong" color="primary">
            {money(service.price_amount, service.currency)}
          </Text>
        </View>
      </Card>
    </Pressable>
  );
}

function appointmentTime(value: string): string {
  return new Date(value).toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function TkWorkspaceHome({ firstName }: { firstName?: string }) {
  const router = useRouter();
  const theme = useTheme();
  const { width } = useWindowDimensions();
  const wide = width >= 720;
  const reviews = useQuery({
    queryKey: ["staff", "consultations", "recent"],
    queryFn: () => getStaffConsultations(3),
  });
  const latestReview = reviews.data?.[0];

  return (
    <Screen contentStyle={{ gap: theme.spacing.xl }}>
      <SectionEntrance index={0}>
        <View style={{ gap: theme.spacing.sm, paddingTop: theme.spacing.sm }}>
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: theme.spacing.xs,
              }}
            >
              <View
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: theme.radius.pill,
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: theme.colors.primaryMuted,
                }}
              >
                <Feather name="shield" size={16} color={theme.colors.primary} />
              </View>
              <Text variant="overline" color="primary">
                TK WORKSPACE
              </Text>
            </View>
            <NotificationBell />
          </View>
          <Text variant="display">
            {firstName ? `Welcome, ${firstName}.` : "Welcome, TK."}
          </Text>
          <Text color="muted">
            This is the expert workspace. Client reviews, appointments,
            messages, and availability stay separate from the client app.
          </Text>
        </View>
      </SectionEntrance>

      <SectionEntrance index={1}>
        <Card
          style={{
            gap: theme.spacing.md,
            backgroundColor: theme.colors.primaryMuted,
            borderColor: theme.colors.decorative,
          }}
        >
          <Text variant="overline" color="primary">
            START HERE
          </Text>
          <Text variant="title">
            {latestReview
              ? latestReview.client_name
              : "Review submitted consultations"}
          </Text>
          <Text color="muted">
            {latestReview
              ? `${latestReview.service_name} · ${latestReview.photo_count} ${latestReview.photo_count === 1 ? "photo" : "photos"} · submitted ${new Date(latestReview.photos_completed_at).toLocaleString()}`
              : "New client intakes and consented photo sets will appear here."}
          </Text>
          {reviews.isError ? (
            <Text color="danger">The review queue could not refresh.</Text>
          ) : null}
          <Button
            onPress={() =>
              router.push(
                (latestReview
                  ? `/staff/consultations/${latestReview.public_id}`
                  : "/staff/consultations") as Href,
              )
            }
          >
            {latestReview ? "Review latest upload" : "Open client reviews"}
          </Button>
        </Card>
      </SectionEntrance>

      <SectionEntrance index={2}>
        <View style={{ gap: theme.spacing.md }}>
          <View style={{ gap: 2 }}>
            <Text variant="heading">Today’s work</Text>
            <Text variant="caption" color="muted">
              Only expert tools appear in this section.
            </Text>
          </View>
          <View
            style={{
              flexDirection: "row",
              flexWrap: "wrap",
              justifyContent: "space-between",
              rowGap: theme.spacing.sm,
            }}
          >
            <QuickAction
              wide={wide}
              icon="clipboard"
              label="Reviews"
              description="Intake and photos"
              onPress={() => router.push("/staff/consultations" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="calendar"
              label="Appointments"
              description="Client schedule"
              onPress={() => router.push("/staff/appointments" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="message-circle"
              label="Messages"
              description="Client conversations"
              onPress={() => router.push("/messages" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="clock"
              label="Availability"
              description="Hours and exceptions"
              onPress={() => router.push("/staff/availability" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="credit-card"
              label="Payments"
              description="Client payment activity"
              onPress={() => router.push("/payments" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="trending-up"
              label="Progress"
              description="Check-ins and feedback"
              onPress={() => router.push("/staff/progress" as Href)}
            />
            <QuickAction
              wide={wide}
              icon="settings"
              label="Settings"
              description="Profile and security"
              onPress={() => router.push("/settings" as Href)}
            />
          </View>
        </View>
      </SectionEntrance>
    </Screen>
  );
}

export function ContentHubScreen() {
  const router = useRouter();
  const theme = useTheme();
  const { width } = useWindowDimensions();
  const authStatus = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const authenticated = authStatus === "authenticated";
  const wide = width >= 720;
  const home = useQuery({
    queryKey: ["home", user?.public_id],
    queryFn: getHome,
    enabled: authenticated && !user?.is_staff,
  });
  const activeConsultation = home.data?.active_consultation;
  const nextAppointment = home.data?.next_appointment;
  const styles = useMemo(
    () =>
      StyleSheet.create({
        screen: { gap: 28 },
        header: { gap: theme.spacing.sm },
        topRow: {
          minHeight: 48,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: theme.spacing.md,
        },
        identity: { flexDirection: "row", alignItems: "center", gap: 12 },
        avatar: {
          width: 42,
          height: 42,
          borderRadius: theme.radius.pill,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.primary,
        },
        roundAction: {
          width: 44,
          height: 44,
          borderRadius: theme.radius.pill,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.surface,
        },
        hero: { maxWidth: 620 },
        nextCard: {
          gap: 18,
          padding: theme.spacing.lg,
          backgroundColor: theme.colors.primaryMuted,
        },
        nextIcon: {
          width: 44,
          height: 44,
          borderRadius: theme.radius.md,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.colors.surface,
        },
        section: { gap: 18 },
        sectionHeader: { gap: 4 },
        actions: {
          flexDirection: "row",
          flexWrap: "wrap",
          justifyContent: "space-between",
          rowGap: theme.spacing.sm,
        },
        serviceGrid: {
          flexDirection: "row",
          flexWrap: "wrap",
          justifyContent: "space-between",
          rowGap: theme.spacing.md,
        },
        card: { gap: theme.spacing.sm },
        empty: {
          alignItems: "center",
          gap: theme.spacing.md,
          paddingVertical: theme.spacing.lg,
        },
        contentRow: { gap: theme.spacing.sm },
      }),
    [theme],
  );

  if (authStatus === "bootstrapping") {
    return (
      <Screen
        scroll={false}
        contentStyle={{ alignItems: "center", justifyContent: "center" }}
      >
        <LoadingIndicator />
      </Screen>
    );
  }
  if (!authenticated) return <PublicLandingScreen />;
  if (user?.is_staff) return <TkWorkspaceHome firstName={user.first_name} />;

  const consultationStep = (() => {
    if (!activeConsultation) return null;
    if (activeConsultation.status === "DRAFT")
      return {
        label: "Continue intake",
        title: activeConsultation.service_name,
        body: "Your answers are saved. Continue when you’re ready.",
        href: `/consult/intake/${activeConsultation.public_id}` as Href,
      };
    if (activeConsultation.status === "INTAKE_COMPLETE")
      return {
        label: "Add private photos",
        title: "Your intake is complete",
        body: "Add the requested hair or scalp views before booking.",
        href: `/consult/photos/${activeConsultation.public_id}` as Href,
      };
    return {
      label: "Choose appointment",
      title: "Your consultation is ready to book",
      body: `${activeConsultation.service_name} · ${activeConsultation.duration_minutes} minutes`,
      href: `/book/${activeConsultation.public_id}` as Href,
    };
  })();

  return (
    <Screen contentStyle={styles.screen}>
      <SectionEntrance index={0}>
        <View style={styles.topRow}>
          <View style={styles.identity}>
            <View style={styles.avatar}>
              <Text
                variant="bodyStrong"
                style={{ color: theme.colors.onPrimary }}
              >
                {(
                  user?.first_name?.[0] ||
                  user?.email?.[0] ||
                  "H"
                ).toUpperCase()}
              </Text>
            </View>
            <View style={{ gap: 1 }}>
              <Text variant="caption" color="muted">
                Welcome back
              </Text>
              <Text variant="bodyStrong">
                {user?.first_name || "Your care"}
              </Text>
            </View>
          </View>
          <View style={{ flexDirection: "row", gap: theme.spacing.xs }}>
            <NotificationBell />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Open settings"
              onPress={() => router.push("/settings" as Href)}
              style={({ pressed }) => [
                styles.roundAction,
                { opacity: pressed ? 0.68 : 1 },
              ]}
            >
              <Feather name="settings" size={20} color={theme.colors.text} />
            </Pressable>
          </View>
        </View>
      </SectionEntrance>

      <SectionEntrance index={1}>
        <View style={styles.header}>
          <Text variant="display" style={styles.hero}>
            Your care, clearly organised.
          </Text>
          <Text color="muted" style={styles.hero}>
            Continue where you left off or see what is coming up next.
          </Text>
        </View>
      </SectionEntrance>

      {home.isLoading ? (
        <SectionEntrance index={2}>
          <Card style={styles.empty}>
            <LoadingIndicator />
            <Text variant="caption" color="muted">
              Preparing your home…
            </Text>
          </Card>
        </SectionEntrance>
      ) : null}

      {home.isError ? (
        <SectionEntrance index={2}>
          <Card style={styles.card}>
            <Text variant="heading">Home couldn’t refresh.</Text>
            <Text color="muted">
              The app opened, but the backend did not answer this request.
            </Text>
            <Button variant="secondary" onPress={() => home.refetch()}>
              Try again
            </Button>
          </Card>
        </SectionEntrance>
      ) : null}

      {home.isSuccess ? (
        <SectionEntrance index={2}>
          <Card style={styles.nextCard}>
            <View style={styles.nextIcon}>
              <Feather
                name={
                  nextAppointment
                    ? "calendar"
                    : consultationStep
                      ? "arrow-right"
                      : "message-circle"
                }
                size={theme.iconSize.md}
                color={theme.colors.primary}
              />
            </View>
            <View style={{ gap: theme.spacing.xs }}>
              <Text variant="caption" color="primary">
                Continue
              </Text>
              <Text variant="heading">
                {nextAppointment
                  ? nextAppointment.service_name
                  : consultationStep?.title || "Start with a consultation"}
              </Text>
              <Text color="muted">
                {nextAppointment
                  ? `${appointmentTime(nextAppointment.starts_at)} · ${nextAppointment.status_label}`
                  : consultationStep?.body ||
                    "Choose the service that matches your concerns and complete the intake at your own pace."}
              </Text>
            </View>
            <Button
              onPress={() =>
                router.push(
                  nextAppointment
                    ? (`/appointments/${nextAppointment.public_id}` as Href)
                    : consultationStep?.href || ("/consult" as Href),
                )
              }
            >
              {nextAppointment
                ? "View appointment"
                : consultationStep?.label || "View consultations"}
            </Button>
          </Card>
        </SectionEntrance>
      ) : null}

      {home.isSuccess ? (
        <SectionEntrance index={3}>
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text variant="caption" color="primary">
                CONSULTATIONS
              </Text>
              <Text variant="heading">Choose your starting point</Text>
              <Text variant="caption" color="muted">
                These services, durations, and prices come directly from HairDoc
                TK.
              </Text>
            </View>
            {home.data.services.length ? (
              <>
                <View style={styles.serviceGrid}>
                  {home.data.services.slice(0, 4).map((service) => (
                    <ServicePreview
                      key={service.public_id}
                      service={service}
                      wide={wide}
                      onPress={() =>
                        router.push({
                          pathname: "/consult/[serviceId]",
                          params: { serviceId: service.public_id },
                        })
                      }
                    />
                  ))}
                </View>
                <Button
                  variant="secondary"
                  onPress={() => router.push("/consult" as Href)}
                >
                  View all consultations
                </Button>
              </>
            ) : (
              <Card style={styles.empty}>
                <Feather
                  name="calendar"
                  size={30}
                  color={theme.colors.textMuted}
                />
                <Text variant="bodyStrong">
                  No consultations are available right now.
                </Text>
                <Text
                  variant="caption"
                  color="muted"
                  style={{ textAlign: "center" }}
                >
                  Please check again later or contact TK for availability.
                </Text>
              </Card>
            )}
          </View>
        </SectionEntrance>
      ) : null}

      <SectionEntrance index={4}>
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text variant="heading">More for you</Text>
            <Text variant="caption" color="muted">
              Details and payments that support your care.
            </Text>
          </View>
          <View style={styles.actions}>
            <QuickAction
              wide={false}
              icon="clipboard"
              label="Care plans"
              description="Guidance from TK"
              onPress={() => router.push("/plans" as Href)}
            />
            <QuickAction
              wide={false}
              icon="trending-up"
              label="Progress"
              description="Check-ins and feedback"
              onPress={() => router.push("/progress" as Href)}
            />
            <QuickAction
              wide={false}
              icon="credit-card"
              label="Payments"
              description="Checkout and receipts"
              onPress={() => router.push("/payments" as Href)}
            />
            <QuickAction
              wide={false}
              icon="user"
              label="Hair profile"
              description="History and concerns"
              onPress={() => router.push("/settings/hair-profile" as Href)}
            />
          </View>
        </View>
      </SectionEntrance>

      {home.data?.content.length ? (
        <SectionEntrance index={6}>
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text variant="heading">From TK</Text>
              <Text variant="caption" color="muted">
                Published talks, resources, and hair care.
              </Text>
            </View>
            <View style={styles.contentRow}>
              {home.data.content.map((item) => (
                <Card key={item.public_id} style={styles.card}>
                  <Text variant="caption" color="accent">
                    {typeLabel[item.type]}
                  </Text>
                  <Text variant="heading">{item.title}</Text>
                  <Text color="muted">{item.summary}</Text>
                  {item.external_url ? (
                    <Button
                      variant="secondary"
                      onPress={() => Linking.openURL(item.external_url)}
                    >
                      Open
                    </Button>
                  ) : null}
                </Card>
              ))}
            </View>
          </View>
        </SectionEntrance>
      ) : null}
    </Screen>
  );
}
