// The access token lives only in memory (this module-level variable), never
// localStorage -- same reasoning as the sibling readiness-tracker project.
// Session persistence across reloads comes from the httpOnly refresh
// cookie instead (see lib/auth.tsx).
let currentToken: string | null = null;

export function getAccessToken(): string | null {
  return currentToken;
}

export function setAccessToken(token: string | null): void {
  currentToken = token;
}
