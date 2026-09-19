import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { getApiErrorMessage } from "./errors";

import { Button, Text, TextField } from "@/components/ui";
import { resendVerification, verifyEmail } from "@/services/api/auth";

const schema = z.object({ token: z.string().trim().min(1, "Paste the verification token.") });
type Values = z.infer<typeof schema>;

function firstParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

export function VerifyEmailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string | string[]; token?: string | string[] }>();
  const email = firstParam(params.email);
  const [resending, setResending] = useState(false);
  const [notice, setNotice] = useState("Check your email for the one-time verification link or token.");
  const { control, handleSubmit, setError, setValue, formState: { errors, isSubmitting } } = useForm<Values>({
    defaultValues: { token: firstParam(params.token) },
  });

  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    if (!parsed.success) return setError("token", { message: parsed.error.issues[0].message });
    try {
      await verifyEmail(parsed.data.token);
      router.replace("/auth/sign-in");
    } catch (error) {
      setError("token", { message: getApiErrorMessage(error) });
    }
  });

  const resend = async () => {
    if (!email) return setError("root", { message: "Return to sign up and enter your email again." });
    setResending(true);
    try {
      const response = await resendVerification(email);
      if (response.debug_verification_token) setValue("token", response.debug_verification_token);
      setNotice(response.message);
    } catch (error) {
      setError("root", { message: getApiErrorMessage(error) });
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthShell eyebrow="Email verification" title="Verify your email" description={notice}>
      <Controller control={control} name="token" render={({ field }) => (
        <TextField label="Verification token" autoCapitalize="none" value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.token?.message} />
      )} />
      {errors.root?.message ? <Text variant="caption" color="danger">{errors.root.message}</Text> : null}
      <Button loading={isSubmitting} onPress={submit}>Verify email</Button>
      <Button variant="ghost" loading={resending} onPress={resend}>Send a new token</Button>
    </AuthShell>
  );
}
