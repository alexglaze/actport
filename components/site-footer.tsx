import { contact, site } from "@/content/portfolio";

export function SiteFooter() {
  // Rendered at build time; fine for a copyright line.
  const year = new Date().getFullYear();

  return (
    <footer className="border-line mt-24 border-t">
      <div className="text-muted mx-auto flex max-w-5xl flex-col gap-4 px-6 py-10 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p>
          © {year} {site.name}
        </p>

        <ul className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <li>
            <a href={`mailto:${contact.email}`} className="hover:text-ink transition-colors">
              {contact.email}
            </a>
          </li>
          {contact.socials.map((social) => (
            <li key={social.href}>
              <a
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink transition-colors"
              >
                {social.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
