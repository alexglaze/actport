import type { Metadata } from "next";
import { about, contact, creditSections, resumePdf, site, stats } from "@/content/portfolio";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Résumé",
  description: `Acting credits, training, and special skills for ${site.name}.`,
  alternates: { canonical: "/resume" },
};

export default function ResumePage() {
  const sections = creditSections.filter((section) => section.credits.length > 0);

  // Only show vitals that are actually set — an empty row invites the reader
  // to wonder what is being withheld.
  const vitals = [
    { label: "Height", value: stats.height },
    { label: "Eyes", value: stats.eyes },
    { label: "Hair", value: stats.hair },
    { label: "Voice", value: stats.vocalRange },
    { label: "Union", value: stats.unions },
  ].filter((item): item is { label: string; value: string } => Boolean(item.value));

  const hasContent = sections.length > 0 || about.training.length > 0 || about.skills.length > 0;

  return (
    <>
      <PageHeader title="Résumé" />

      <div className="mx-auto max-w-5xl px-6 pb-8">
        {/* Vitals */}
        {vitals.length > 0 ? (
          <dl className="border-line divide-line grid grid-cols-2 gap-x-8 gap-y-4 border-y py-6 sm:grid-cols-4">
            {vitals.map((item) => (
              <div key={item.label}>
                <dt className="text-muted text-xs tracking-wide uppercase">{item.label}</dt>
                <dd className="mt-1 text-sm">{item.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}

        {!hasContent ? (
          <p className="text-muted mt-8 max-w-xl leading-relaxed">
            Credits and training are being added. For a current résumé, please{" "}
            <a href={`mailto:${contact.email}`} className="text-ink underline underline-offset-4">
              get in touch
            </a>
            .
          </p>
        ) : null}

        {resumePdf ? (
          <a
            href={resumePdf}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-ink text-canvas mt-8 inline-block rounded-full px-5 py-2.5 text-sm transition-opacity hover:opacity-85"
          >
            Download PDF résumé
          </a>
        ) : null}

        {/* Credits */}
        {sections.map((section) => (
          <section key={section.heading} className="mt-14">
            <h2 className="font-display text-2xl tracking-tight">{section.heading}</h2>
            {/* Four columns is too wide for phones — scroll the table, not the page. */}
            <div className="mt-4 -mx-6 overflow-x-auto px-6">
            <table className="w-full min-w-lg border-collapse text-left text-sm">
              <thead>
                <tr className="text-muted border-line border-b text-xs tracking-wide uppercase">
                  <th scope="col" className="py-2 pr-4 font-normal">
                    Production
                  </th>
                  <th scope="col" className="py-2 pr-4 font-normal">
                    Role
                  </th>
                  <th scope="col" className="py-2 pr-4 font-normal">
                    Company
                  </th>
                  <th scope="col" className="py-2 font-normal">
                    Director
                  </th>
                </tr>
              </thead>
              <tbody className="divide-line divide-y">
                {section.credits.map((credit, i) => (
                  <tr key={`${credit.title}-${i}`}>
                    <td className="py-3 pr-4 align-top">
                      <span className="font-medium">{credit.title}</span>
                      {credit.year ? (
                        <span className="text-muted block text-xs">{credit.year}</span>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4 align-top">{credit.role}</td>
                    <td className="text-muted py-3 pr-4 align-top">{credit.company}</td>
                    <td className="text-muted py-3 align-top">{credit.director ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        ))}

        {/* Training */}
        {about.training.length > 0 ? (
          <section className="mt-14">
            <h2 className="font-display text-2xl tracking-tight">Training</h2>
            <ul className="divide-line mt-4 divide-y text-sm">
              {about.training.map((item, i) => (
                <li
                  key={`${item.credential}-${i}`}
                  className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-3"
                >
                  <span className="font-medium">{item.credential}</span>
                  <span className="text-muted">
                    {item.org}
                    {item.year ? ` · ${item.year}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {/* Skills */}
        {about.skills.length > 0 ? (
          <section className="mt-14">
            <h2 className="font-display text-2xl tracking-tight">Special skills</h2>
            <ul className="mt-4 flex flex-wrap gap-2">
              {about.skills.map((skill) => (
                <li
                  key={skill}
                  className="border-line text-muted rounded-full border px-3 py-1.5 text-sm"
                >
                  {skill}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </>
  );
}
