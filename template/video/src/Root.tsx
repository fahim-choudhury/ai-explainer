import React from "react";
import { Composition, Still } from "remotion";
import { makeExplainer, durationFrames, Timings } from "@xv/Explainer";
import timings from "../../audio/timings.json";
import { SCENES } from "./scenes";
import { Thumbnail } from "./Thumbnail";

const t = timings as Timings;
const Main = makeExplainer(SCENES, t);

export const Root: React.FC = () => (
  <>
    <Composition id="Main" component={Main} durationInFrames={durationFrames(t)} fps={t.fps} width={1920} height={1080} />
    {/* `xv thumbnail` renders every Still whose id starts with "Thumbnail": ThumbnailB -> thumbnail-b.jpg for Studio's Test & compare */}
    <Still id="Thumbnail" component={Thumbnail} width={1920} height={1080} />
  </>
);
