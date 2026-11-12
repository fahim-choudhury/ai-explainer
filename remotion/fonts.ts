// Bundled fonts, so rendering needs no network. Same files @remotion/google-fonts would fetch
// (Inter v18 and JetBrains Mono v20, latin subset, variable weight). Licenses: fonts/OFL-*.txt.
import { continueRender, delayRender } from "remotion";
import interUrl from "./fonts/Inter-latin.woff2";
import monoUrl from "./fonts/JetBrainsMono-latin.woff2";

const LATIN = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD";

function load(family: string, url: string, weights: string[]): string {
  if (typeof FontFace === "undefined") return family;
  for (const weight of weights) {
    const handle = delayRender(`font ${family} ${weight}`);
    const face = new FontFace(family, `url(${url}) format('woff2')`, { weight, style: "normal", unicodeRange: LATIN });
    face.load().then((f) => { document.fonts.add(f); continueRender(handle); }).catch((e) => { throw e; });
  }
  return family;
}

export const SANS = load("Inter", interUrl, ["400", "500", "600", "700", "800"]);
export const MONO = load("JetBrains Mono", monoUrl, ["400", "600"]);
