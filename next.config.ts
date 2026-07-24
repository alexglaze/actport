import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static portfolio: local images in /public need no `images` config,
  // Tailwind v4 is PostCSS-driven, and Turbopack is the v16 default.
  // `typedRoutes` gives compile-time checking of <Link href> values.
  typedRoutes: true,
};

export default nextConfig;
