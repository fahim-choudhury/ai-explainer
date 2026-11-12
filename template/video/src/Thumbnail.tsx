// Rendered at 1920x1080 and scaled to 1280x720 by `xv thumbnail`. Keep text large: it is viewed at ~320px wide.
import React from "react";
import { AbsoluteFill } from "remotion";
import { C, SANS, MONO } from "@xv/ui";

export const Thumbnail: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(1100px 900px at 78% 50%, #1B2A55 0%, ${C.bg} 65%)`, padding: 100, fontFamily: SANS }}>
    <div style={{ fontFamily: MONO, fontSize: 40, color: C.orange, letterSpacing: 6 }}>EXPLAINED</div>
    <div style={{ fontSize: 158, fontWeight: 800, lineHeight: 0.98, color: C.text, letterSpacing: -4, marginTop: 14 }}>{"{{TITLE}}"}</div>
  </AbsoluteFill>
);
