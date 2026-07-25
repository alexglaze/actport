import type { MetadataRoute } from "next";
import { searchIndexing, site } from "@/content/portfolio";

// Belt and braces alongside the `robots` meta tag in layout.tsx: the meta tag
// tells crawlers not to index, this tells them not to fetch in the first place.
export default function robots(): MetadataRoute.Robots {
  if (!searchIndexing) {
    return {
      rules: [{ userAgent: "*", disallow: "/" }],
    };
  }

  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: `${site.url}/sitemap.xml`,
  };
}
