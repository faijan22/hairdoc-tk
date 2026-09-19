import { z } from "zod";

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

const userSchema = z.object({
  public_id: z.string().uuid(),
  email: z.string().email(),
  first_name: z.string(),
  last_name: z.string(),
  // Older local sessions may briefly receive a pre-profile API payload while
  // Metro/Expo Go refreshes. Missing optional profile data is safely empty.
  phone: z
    .string()
    .optional()
    .transform((value) => value ?? ""),
  is_email_verified: z.boolean(),
  is_staff: z
    .boolean()
    .optional()
    .transform((value) => value ?? false),
});

const tokenResponseSchema = z.object({
  access_token: z.string(),
  // Native receives the opaque token for SecureStore. Web rotates it only in
  // an HTTP-only cookie, so browser JavaScript never reads it.
  refresh_token: z.string().optional(),
  token_type: z.literal("Bearer"),
  expires_in: z.number().positive(),
  user: userSchema,
});

const registerResponseSchema = z.object({
  message: z.string(),
  debug_verification_token: z.string().optional(),
});

const recoveryResponseSchema = z.object({
  message: z.string(),
  debug_reset_token: z.string().optional(),
  debug_verification_token: z.string().optional(),
});

const sessionSchema = z.object({
  public_id: z.string().uuid(),
  device_name: z.string(),
  created_at: z.string(),
  last_used_at: z.string(),
  expires_at: z.string(),
  is_current: z.boolean(),
});

export type AuthUser = z.infer<typeof userSchema>;
export type AuthTokenResponse = z.infer<typeof tokenResponseSchema>;
export type DeviceSession = z.infer<typeof sessionSchema>;

export async function register(input: {
  email: string;
  password: string;
  first_name?: string;
}) {
  return registerResponseSchema.parse(
    await apiPost<unknown>("/auth/register/", input, false),
  );
}

export async function verifyEmail(token: string) {
  return userSchema.parse(
    (await apiPost<{ user: unknown }>("/auth/email/verify/", { token }, false))
      .user,
  );
}

export async function resendVerification(email: string) {
  return recoveryResponseSchema.parse(
    await apiPost<unknown>("/auth/email/resend/", { email }, false),
  );
}

export async function login(input: {
  email: string;
  password: string;
  device_name: string;
}) {
  return tokenResponseSchema.parse(
    await apiPost<unknown>("/auth/login/", input, false),
  );
}

export async function refreshSession(refreshToken?: string | null) {
  return tokenResponseSchema.parse(
    await apiPost<unknown>(
      "/auth/refresh/",
      refreshToken ? { refresh_token: refreshToken } : {},
      false,
    ),
  );
}

export async function logout(refreshToken?: string | null) {
  await apiPost<void>(
    "/auth/logout/",
    refreshToken ? { refresh_token: refreshToken } : {},
    false,
  );
}

export async function forgotPassword(email: string) {
  return recoveryResponseSchema.parse(
    await apiPost<unknown>("/auth/password/forgot/", { email }, false),
  );
}

export async function resetPassword(token: string, newPassword: string) {
  await apiPost(
    "/auth/password/reset/",
    { token, new_password: newPassword },
    false,
  );
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
) {
  await apiPost("/auth/password/change/", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export async function getMe() {
  return userSchema.parse(await apiGet<unknown>("/me/"));
}

export async function updateMe(input: {
  first_name: string;
  last_name: string;
  phone: string;
}) {
  return userSchema.parse(await apiPatch<unknown>("/me/", input));
}

export async function getSessions() {
  return z.array(sessionSchema).parse(await apiGet<unknown>("/me/sessions/"));
}

export async function revokeSession(publicId: string) {
  await apiDelete(`/me/sessions/${publicId}/`);
}

export async function logoutAll() {
  await apiPost<void>("/auth/logout-all/");
}

export async function deleteAccount(
  currentPassword: string,
  confirmation: string,
) {
  await apiPost<void>("/me/account/delete/", {
    current_password: currentPassword,
    confirmation,
  });
}
