import Image from "next/image";
import Link from "next/link";
import { creditSections, headshots, reel, site, stats } from "@/content/portfolio";

const HEADSHOT_W = 1200;
const HEADSHOT_H = 1500;

export default function HomePage() {
  const featured = headshots[0];
  // Show a short teaser of credits on the home page; the full list lives on /resume.
  const teaserCredits = creditSections.flatMap((section) =>
    section.credits.map((credit) => ({ ...credit, section: section.heading })),
  );

  return (
    <>
      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 pt-16 pb-16 sm:pt-24">
        <div className="grid items-center gap-10 sm:grid-cols-[1.15fr_1fr] sm:gap-14">
          <div>
            <h1 className="font-display text-5xl leading-[1.05] tracking-tight sm:text-6xl">
              {site.name}
            </h1>
            <p className="text-muted mt-5 text-lg sm:text-xl">{site.tagline}</p>
            <p className="text-muted mt-2 text-sm">
              Based in {site.basedIn} · {stats.unions}
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                href="/headshots"
                className="bg-ink text-canvas rounded-full px-5 py-2.5 text-sm transition-opacity hover:opacity-85"
              >
                View headshots
              </Link>
              <Link
                href="/resume"
                className="border-line hover:border-ink rounded-full border px-5 py-2.5 text-sm transition-colors"
              >
                Résumé &amp; credits
              </Link>
              <Link
                href="/contact"
                className="border-line hover:border-ink rounded-full border px-5 py-2.5 text-sm transition-colors"
              >
                Get in touch
              </Link>
            </div>
          </div>

          {featured ? (
            // Capped width so the 4:5 portrait does not tower over the text column.
            <div className="border-line bg-surface w-full overflow-hidden rounded-lg border sm:ml-auto sm:max-w-xs">
              <Image
                src={featured.src}
                alt={featured.alt}
                width={HEADSHOT_W}
                height={HEADSHOT_H}
                // `priority` is deprecated in this version of Next.
                fetchPriority="high"
                loading="eager"
                sizes="(min-width: 640px) 320px, 100vw"
                className="h-auto w-full object-cover"
              />
            </div>
          ) : null}
        </div>
      </section>

      {/* Reel — hidden entirely until `reel.embedUrl` is set in content/portfolio.ts */}
      {reel.embedUrl ? (
        <section className="border-line border-t">
          <div className="mx-auto max-w-5xl px-6 py-16">
            <h2 className="font-display text-3xl tracking-tight">{reel.title}</h2>
            {reel.note ? <p className="text-muted mt-2 text-sm">{reel.note}</p> : null}
            <div className="border-line bg-surface mt-6 aspect-video overflow-hidden rounded-lg border">
              <iframe
                src={reel.embedUrl}
                title={`${site.name} — ${reel.title}`}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                allowFullScreen
                loading="lazy"
                className="h-full w-full"
              />
            </div>
          </div>
        </section>
      ) : null}

      {/* Headshot strip */}
      {headshots.length > 1 ? (
        <section className="border-line border-t">
          <div className="mx-auto max-w-5xl px-6 py-16">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-display text-3xl tracking-tight">Headshots</h2>
              <Link href="/headshots" className="text-muted hover:text-ink text-sm transition-colors">
                See all →
              </Link>
            </div>

            {/* Three columns at every width so a 3-item teaser never orphans a tile. */}
            <ul className="mt-6 grid grid-cols-3 gap-4">
              {headshots.slice(0, 3).map((headshot, i) => (
                <li
                  key={`${headshot.src}-${i}`}
                  className="border-line bg-surface overflow-hidden rounded-lg border"
                >
                  <Image
                    src={headshot.src}
                    alt={headshot.alt}
                    width={HEADSHOT_W}
                    height={HEADSHOT_H}
                    sizes="(min-width: 640px) 30vw, 50vw"
                    className="h-auto w-full object-cover"
                  />
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}

      {/* Selected credits */}
      {teaserCredits.length > 0 ? (
        <section className="border-line border-t">
          <div className="mx-auto max-w-5xl px-6 py-16">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-display text-3xl tracking-tight">Selected credits</h2>
              <Link href="/resume" className="text-muted hover:text-ink text-sm transition-colors">
                Full résumé →
              </Link>
            </div>

            <ul className="divide-line mt-6 divide-y">
              {teaserCredits.slice(0, 4).map((credit, i) => (
                <li
                  key={`${credit.title}-${i}`}
                  className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-4"
                >
                  <span className="font-medium">{credit.title}</span>
                  <span className="text-muted text-sm">
                    {credit.role} · {credit.company}
                    {credit.year ? ` · ${credit.year}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </>
  );
}
