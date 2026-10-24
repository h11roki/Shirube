export const E2E_PORT = 3100;

export const E2E_ORIGIN = `http://localhost:${E2E_PORT}`;

export const E2E_AUTH_SECRET = "e2e-only-auth-secret-for-playwright-tests";

export const E2E_SERVER_ENV = {
  SITE_URL: E2E_ORIGIN,
  AUTH_SECRET: E2E_AUTH_SECRET,
  AUTH_TRUST_HOST: "true",
  AUTH_GOOGLE_ID: "e2e-google-id",
  AUTH_GOOGLE_SECRET: "e2e-google-secret",
  AUTH_JWT_SECRET: "e2e-only-jwt-secret-for-playwright-tests",
  BACKEND_URL: "http://127.0.0.1:9",
};
