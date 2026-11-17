import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { getApiErrorMessage } from "./errors";
import { applyApiFieldErrors, applyZodErrors } from "./formUtils";

import { Button, Text, TextField } from "@/components/ui";
import { resetPassword } from "@/services/api/auth";

const schema = z.object({
  token: z.string().trim().min(1, "Paste the reset token."),
  new_password: z.string().min(8, "Use at least 8 characters.").max(128),
  confirm_password: z.string(),
}).refine((value) => value.new_password === value.confirm_password, {
  path: ["confirm_password"], message: "Passwords do not match.",
});
type Values = z.infer<typeof schema>;

export function ResetPasswordScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const token = Array.isArray(params.token) ? params.token[0] || "" : params.token || "";
  const { control, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Values>({
    defaultValues: { token, new_password: "", confirm_password: "" },
  });
  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    const report = (field: string, message: string) => setError(field as keyof Values, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      await resetPassword(parsed.data.token, parsed.data.new_password);
      router.replace("/auth/sign-in");
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });

  return (
    <AuthShell eyebrow="Account recovery" title="Choose a new password" description="The reset token works once and signs out your existing sessions.">
      <Controller control={control} name="token" render={({ field }) => (
        <TextField label="Reset token" autoCapitalize="none" value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.token?.message} />
      )} />
      <Controller control={control} name="new_password" render={({ field }) => (
        <TextField label="New password" autoComplete="new-password" secureTextEntry value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.new_password?.message} />
      )} />
      <Controller control={control} name="confirm_password" render={({ field }) => (
        <TextField label="Confirm new password" autoComplete="new-password" secureTextEntry value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.confirm_password?.message} />
      )} />
      {errors.root?.message ? <Text variant="caption" color="danger">{errors.root.message}</Text> : null}
      <Button loading={isSubmitting} onPress={() => void submit()}>Reset password</Button>
    </AuthShell>
  );
}
