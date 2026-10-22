const DEFAULT_SITE_URL = "http://localhost:3000";

export function siteUrl(): URL {
  const given = process.env.SITE_URL ?? DEFAULT_SITE_URL;
  let url: URL;
  try {
    url = new URL(given);
  } catch {
    throw new Error(
      `SITE_URL を https://example.com のような URL にしてください: ${given}`,
    );
  }
  if (url.pathname !== "/" || url.search || url.hash) {
    throw new Error(`SITE_URL にはパスを含めないでください: ${given}`);
  }
  return url;
}
