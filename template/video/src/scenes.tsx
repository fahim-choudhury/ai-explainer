// One component per scene id in script/script.json. Canvas is 1920x1080.
// useBeats() returns the frame (relative to the scene start) where each narration line begins:
// b[0] = first line, b[1] = second line, ... Tie every entrance to a beat so visuals follow the voice.
import React from "react";
import { AbsoluteFill } from "remotion";
import { C, SANS, MONO, Title, Node, Links, Chip, Appear, useBeats } from "@xv/ui";

const Intro: React.FC = () => {
  const b = useBeats();
  return (
    <AbsoluteFill>
      <Title kicker="Section label" title="Scene title" />
      <Links links={[{ a: [600, 600], b: [1300, 600], at: b[1], color: C.green, packets: 3 }]} />
      <Node x={600} y={600} kind="laptop" label="Peer A" at={b[0]} color={C.blue} />
      <Node x={1300} y={600} kind="server" label="Peer B" at={b[0] + 10} color={C.green} />
      <div style={{ position: "absolute", left: 120, top: 860 }}>
        <Chip at={b[1] + 20} color={C.orange}>Appears 20 frames after line 2 starts</Chip>
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const b = useBeats();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <Appear at={b[0]} scale>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 120, color: C.text }}>{"{{TITLE}}"}</div>
        <div style={{ fontFamily: MONO, fontSize: 32, color: C.muted, textAlign: "center", marginTop: 24 }}>links go here</div>
      </Appear>
    </AbsoluteFill>
  );
};

export const SCENES: Record<string, React.FC> = { intro: Intro, outro: Outro };
