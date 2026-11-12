import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, BeatCtx } from "./ui";

export type Timings = {
  fps: number;
  total: number;
  scenes: { id: string; start: number; end: number; lines: { text: string; start: number; end: number }[] }[];
};

const FADE = 12;

const Fader: React.FC<{ dur: number; last: boolean; children: React.ReactNode }> = ({ dur, last, children }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, FADE, dur - FADE, dur], [0, 1, 1, last ? 1 : 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const Background: React.FC<{ progress?: boolean }> = ({ progress = true }) => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: `radial-gradient(1200px 800px at 75% 20%, #16213F 0%, ${C.bg} 60%)` }}>
      <AbsoluteFill style={{ backgroundImage: `linear-gradient(${C.line}33 1px, transparent 1px), linear-gradient(90deg, ${C.line}33 1px, transparent 1px)`, backgroundSize: "64px 64px", backgroundPosition: `${f * 0.2}px ${f * 0.2}px` }} />
      {progress ? <div style={{ position: "absolute", left: 0, bottom: 0, height: 6, width: `${(f / durationInFrames) * 100}%`, background: C.orange, opacity: 0.8 }} /> : null}
    </AbsoluteFill>
  );
};

/** Lays scenes on the timeline from timings.json. Each scene reads its line start frames with useBeats(). */
export const makeExplainer = (scenes: Record<string, React.FC>, timings: Timings): React.FC => () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Background />
      <Audio src={staticFile("narration.wav")} />
      {timings.scenes.map((sc, i) => {
        const S = scenes[sc.id];
        if (!S) throw new Error(`No component registered for scene "${sc.id}"`);
        const from = Math.round(sc.start * fps);
        const last = i === timings.scenes.length - 1;
        const dur = Math.round((sc.end - sc.start) * fps) + (last ? 30 : FADE);
        const beats = sc.lines.map((l) => Math.round((l.start - sc.start) * fps));
        return (
          <Sequence key={sc.id} from={from} durationInFrames={dur} name={sc.id}>
            <BeatCtx.Provider value={beats}>
              <Fader dur={dur} last={last}><S /></Fader>
            </BeatCtx.Provider>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const durationFrames = (t: Timings) => Math.ceil(t.total * t.fps) + 30;
