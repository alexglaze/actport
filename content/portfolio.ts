/**
 * ─────────────────────────────────────────────────────────────
 *  EDIT THIS FILE — it is the only file you need to touch.
 *  Everything on the site reads from here.
 *  Anything marked PLACEHOLDER is fake and should be replaced.
 * ─────────────────────────────────────────────────────────────
 */

export const site = {
  /** Your professional name, as it should appear in credits. */
  name: "Alex Glaze",
  /** Shown under your name in the hero. Keep it short. */
  tagline: "Actor — Stage & Screen", // PLACEHOLDER
  /** Used for <title>, OG tags, and SEO. */
  description:
    "Acting portfolio of Alex Glaze — reel, headshots, and credits.", // PLACEHOLDER
  /** Set this once you have a domain. Used for canonical + OG URLs. */
  url: "https://actport.vercel.app", // PLACEHOLDER
  /** Locations you can work as a local hire. */
  basedIn: "New York, NY", // PLACEHOLDER
};

export const stats = {
  height: "5'11\"", // PLACEHOLDER
  eyes: "Brown", // PLACEHOLDER
  hair: "Brown", // PLACEHOLDER
  vocalRange: "Baritone", // PLACEHOLDER
  unions: "Non-Union", // PLACEHOLDER — e.g. "SAG-AFTRA (Eligible)"
};

export const contact = {
  /** Your public booking email. */
  email: "you@example.com", // PLACEHOLDER
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
    // Delete any you do not use — empty list renders nothing.
    { label: "Instagram", href: "https://instagram.com/username" }, // PLACEHOLDER
    { label: "IMDb", href: "https://imdb.com/name/nm0000000" }, // PLACEHOLDER
  ],
};

export const about = {
  /** Each string is its own paragraph. */
  paragraphs: [
    // PLACEHOLDER — replace all of this with your real bio.
    "Alex Glaze is an actor based in New York. Replace this paragraph with your real bio — where you trained, the kind of work you are drawn to, and what a director should know about working with you.",
    "Write a second paragraph about recent work, or the range you want to be cast in. Two or three short paragraphs reads better than one long one.",
  ],
  training: [
    // PLACEHOLDER
    { credential: "BA, Theater", org: "Harvard University", year: "2024" },
    { credential: "Meisner Technique", org: "Studio Name", year: "2025" },
  ],
  skills: [
    // PLACEHOLDER — special skills, as casting would read them.
    "Stage combat (unarmed)",
    "Guitar (intermediate)",
    "Dialects: RP, Southern American",
    "Improv",
  ],
};

/**
 * The featured reel on the home page.
 * Use a YouTube or Vimeo *embed* URL:
 *   YouTube → https://www.youtube.com/embed/VIDEO_ID
 *   Vimeo   → https://player.vimeo.com/video/VIDEO_ID
 * Set `embedUrl` to null to hide the reel section entirely.
 */
export const reel = {
  embedUrl: null as string | null, // PLACEHOLDER — e.g. "https://player.vimeo.com/video/76979871"
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
    alt: "Theatrical headshot of Alex Glaze",
    label: "Theatrical",
    credit: "Photographer Name",
  },
  {
    src: "/headshots/placeholder.png", // PLACEHOLDER
    alt: "Commercial headshot of Alex Glaze",
    label: "Commercial",
    credit: "Photographer Name",
  },
  {
    src: "/headshots/placeholder.png", // PLACEHOLDER
    alt: "Character headshot of Alex Glaze",
    label: "Character",
    credit: "Photographer Name",
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
 * lead film/TV work above chorus roles. Delete any section you have
 * nothing for — empty sections do not render.
 */
export const creditSections: { heading: string; credits: Credit[] }[] = [
  {
    heading: "Film",
    credits: [
      // PLACEHOLDER — replace with real credits.
      {
        title: "Short Film Title",
        role: "Lead",
        company: "Production Company",
        director: "Director Name",
        year: "2025",
      },
    ],
  },
  {
    heading: "Television",
    credits: [
      // PLACEHOLDER
      {
        title: "Series Title",
        role: "Guest Star",
        company: "Network",
        director: "Director Name",
        year: "2025",
      },
    ],
  },
  {
    heading: "Theater",
    credits: [
      // PLACEHOLDER
      {
        title: "Play Title",
        role: "Character Name",
        company: "Theater Company",
        director: "Director Name",
        year: "2024",
      },
      {
        title: "Another Play",
        role: "Character Name",
        company: "Theater Company",
        director: "Director Name",
        year: "2024",
      },
    ],
  },
];

/**
 * Put a real PDF at /public/<filename> and set this to its path,
 * e.g. "/alex-glaze-resume.pdf". Set to null to hide the download button.
 */
export const resumePdf: string | null = null; // PLACEHOLDER
