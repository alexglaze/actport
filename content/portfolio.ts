/**
 * ─────────────────────────────────────────────────────────────
 *  EDIT THIS FILE — it is the only file you need to touch.
 *  Everything on the site reads from here.
 *  Anything marked PLACEHOLDER is fake and should be replaced.
 * ─────────────────────────────────────────────────────────────
 */

/**
 * Search engine indexing — currently OFF.
 *
 * While this is `false` the site sends `noindex, nofollow` and robots.txt
 * disallows everything, so search engines will not list it. Vercel only
 * noindexes *preview* deployments automatically; the production domain is
 * crawlable by default, which is why this flag exists.
 *
 * Leave it off until there is a reel and real credits. A thin page indexed
 * under your own name reads as less experienced than no page at all, and it
 * is much harder to get a bad impression out of the index than to delay.
 *
 * Flip to `true` when ready — that is the only change needed.
 */
export const searchIndexing = false;

export const site = {
  /** Your professional name, as it should appear in credits. */
  name: "Alex Glaze",
  /** Shown under your name in the hero. Keep it short. */
  tagline: "Actor", // PLACEHOLDER — refine, e.g. "Actor — Stage & Screen"
  /** Used for <title>, OG tags, and SEO. */
  description:
    "Alex Glaze is an actor based in New York. Reel, headshots, and credits.", // PLACEHOLDER
  /**
   * Canonical URL. Still the Vercel host — change to "https://alexglaze.com"
   * once that domain is attached in Vercel → Settings → Domains, so canonical
   * and OG URLs point at a host that actually serves the site.
   */
  url: "https://actport.vercel.app",
  /** Where you can work as a local hire. */
  basedIn: "New York, NY", // PLACEHOLDER
};

/**
 * Casting vitals. Set any of these to null to hide the row — better an
 * absent field than an invented one, since casting treats these as factual.
 */
export const stats = {
  height: null as string | null, // e.g. "5'11\""
  eyes: null as string | null, // e.g. "Brown"
  hair: null as string | null, // e.g. "Brown"
  vocalRange: null as string | null, // e.g. "Baritone"
  unions: null as string | null, // e.g. "Non-Union" / "SAG-AFTRA (Eligible)"
};

export const contact = {
  /** Your public booking email. */
  email: "alexiglaze@gmail.com", // Consider a dedicated booking address
  /** Leave `agent` null if you are self-represented. */
  agent: null as null | {
    name: string;
    company: string;
    email: string;
    phone?: string;
  },
  // Example once you sign:
  // agent: {
  //   name: "Jane Doe",
  //   company: "Talent Co.",
  //   email: "jane@talentco.com",
  //   phone: "+1 (212) 555-0100",
  // },
  socials: [
    { label: "Instagram", href: "https://instagram.com/alexiglaze" },
    { label: "X", href: "https://x.com/alexiglaze" },
  ],
};

/**
 * Profiles that prove this Alex Glaze is a distinct person from the others
 * who share the name. Google uses these (via schema.org `sameAs`) to resolve
 * you as one entity across the web — the single most useful thing this site
 * can do about the name collision.
 *
 * Add your IMDb URL here as soon as you have a page. IMDb is what Google
 * reads to build an actor's Knowledge Panel.
 */
export const sameAs: string[] = [
  "https://instagram.com/alexiglaze",
  "https://x.com/alexiglaze",
  // "https://www.imdb.com/name/nmXXXXXXX/",
];

/** Helps disambiguate you from the other Alex Glazes in search results. */
export const identity = {
  jobTitle: "Actor",
  alumniOf: "Harvard University",
};

export const about = {
  /** Each string is its own paragraph. */
  paragraphs: [
    // PLACEHOLDER — replace with your real bio before making this public.
    "Alex Glaze is an actor based in New York. Replace this paragraph with your real bio — where you trained, the kind of work you are drawn to, and what a director should know about working with you.",
    "Write a second paragraph about recent work, or the range you want to be cast in. Two or three short paragraphs reads better than one long one.",
  ],
  /**
   * Real training only. Emptied out rather than guessed at — a fabricated
   * credential is the one mistake here with actual consequences.
   */
  training: [] as { credential: string; org: string; year?: string }[],
  /** Special skills, phrased as casting would read them. */
  skills: [] as string[],
};

/**
 * The featured reel on the home page.
 * Use a YouTube or Vimeo *embed* URL:
 *   YouTube → https://www.youtube.com/embed/VIDEO_ID
 *   Vimeo   → https://player.vimeo.com/video/VIDEO_ID
 * Set `embedUrl` to null to hide the reel section entirely.
 */
export const reel = {
  embedUrl: null as string | null,
  title: "Acting Reel",
  /** Optional one-line note, e.g. "Updated Spring 2026". */
  note: null as string | null,
};

export type Headshot = {
  /** Path under /public, e.g. "/headshots/commercial.jpg". */
  src: string;
  /** Describe the image for screen readers and SEO. Required. */
  alt: string;
  /** Shown as a caption, e.g. "Commercial" or "Theatrical". */
  label: string;
  /** Photographer credit — good practice, often contractually required. */
  credit?: string;
};

/**
 * Drop real files into /public/headshots/ and point `src` at them.
 * Until then these point at a placeholder graphic that ships with the repo.
 * Recommended: 1200×1500 (4:5) JPEGs, under ~400KB each.
 */
export const headshots: Headshot[] = [
  {
    src: "/headshots/placeholder.png", // PLACEHOLDER
    alt: "Headshot of Alex Glaze",
    label: "Theatrical",
  },
];

export type Credit = {
  /** Production title. */
  title: string;
  /** The part you played. */
  role: string;
  /** Company, network, studio, or venue. */
  company: string;
  /** Director, or showrunner. Optional. */
  director?: string;
  /** Free-text year so "2024–2025" and "Upcoming" both work. */
  year?: string;
};

/**
 * Credits are grouped into sections. Convention is strongest-first:
 * lead film/TV work above chorus roles. Sections with no credits do not
 * render, so the page stays honest while these are empty.
 *
 * Emptied deliberately — the previous entries were invented examples, and
 * they were briefly live under your real name.
 */
export const creditSections: { heading: string; credits: Credit[] }[] = [
  { heading: "Film", credits: [] },
  { heading: "Television", credits: [] },
  { heading: "Theater", credits: [] },
];

/**
 * Put a real PDF at /public/<filename> and set this to its path,
 * e.g. "/alex-glaze-resume.pdf". Set to null to hide the download button.
 */
export const resumePdf: string | null = null;
