import { ImageResponse } from "next/og";
import { site } from "@/content/portfolio";

export const alt = `${site.name} — ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Only flexbox and a subset of CSS properties are supported here — no CSS grid.
export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          backgroundColor: "#faf9f7",
          color: "#1c1917",
          padding: "80px",
        }}
      >
        <div style={{ display: "flex", fontSize: 92, letterSpacing: "-0.02em" }}>
          {site.name}
        </div>
        <div style={{ display: "flex", marginTop: 20, fontSize: 40, color: "#6b625c" }}>
          {site.tagline}
        </div>
        <div style={{ display: "flex", marginTop: 48, fontSize: 26, color: "#6b625c" }}>
          {site.basedIn}
        </div>
      </div>
    ),
    { ...size },
  );
}
