const DEFAULT_SITE_URL = "http://localhost:3000";
const WEB_PROTOCOLS = new Set(["http:", "https:"]);

export function siteUrl(): URL {
  const given =
    process.env.SITE_URL ||
    (process.env.NODE_ENV === "production" ? "" : DEFAULT_SITE_URL);
  if (!given) {
    throw new Error(
      "本番のビルドと起動には SITE_URL(https://example.com のようなオリジン)が要ります",
    );
  }
  let url: URL;
  try {
    url = new URL(given);
  } catch {
    throw new Error(
      `SITE_URL を https://example.com のような URL にしてください: ${given}`,
    );
  }
  if (!WEB_PROTOCOLS.has(url.protocol)) {
    throw new Error(
      `SITE_URL は http:// か https:// で始めてください: ${given}`,
    );
  }
  if (url.pathname !== "/" || url.search || url.hash) {
    throw new Error(`SITE_URL にはパスを含めないでください: ${given}`);
  }
  return url;
}
