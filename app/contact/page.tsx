import type { Metadata } from "next";
import { contact, site, stats } from "@/content/portfolio";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Contact",
  description: `Booking and representation enquiries for ${site.name}.`,
  alternates: { canonical: "/contact" },
};

export default function ContactPage() {
  const { agent } = contact;

  return (
    <>
      <PageHeader
        title="Contact"
        intro={
          agent
            ? "For casting and booking enquiries, please go through representation."
            : "Currently self-represented — enquiries come straight to me."
        }
      />

      <div className="mx-auto max-w-5xl px-6 pb-8">
        <div className="grid gap-10 sm:grid-cols-2">
          {/* Representation takes precedence when it exists. */}
          {agent ? (
            <section>
              <h2 className="text-muted text-xs tracking-wide uppercase">Representation</h2>
              <p className="mt-3 font-medium">{agent.company}</p>
              <p className="text-muted text-sm">{agent.name}</p>
              <p className="mt-2 text-sm">
                <a
                  href={`mailto:${agent.email}`}
                  className="underline underline-offset-4"
                >
                  {agent.email}
                </a>
              </p>
              {agent.phone ? (
                <p className="text-sm">
                  <a href={`tel:${agent.phone.replace(/[^+\d]/g, "")}`} className="underline underline-offset-4">
                    {agent.phone}
                  </a>
                </p>
              ) : null}
            </section>
          ) : null}

          <section>
            <h2 className="text-muted text-xs tracking-wide uppercase">
              {agent ? "Direct" : "Email"}
            </h2>
            <p className="mt-3">
              <a
                href={`mailto:${contact.email}`}
                className="text-lg underline underline-offset-4"
              >
                {contact.email}
              </a>
            </p>
            <p className="text-muted mt-2 text-sm">
              Based in {site.basedIn} · {stats.unions}
            </p>
          </section>

          {contact.socials.length > 0 ? (
            <section>
              <h2 className="text-muted text-xs tracking-wide uppercase">Elsewhere</h2>
              <ul className="mt-3 space-y-1.5 text-sm">
                {contact.socials.map((social) => (
                  <li key={social.href}>
                    <a
                      href={social.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-4"
                    >
                      {social.label}
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <a
          href={`mailto:${agent ? agent.email : contact.email}?subject=${encodeURIComponent(
            `Enquiry for ${site.name}`,
          )}`}
          className="bg-ink text-canvas mt-12 inline-block rounded-full px-5 py-2.5 text-sm transition-opacity hover:opacity-85"
        >
          Send an email
        </a>
      </div>
    </>
  );
}
