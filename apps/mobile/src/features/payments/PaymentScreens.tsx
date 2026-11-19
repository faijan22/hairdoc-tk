import Feather from "@expo/vector-icons/Feather";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { AppState, Linking, Pressable, View } from "react-native";

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
import {
  createCheckout,
  createOrder,
  getPayment,
  getPayments,
  getStaffPayment,
  getStaffPayments,
  Payment,
  refreshPayment,
  StaffPayment,
} from "@/services/api/payments";
import { useTheme } from "@/theme/ThemeProvider";

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

function appointmentTime(value: string) {
  return new Date(value).toLocaleString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isStaffPayment(payment: Payment | StaffPayment): payment is StaffPayment {
  return "client_name" in payment && typeof payment.client_name === "string";
}

function Guard({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status !== "authenticated") return <Redirect href="/auth/sign-in" />;
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
        SECURE PAYMENT
      </Text>
      <Text variant="title">{title}</Text>
    </View>
  );
}

function statusTone(
  status: Payment["status"],
): "primary" | "accent" | "muted" | "danger" {
  if (status === "SUCCEEDED" || status === "REFUNDED") return "primary";
  if (
    status === "PROCESSING" ||
    status === "REFUND_PENDING" ||
    status === "PARTIALLY_REFUNDED"
  )
    return "accent";
  if (status === "FAILED" || status === "CANCELLED") return "danger";
  return "muted";
}

function StatusCard({
  payment,
  onCheck,
  checking = false,
}: {
  payment: Payment;
  onCheck?: () => void;
  checking?: boolean;
}) {
  const theme = useTheme();
  const router = useRouter();
  const paid = payment.status === "SUCCEEDED";
  const pending =
    payment.status === "PROCESSING" || payment.status === "CREATED";
  const refundPending =
    payment.status === "REFUND_PENDING" ||
    payment.status === "PARTIALLY_REFUNDED";
  return (
    <Card style={{ gap: theme.spacing.md, alignItems: "flex-start" }}>
      <View
        style={{
          width: 44,
          height: 44,
          borderRadius: 22,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: paid
            ? theme.colors.primaryMuted
            : pending || refundPending
              ? theme.colors.accentMuted
              : theme.colors.surfaceMuted,
        }}
      >
        <Feather
          name={
            paid ? "check" : pending || refundPending ? "clock" : "alert-circle"
          }
          size={theme.iconSize.md}
          color={
            paid
              ? theme.colors.primary
              : pending || refundPending
                ? theme.colors.accent
                : theme.colors.danger
          }
        />
      </View>
      <View style={{ gap: theme.spacing.xs }}>
        <Text variant="overline" color={statusTone(payment.status)}>
          {payment.status_label}
        </Text>
        <Text variant="heading">
          {paid
            ? "Your appointment is confirmed."
            : pending
              ? "Waiting for Stripe confirmation."
              : refundPending
                ? "Refund review is in progress."
                : "Payment was not completed."}
        </Text>
        <Text color="muted">
          {payment.failure_message ||
            (pending
              ? "This updates only after HairDoc TK receives Stripe's signed confirmation. It can take a few moments."
              : paid
                ? "Your receipt and appointment details are ready."
                : refundPending
                  ? "TK can review the refund state without exposing your card details."
                  : "You can retry checkout while the appointment reservation remains active.")}
        </Text>
      </View>
      {onCheck && pending ? (
        <Button variant="secondary" loading={checking} onPress={onCheck}>
          Check payment status
        </Button>
      ) : null}
      {paid ? (
        <Button
          onPress={() =>
            router.replace(
              `/appointments/${payment.appointment_public_id}` as Href,
            )
          }
        >
          View confirmed appointment
        </Button>
      ) : null}
    </Card>
  );
}

export function CheckoutScreen() {
  const { appointmentId } = useLocalSearchParams<{ appointmentId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [paymentId, setPaymentId] = useState<string>();
  const [browserOpened, setBrowserOpened] = useState(false);
  const order = useMutation({ mutationFn: () => createOrder(appointmentId) });
  const payment = useQuery({
    queryKey: ["payments", paymentId],
    queryFn: () => getPayment(paymentId!),
    enabled: Boolean(paymentId),
  });
  const refresh = useMutation({
    mutationFn: () => refreshPayment(paymentId!),
    onSuccess: (updated) => {
      queryClient.setQueryData(["payments", paymentId], updated);
      void queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
  const refreshStatus = refresh.mutate;
  const checkout = useMutation({
    mutationFn: async () => {
      const activeOrder = order.data || (await order.mutateAsync());
      const result = await createCheckout(activeOrder.public_id);
      setPaymentId(result.payment.public_id);
      setBrowserOpened(true);
      await Linking.openURL(result.checkout_url);
      return result;
    },
  });
  const prepareOrder = order.mutate;
  useEffect(() => {
    if (appointmentId && !order.data && !order.isPending && !order.isError)
      prepareOrder();
  }, [appointmentId, order.data, order.isPending, order.isError, prepareOrder]);
  useEffect(() => {
    if (order.data?.payment_public_id) {
      // Existing server checkout state seeds the local polling target.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPaymentId(order.data.payment_public_id);
    }
  }, [order.data?.payment_public_id]);
  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && paymentId) {
        refreshStatus();
      }
    });
    return () => subscription.remove();
  }, [paymentId, refreshStatus]);
  useEffect(() => {
    if (
      payment.data &&
      !["CREATED", "PROCESSING"].includes(payment.data.status)
    ) {
      // A terminal provider state ends this external polling session.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBrowserOpened(false);
    }
  }, [payment.data]);
  if (!appointmentId) return <Redirect href="/appointments" />;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Checkout" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">Confirm, then pay securely.</Text>
          <Text color="muted">
            Your appointment and price come directly from HairDoc TK. Card
            details are entered on Stripe&apos;s hosted page.
          </Text>
        </View>
        {order.isPending ? <LoadingIndicator /> : null}
        {order.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Checkout is not available.</Text>
            <Text color="danger">{getApiErrorMessage(order.error)}</Text>
            <Button onPress={() => order.mutate()}>Try again</Button>
            <Button
              variant="ghost"
              onPress={() =>
                router.replace(`/appointments/${appointmentId}` as Href)
              }
            >
              View appointment
            </Button>
          </Card>
        ) : null}
        {order.data ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="overline" color="accent">
              APPOINTMENT HOLD
            </Text>
            <Text variant="title">{order.data.service_name}</Text>
            <Text color="muted">
              {appointmentTime(order.data.appointment_starts_at)}
            </Text>
            <Divider />
            <View
              style={{
                flexDirection: "row",
                justifyContent: "space-between",
                gap: theme.spacing.md,
              }}
            >
              <Text color="muted">Total</Text>
              <Text variant="heading">
                {money(order.data.total_amount, order.data.currency)}
              </Text>
            </View>
          </Card>
        ) : null}
        {payment.data ? (
          <StatusCard
            payment={payment.data}
            checking={refresh.isPending}
            onCheck={() => refreshStatus()}
          />
        ) : null}
        {refresh.isError ? (
          <Text color="danger">{getApiErrorMessage(refresh.error)}</Text>
        ) : null}
        {payment.isError ? (
          <Card style={{ gap: theme.spacing.sm }}>
            <Text variant="bodyStrong">Payment status could not refresh.</Text>
            <Text color="danger">{getApiErrorMessage(payment.error)}</Text>
            <Button
              variant="secondary"
              onPress={() => {
                void payment.refetch().catch(() => undefined);
              }}
            >
              Try again
            </Button>
          </Card>
        ) : null}
        {order.data && payment.data?.status !== "SUCCEEDED" ? (
          <Card style={{ gap: theme.spacing.md }}>
            <View
              style={{
                flexDirection: "row",
                gap: theme.spacing.sm,
                alignItems: "center",
              }}
            >
              <Feather
                name="shield"
                size={theme.iconSize.md}
                color={theme.colors.primary}
              />
              <View style={{ flex: 1 }}>
                <Text variant="bodyStrong">Stripe secure checkout</Text>
                <Text variant="caption" color="muted">
                  HairDoc TK never receives or stores your card number.
                </Text>
              </View>
            </View>
            {checkout.isError ? (
              <Text color="danger">{getApiErrorMessage(checkout.error)}</Text>
            ) : null}
            <Button
              loading={checkout.isPending}
              onPress={() => checkout.mutate()}
            >
              {browserOpened
                ? "Return to secure checkout"
                : `Pay ${money(order.data.total_amount, order.data.currency)}`}
            </Button>
            <Text
              variant="caption"
              color="muted"
              style={{ textAlign: "center" }}
            >
              Your booking becomes confirmed only after Stripe verifies the
              payment.
            </Text>
          </Card>
        ) : null}
      </Screen>
    </Guard>
  );
}

export function PaymentHistoryScreen() {
  const theme = useTheme();
  const router = useRouter();
  const isStaff = useAuthStore((state) => Boolean(state.user?.is_staff));
  const payments = useQuery({
    queryKey: ["payments", isStaff ? "staff" : "client"],
    queryFn: isStaff ? getStaffPayments : getPayments,
  });
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Payments" />
        <View style={{ gap: theme.spacing.xs }}>
          <Text variant="display">
            {isStaff ? "Client payments." : "Receipts and payment status."}
          </Text>
          <Text color="muted">
            {isStaff
              ? "Payments for appointments assigned to you, directly from the backend."
              : "Only payments created for your consultation appointments appear here."}
          </Text>
        </View>
        {payments.isLoading ? <LoadingIndicator /> : null}
        {payments.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Payments could not load.</Text>
            <Text color="danger">{getApiErrorMessage(payments.error)}</Text>
            <Button
              onPress={() => {
                void payments.refetch().catch(() => undefined);
              }}
            >
              Try again
            </Button>
          </Card>
        ) : null}
        {payments.isSuccess && !payments.data.length ? (
          <Card style={{ alignItems: "center", gap: theme.spacing.sm }}>
            <Feather
              name="credit-card"
              size={30}
              color={theme.colors.textMuted}
            />
            <Text variant="heading">No payments yet.</Text>
            <Text color="muted" style={{ textAlign: "center" }}>
              {isStaff
                ? "Paid consultation activity will appear here. Free appointments do not create payment records."
                : "Payments appear after you reserve an appointment and open secure checkout."}
            </Text>
            {!isStaff ? (
              <Button onPress={() => router.push("/consult" as Href)}>
                View consultations
              </Button>
            ) : null}
          </Card>
        ) : null}
        <View style={{ gap: theme.spacing.md }}>
          {payments.data?.map((item) => (
            <Card key={item.public_id} style={{ gap: theme.spacing.md }}>
              <View style={{ gap: theme.spacing.xs }}>
                <Text variant="overline" color={statusTone(item.status)}>
                  {item.status_label}
                </Text>
                <Text variant="heading">{item.service_name}</Text>
                {isStaffPayment(item) ? (
                  <Text variant="bodyStrong">{item.client_name}</Text>
                ) : null}
                <Text color="muted">
                  {appointmentTime(item.appointment_starts_at)}
                </Text>
                <Text variant="bodyStrong">
                  {money(item.amount, item.currency)}
                </Text>
              </View>
              <Button
                variant="secondary"
                onPress={() =>
                  router.push(`/payments/${item.public_id}` as Href)
                }
              >
                View details
              </Button>
            </Card>
          ))}
        </View>
      </Screen>
    </Guard>
  );
}

export function PaymentDetailScreen() {
  const { paymentId } = useLocalSearchParams<{ paymentId: string }>();
  const theme = useTheme();
  const queryClient = useQueryClient();
  const isStaff = useAuthStore((state) => Boolean(state.user?.is_staff));
  const detailKey = ["payments", isStaff ? "staff" : "client", paymentId];
  const item = useQuery({
    queryKey: detailKey,
    queryFn: () =>
      isStaff ? getStaffPayment(paymentId) : getPayment(paymentId),
    enabled: Boolean(paymentId),
  });
  const refresh = useMutation({
    mutationFn: () => refreshPayment(paymentId!),
    onSuccess: (updated) => {
      queryClient.setQueryData(detailKey, updated);
      void queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
  if (!paymentId) return <Redirect href={"/payments" as Href} />;
  return (
    <Guard>
      <Screen contentStyle={{ gap: theme.spacing.xl }}>
        <Header title="Payment details" />
        {item.isLoading ? <LoadingIndicator /> : null}
        {item.isError ? (
          <Card style={{ gap: theme.spacing.md }}>
            <Text variant="heading">Payment could not load.</Text>
            <Text color="danger">{getApiErrorMessage(item.error)}</Text>
            <Button
              onPress={() => {
                void item.refetch().catch(() => undefined);
              }}
            >
              Try again
            </Button>
          </Card>
        ) : null}
        {item.data ? (
          <>
            <StatusCard
              payment={item.data}
              checking={refresh.isPending}
              onCheck={isStaff ? undefined : () => refresh.mutate()}
            />
            {refresh.isError ? (
              <Text color="danger">{getApiErrorMessage(refresh.error)}</Text>
            ) : null}
            <Card style={{ gap: theme.spacing.md }}>
              <Text variant="overline" color="accent">
                RECEIPT
              </Text>
              <Text variant="title">{item.data.service_name}</Text>
              {isStaffPayment(item.data) ? (
                <View style={{ gap: 2 }}>
                  <Text variant="caption" color="muted">Client</Text>
                  <Text variant="bodyStrong">{item.data.client_name}</Text>
                  <Text color="muted">{item.data.client_email}</Text>
                </View>
              ) : null}
              <View style={{ gap: theme.spacing.sm }}>
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                  }}
                >
                  <Text color="muted">Amount</Text>
                  <Text variant="bodyStrong">
                    {money(item.data.amount, item.data.currency)}
                  </Text>
                </View>
                <Divider />
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                  }}
                >
                  <Text color="muted">Reference</Text>
                  <Text variant="bodyStrong">{item.data.receipt_number}</Text>
                </View>
                <Divider />
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                  }}
                >
                  <Text color="muted">Provider</Text>
                  <Text variant="bodyStrong">
                    {item.data.provider === "STRIPE"
                      ? "Stripe"
                      : item.data.provider}
                  </Text>
                </View>
                <Divider />
                <Text variant="caption" color="muted">
                  Appointment
                </Text>
                <Text>{appointmentTime(item.data.appointment_starts_at)}</Text>
                {item.data.paid_at ? (
                  <>
                    <Text variant="caption" color="muted">
                      Paid
                    </Text>
                    <Text>{new Date(item.data.paid_at).toLocaleString()}</Text>
                  </>
                ) : null}
              </View>
            </Card>
            {item.data.refunds.map((refund) => (
              <Card key={refund.public_id} style={{ gap: theme.spacing.xs }}>
                <Text variant="overline" color="accent">
                  {refund.status_label}
                </Text>
                <Text variant="heading">
                  {money(refund.amount, refund.currency)}
                </Text>
                <Text color="muted">{refund.reason}</Text>
              </Card>
            ))}
          </>
        ) : null}
      </Screen>
    </Guard>
  );
}
