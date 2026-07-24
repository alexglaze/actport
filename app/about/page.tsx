import type { Metadata } from "next";
import Link from "next/link";
import { about, site } from "@/content/portfolio";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "About",
  description: `About ${site.name}, actor based in ${site.basedIn}.`,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <>
      <PageHeader title="About" />

      <div className="mx-auto max-w-5xl px-6 pb-8">
        <div className="max-w-2xl space-y-5 text-lg leading-relaxed">
          {about.paragraphs.map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>

        <p className="text-muted mt-10 text-sm">
          Full credits and training are on the{" "}
          <Link href="/resume" className="text-ink underline underline-offset-4">
            résumé
          </Link>
          . For bookings, see{" "}
          <Link href="/contact" className="text-ink underline underline-offset-4">
            contact
          </Link>
          .
        </p>
      </div>
    </>
  );
}
