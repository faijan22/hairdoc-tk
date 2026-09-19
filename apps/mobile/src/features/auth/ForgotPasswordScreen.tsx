import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { getApiErrorMessage } from "./errors";

import { Button, Text, TextField } from "@/components/ui";
import { forgotPassword } from "@/services/api/auth";

const schema = z.object({ email: z.string().trim().email("Enter a valid email address.") });
type Values = z.infer<typeof schema>;

export function ForgotPasswordScreen() {
  const router = useRouter();
  const { control, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Values>({ defaultValues: { email: "" } });
  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    if (!parsed.success) return setError("email", { message: parsed.error.issues[0].message });
    try {
      const response = await forgotPassword(parsed.data.email);
      router.push({ pathname: "/auth/reset-password", params: { token: response.debug_reset_token || "" } });
    } catch (error) {
      setError("root", { message: getApiErrorMessage(error) });
    }
  });

  return (
    <AuthShell eyebrow="Account recovery" title="Reset your password" description="Enter your email and we’ll send a one-time reset link if the account is eligible.">
      <Controller control={control} name="email" render={({ field }) => (
        <TextField label="Email" autoCapitalize="none" autoComplete="email" keyboardType="email-address" value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.email?.message} />
      )} />
      {errors.root?.message ? <Text variant="caption" color="danger">{errors.root.message}</Text> : null}
      <Button loading={isSubmitting} onPress={submit}>Send reset link</Button>
    </AuthShell>
  );
}
