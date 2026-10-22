const GOOGLE_SIGN_IN = "https://accounts.google.com";

export function contentSecurityPolicy(development: boolean): string {
  const script = [
    "'self'",
    "'unsafe-inline'",
    ...(development ? ["'unsafe-eval'"] : []),
  ];
  const connect = ["'self'", ...(development ? ["ws:"] : [])];
  return [
    "default-src 'self'",
    `script-src ${script.join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src ${connect.join(" ")}`,
    "frame-ancestors 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    `form-action 'self' ${GOOGLE_SIGN_IN}`,
  ].join("; ");
}

export function securityHeaders(
  development: boolean,
): { key: string; value: string }[] {
  return [
    {
      key: "Content-Security-Policy",
      value: contentSecurityPolicy(development),
    },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    {
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=()",
    },
  ];
}
