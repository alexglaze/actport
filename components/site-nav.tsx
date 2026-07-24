"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";
import { site } from "@/content/portfolio";

// Derive the href type from Link itself so this stays correct under
// `typedRoutes` without hardcoding Next's generated Route type.
type Href = ComponentProps<typeof Link>["href"];

const links: { href: Href; label: string }[] = [
  { href: "/headshots", label: "Headshots" },
  { href: "/resume", label: "Résumé" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="border-line bg-canvas/85 sticky top-0 z-50 border-b backdrop-blur-sm">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-6 py-4 sm:flex-row sm:justify-between sm:gap-6"
      >
        <Link
          href="/"
          className="font-display text-xl tracking-tight sm:text-2xl"
          aria-current={pathname === "/" ? "page" : undefined}
        >
          {site.name}
        </Link>

        <ul className="flex items-center gap-5 text-sm sm:gap-6">
          {links.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <li key={String(href)}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "text-ink decoration-ink underline decoration-1 underline-offset-[6px]"
                      : "text-muted hover:text-ink transition-colors"
                  }
                >
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
