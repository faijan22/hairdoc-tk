import { Redirect, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { AuthShell } from "./AuthShell";
import { useAuthStore } from "./authStore";
import { getApiErrorMessage } from "./errors";
import { applyApiFieldErrors, applyZodErrors } from "./formUtils";

import { Button, LoadingIndicator, Text, TextField } from "@/components/ui";
import { changePassword } from "@/services/api/auth";

const schema = z.object({
  current_password: z.string().min(1, "Enter your current password."),
  new_password: z.string().min(8, "Use at least 8 characters.").max(128),
  confirm_password: z.string(),
}).refine((value) => value.new_password === value.confirm_password, {
  path: ["confirm_password"], message: "Passwords do not match.",
});
type Values = z.infer<typeof schema>;

export function ChangePasswordScreen() {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);
  const signOut = useAuthStore((state) => state.signOut);
  const { control, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Values>({
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });
  if (status === "bootstrapping") return <LoadingIndicator />;
  if (status === "anonymous") return <Redirect href="/auth/sign-in" />;

  const submit = handleSubmit(async (values) => {
    const parsed = schema.safeParse(values);
    const report = (field: string, message: string) => setError(field as keyof Values, { message });
    if (!parsed.success) return applyZodErrors(parsed.error, report);
    try {
      await changePassword(parsed.data.current_password, parsed.data.new_password);
      await signOut();
      router.replace("/auth/sign-in");
    } catch (error) {
      applyApiFieldErrors(error, report);
      setError("root", { message: getApiErrorMessage(error) });
    }
  });

  return (
    <AuthShell eyebrow="Account security" title="Change your password" description="After this change, every device will need to sign in again.">
      <Controller control={control} name="current_password" render={({ field }) => (
        <TextField label="Current password" autoComplete="current-password" secureTextEntry value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.current_password?.message} />
      )} />
      <Controller control={control} name="new_password" render={({ field }) => (
        <TextField label="New password" autoComplete="new-password" secureTextEntry value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.new_password?.message} />
      )} />
      <Controller control={control} name="confirm_password" render={({ field }) => (
        <TextField label="Confirm new password" autoComplete="new-password" secureTextEntry value={field.value} onBlur={field.onBlur} onChangeText={field.onChange} error={errors.confirm_password?.message} />
      )} />
      {errors.root?.message ? <Text variant="caption" color="danger">{errors.root.message}</Text> : null}
      <Button loading={isSubmitting} onPress={() => void submit()}>Change password</Button>
    </AuthShell>
  );
}
