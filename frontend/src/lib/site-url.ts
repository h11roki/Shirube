export function siteUrl(): URL {
  return new URL(process.env.SITE_URL ?? "http://localhost:3000");
}
