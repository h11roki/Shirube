import type { MetadataRoute } from "next";

import { PUBLIC_PAGES } from "@/lib/site";
import { siteUrl } from "@/lib/site-url";

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PAGES.map((path) => ({
    url: new URL(path, siteUrl()).toString(),
  }));
}
