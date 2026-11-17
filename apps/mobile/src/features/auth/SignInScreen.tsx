import { Feather } from "@expo/vector-icons";
import { Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Pressable, type TextInputInstance, View } from "react-native";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { useAuthStore } from "./authStore";
import { getApiErrorMessage } from "./errors";
import { applyApiFieldErrors, applyZodErrors } from "./formUtils";

import { Button, LoadingIndicator, Text, TextField } from "@/components/ui";
import { useTheme } from "@/theme/ThemeProvider";

const schema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});
type Values = z.infer<typeof schema>;

export function SignInScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ next?: string }>();
  const destination: Href =
    params.next === "/settings/delete-account"
      ? "/settings/delete-account"
      : "/explore";
  const theme = useTheme();
  const status = useAuthStore((state) => state.status);
  const signIn = useAuthStore((state) => state.signIn);
  const passwordRef = useRef<TextInputInstance>(null);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    defaultValues: { email: "", password: "" },
  });

  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status === "authenticated") return <Redirect href={destination} />;

  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    const report = (field: string, message: string) =>
      setError(field as keyof Values, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      await signIn(parsed.data.email, parsed.data.password);
      router.replace(destination);
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });

  return (
    <AuthShell
      eyebrow="Your account"
      title="Welcome back"
      description="Sign in to manage your consultations and care plan."
    >
      <Controller
        control={control}
        name="email"
        render={({ field }) => (
          <TextField
            label="Email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            returnKeyType="next"
            onSubmitEditing={() => passwordRef.current?.focus()}
            value={field.value}
            onBlur={field.onBlur}
            onChangeText={field.onChange}
            error={errors.email?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="password"
        render={({ field }) => (
          <TextField
            ref={passwordRef}
            label="Password"
            autoCapitalize="none"
            autoComplete="current-password"
            secureTextEntry={!passwordVisible}
            returnKeyType="go"
            onSubmitEditing={() => void submit()}
            value={field.value}
            onBlur={field.onBlur}
            onChangeText={field.onChange}
            error={errors.password?.message}
            endAdornment={
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={
                  passwordVisible ? "Hide password" : "Show password"
                }
                accessibilityState={{ expanded: passwordVisible }}
                hitSlop={6}
                onPress={() => setPasswordVisible((visible) => !visible)}
                style={({ pressed }) => ({
                  width: 40,
                  height: 40,
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: theme.radius.pill,
                  opacity: pressed ? 0.6 : 1,
                })}
              >
                <Feather
                  name={passwordVisible ? "eye-off" : "eye"}
                  size={theme.iconSize.sm}
                  color={theme.colors.textMuted}
                />
              </Pressable>
            }
          />
        )}
      />
      <Pressable
        accessibilityRole="link"
        hitSlop={8}
        onPress={() => router.push("/auth/forgot-password")}
        style={{
          minHeight: 36,
          alignSelf: "flex-end",
          justifyContent: "center",
        }}
      >
        <Text variant="caption" color="primary">
          Forgot password?
        </Text>
      </Pressable>
      {errors.root?.message ? (
        <Text variant="caption" color="danger">
          {errors.root.message}
        </Text>
      ) : null}
      <Button loading={isSubmitting} onPress={() => void submit()}>
        Sign in
      </Button>
      <View
        style={{
          minHeight: 44,
          flexDirection: "row",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "center",
          gap: theme.spacing.xs,
        }}
      >
        <Text variant="caption" color="muted">
          New to HairDoc TK?
        </Text>
        <Pressable
          accessibilityRole="link"
          hitSlop={8}
          onPress={() => router.push("/auth/sign-up")}
        >
          <Text variant="caption" color="primary">
            Create account
          </Text>
        </Pressable>
      </View>
    </AuthShell>
  );
}
