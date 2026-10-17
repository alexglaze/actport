# Portfolio site

Acting portfolio site for Alex Glaze. Next.js 16 (App Router) + TypeScript + Tailwind CSS v4, deployed on Vercel. The app lives at the repository root; paths below are relative to it.

## Editing your content

**You only need to edit one file: [`content/portfolio.ts`](portfolio.ts).**

Every page reads from it — your name, bio, credits, headshots, reel, and contact details. Anything currently marked `PLACEHOLDER` is fake and should be replaced. No page files need to change.

### Adding headshots

1. Drop image files into `public/headshots/`.
2. Point the `src` fields in the `headshots` array at them (e.g. `/headshots/theatrical.jpg`).

Recommended: 4:5 aspect ratio (1200×1500), JPEG, under ~400KB each. Every headshot needs a real `alt` description — it is what screen readers announce and what search engines index.

### Adding your reel

Set `reel.embedUrl` to a **player/embed** URL, not the page URL:

| Platform | Use this form |
| --- | --- |
| YouTube | `https://www.youtube.com/embed/VIDEO_ID` |
| Vimeo | `https://player.vimeo.com/video/VIDEO_ID` |

Leave it as `null` and the reel section is hidden entirely.

### Adding your resume PDF

Put the PDF in `public/` and set `resumePdf` to its path (e.g. `/alex-glaze-resume.pdf`). Leave it `null` to hide the download button. The credits table renders from `creditSections` either way, so the site works with no PDF at all.

## Running locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm run build       # production build
```

Run these before pushing — Vercel will fail the deploy on a type or lint error.

## Deploying

Pushes to `main` deploy to production automatically via the Vercel git integration. Pull requests get their own preview URL.

Set `site.url` in `content/portfolio.ts` to your real domain once you have one — it is used for canonical links and social share previews.
