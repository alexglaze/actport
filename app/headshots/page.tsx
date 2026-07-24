import type { Metadata } from "next";
import Image from "next/image";
import { PageHeader } from "@/components/page-header";
import { headshots } from "@/content/portfolio";

export const metadata: Metadata = {
  title: "Headshots",
  description: "Theatrical, commercial, and character headshots.",
  alternates: { canonical: "/headshots" },
};

export default function HeadshotsPage() {
  return (
    <>
      <PageHeader
        title="Headshots"
        intro="Click any image to open it full size. Available in print resolution on request."
      />

      <div className="mx-auto max-w-5xl px-6 pb-8">
        {headshots.length === 0 ? (
          <p className="text-muted">Headshots coming soon.</p>
        ) : (
          <ul className="grid gap-8 sm:grid-cols-2">
            {headshots.map((headshot, i) => (
              <li key={`${headshot.src}-${i}`}>
                <a
                  href={headshot.src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border-line bg-surface block overflow-hidden rounded-lg border"
                >
                  <Image
                    src={headshot.src}
                    alt={headshot.alt}
                    width={1200}
                    height={1500}
                    sizes="(min-width: 640px) 45vw, 100vw"
                    // Only the first pair is above the fold on most screens.
                    loading={i < 2 ? "eager" : "lazy"}
                    className="h-auto w-full object-cover"
                  />
                </a>
                <div className="mt-3 flex items-baseline justify-between gap-4">
                  <span className="text-sm font-medium">{headshot.label}</span>
                  {headshot.credit ? (
                    <span className="text-muted text-xs">Photo: {headshot.credit}</span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
