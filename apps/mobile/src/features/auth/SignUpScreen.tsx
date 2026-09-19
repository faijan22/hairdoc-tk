import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Pressable, TextInput, View } from "react-native";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { getApiErrorMessage } from "./errors";
import { applyApiFieldErrors, applyZodErrors } from "./formUtils";

import { Button, Text, TextField } from "@/components/ui";
import { register } from "@/services/api/auth";
import { useTheme } from "@/theme/ThemeProvider";

const schema = z
  .object({
    first_name: z.string().trim().max(150),
    email: z.string().trim().email("Enter a valid email address."),
    password: z.string().min(8, "Use at least 8 characters.").max(128),
    confirm_password: z.string(),
  })
  .refine((value) => value.password === value.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  });
type Values = z.infer<typeof schema>;

export function SignUpScreen() {
  const router = useRouter();
  const theme = useTheme();
  const emailRef = useRef<TextInput>(null);
  const passwordRef = useRef<TextInput>(null);
  const confirmPasswordRef = useRef<TextInput>(null);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPasswordVisible, setConfirmPasswordVisible] = useState(false);
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    defaultValues: {
      first_name: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    const report = (field: string, message: string) =>
      setError(field as keyof Values, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      const response = await register(parsed.data);
      router.push({
        pathname: "/auth/verify-email",
        params: {
          email: parsed.data.email,
          token: response.debug_verification_token || "",
        },
      });
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });

  return (
    <AuthShell
      eyebrow="New account"
      title="Create your account"
      description="Use your email to get started. You can add consultation details later."
    >
      <Controller
        control={control}
        name="first_name"
        render={({ field }) => (
          <TextField
            label="First name (optional)"
            autoComplete="name-given"
            returnKeyType="next"
            onSubmitEditing={() => emailRef.current?.focus()}
            value={field.value}
            onBlur={field.onBlur}
            onChangeText={field.onChange}
            error={errors.first_name?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="email"
        render={({ field }) => (
          <TextField
            ref={emailRef}
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
            autoComplete="new-password"
            secureTextEntry={!passwordVisible}
            returnKeyType="next"
            onSubmitEditing={() => confirmPasswordRef.current?.focus()}
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
                onPress={() => setPasswordVisible((visible) => !visible)}
                style={({ pressed }) => ({
                  width: 40,
                  height: 40,
                  alignItems: "center",
                  justifyContent: "center",
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
      <Controller
        control={control}
        name="confirm_password"
        render={({ field }) => (
          <TextField
            ref={confirmPasswordRef}
            label="Confirm password"
            autoCapitalize="none"
            autoComplete="new-password"
            secureTextEntry={!confirmPasswordVisible}
            returnKeyType="go"
            onSubmitEditing={() => void submit()}
            value={field.value}
            onBlur={field.onBlur}
            onChangeText={field.onChange}
            error={errors.confirm_password?.message}
            endAdornment={
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={
                  confirmPasswordVisible ? "Hide password" : "Show password"
                }
                onPress={() => setConfirmPasswordVisible((visible) => !visible)}
                style={({ pressed }) => ({
                  width: 40,
                  height: 40,
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: pressed ? 0.6 : 1,
                })}
              >
                <Feather
                  name={confirmPasswordVisible ? "eye-off" : "eye"}
                  size={theme.iconSize.sm}
                  color={theme.colors.textMuted}
                />
              </Pressable>
            }
          />
        )}
      />
      {errors.root?.message ? (
        <Text variant="caption" color="danger">
          {errors.root.message}
        </Text>
      ) : null}
      <Button loading={isSubmitting} onPress={submit}>
        Create account
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
          Already have an account?
        </Text>
        <Pressable
          accessibilityRole="link"
          hitSlop={8}
          onPress={() => router.replace("/auth/sign-in")}
        >
          <Text variant="caption" color="primary">
            Sign in
          </Text>
        </Pressable>
      </View>
    </AuthShell>
  );
}
