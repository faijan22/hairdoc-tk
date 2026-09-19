let refreshToken: string | null = null;

export async function readRefreshToken(): Promise<string | null> {
  return refreshToken;
}

export async function writeRefreshToken(token: string): Promise<void> {
  refreshToken = token;
}

export async function clearRefreshToken(): Promise<void> {
  refreshToken = null;
}
