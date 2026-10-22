import type { MetadataRoute } from "next";

import { CRAWL_DISALLOWED } from "@/lib/site";
import { siteUrl } from "@/lib/site-url";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: CRAWL_DISALLOWED },
    sitemap: new URL("/sitemap.xml", siteUrl()).toString(),
  };
}
