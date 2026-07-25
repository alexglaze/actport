import type { Metadata, Viewport } from "next";
import { Inter, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { identity, sameAs, searchIndexing, site } from "@/content/portfolio";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// Instrument Serif ships a single weight, so `weight` is required here.
const instrumentSerif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: {
    default: `${site.name} — ${site.tagline}`,
    template: `%s | ${site.name}`,
  },
  description: site.description,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: site.name,
    title: `${site.name} — ${site.tagline}`,
    description: site.description,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: `${site.name} — ${site.tagline}`,
    description: site.description,
  },
  // Vercel only noindexes preview deployments, not the production domain,
  // so this has to be explicit. Driven by the flag in content/portfolio.ts.
  robots: {
    index: searchIndexing,
    follow: searchIndexing,
    googleBot: { index: searchIndexing, follow: searchIndexing },
  },
};

// `metadata.viewport` and `metadata.themeColor` are deprecated in this version —
// they must be a separate `viewport` export.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf9f7" },
    { media: "(prefers-color-scheme: dark)", color: "#0c0a09" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // schema.org Person. `sameAs` is what lets Google resolve this Alex Glaze as
  // a distinct entity from the others sharing the name; jobTitle and alumniOf
  // disambiguate further. Inert while `searchIndexing` is false, but ready.
  const personJsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: site.name,
    url: site.url,
    jobTitle: identity.jobTitle,
    description: site.description,
    alumniOf: {
      "@type": "CollegeOrUniversity",
      name: identity.alumniOf,
    },
    ...(sameAs.length > 0 ? { sameAs } : {}),
  };

  return (
    // `data-scroll-behavior` is required for Next to honour the
    // `scroll-behavior: smooth` set in globals.css during navigation.
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${inter.variable} ${instrumentSerif.variable}`}
    >
      <body className="font-sans flex min-h-screen flex-col">
        <a
          href="#main"
          className="bg-ink text-canvas sr-only rounded px-4 py-2 focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50"
        >
          Skip to content
        </a>
        <SiteNav />
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
        {/* `<` escape per the Next.js JSON-LD guide — JSON.stringify alone
            does not sanitise strings that could close the script tag. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(personJsonLd).replace(/</g, "\\u003c"),
          }}
        />
      </body>
    </html>
  );
}
