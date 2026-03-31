import { getConfig } from '../config';

const TOKEN_KEYS = {
  idToken: 'lmjm_id_token',
  accessToken: 'lmjm_access_token',
  refreshToken: 'lmjm_refresh_token',
} as const;

interface TokenResponse {
  id_token: string;
  access_token: string;
  refresh_token?: string;
}

/** Redirect the browser to the Cognito hosted UI authorize endpoint. */
export function login(): void {
  const { cognitoDomain, cognitoClientId, redirectUri } = getConfig();
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: cognitoClientId,
    redirect_uri: redirectUri,
    identity_provider: 'Google',
    scope: 'openid profile email',
  });
  window.location.href = `${cognitoDomain}/oauth2/authorize?${params.toString()}`;
}

/** Exchange an authorization code for tokens via the Cognito /oauth2/token endpoint. */
export async function handleCallback(code: string): Promise<TokenResponse> {
  const { cognitoDomain, cognitoClientId, redirectUri } = getConfig();
  const response = await fetch(`${cognitoDomain}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: cognitoClientId,
      redirect_uri: redirectUri,
      code,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to exchange authorization code for tokens');
  }

  const data: TokenResponse = await response.json();
  localStorage.setItem(TOKEN_KEYS.idToken, data.id_token);
  localStorage.setItem(TOKEN_KEYS.accessToken, data.access_token);
  if (data.refresh_token) {
    localStorage.setItem(TOKEN_KEYS.refreshToken, data.refresh_token);
  }
  return data;
}

/** Refresh the access token using the stored refresh token. Returns the new access token or null on failure. */
export async function refreshToken(): Promise<string | null> {
  const storedRefresh = localStorage.getItem(TOKEN_KEYS.refreshToken);
  if (!storedRefresh) return null;

  try {
    const { cognitoDomain, cognitoClientId } = getConfig();
    const response = await fetch(`${cognitoDomain}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: cognitoClientId,
        refresh_token: storedRefresh,
      }),
    });

    if (!response.ok) return null;

    const data: TokenResponse = await response.json();
    localStorage.setItem(TOKEN_KEYS.accessToken, data.access_token);
    if (data.id_token) {
      localStorage.setItem(TOKEN_KEYS.idToken, data.id_token);
    }
    return data.access_token;
  } catch {
    return null;
  }
}

/** Clear all stored tokens from localStorage. */
export function logout(): void {
  localStorage.removeItem(TOKEN_KEYS.idToken);
  localStorage.removeItem(TOKEN_KEYS.accessToken);
  localStorage.removeItem(TOKEN_KEYS.refreshToken);
}

/** Get the stored access token (may be expired). */
export function getStoredAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEYS.accessToken);
}

/** Get the stored ID token. */
export function getStoredIdToken(): string | null {
  return localStorage.getItem(TOKEN_KEYS.idToken);
}

/** Decode a JWT payload without verification (browser-side only). */
export function decodeJwtPayload(token: string): Record<string, unknown> {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
  );
  return JSON.parse(jsonPayload);
}

/** Check whether a JWT token is expired (with a 60-second buffer). */
export function isTokenExpired(token: string): boolean {
  try {
    const payload = decodeJwtPayload(token);
    const exp = payload.exp as number | undefined;
    if (!exp) return true;
    return Date.now() >= (exp - 60) * 1000;
  } catch {
    return true;
  }
}
