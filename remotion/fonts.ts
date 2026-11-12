// Bundled fonts, so rendering needs no network. Same files @remotion/google-fonts would fetch
// (Inter v18 and JetBrains Mono v20, latin subset, variable weight). Licenses: fonts/OFL-*.txt.
import { cancelRender, continueRender, delayRender } from "remotion";
import interUrl from "./fonts/Inter-latin.woff2";
import monoUrl from "./fonts/JetBrainsMono-latin.woff2";

const LATIN = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD";

// One FontFace per family over the variable weight range. The earlier version made one FontFace per
// weight from the same file; in long renders some of those loads never settled and the delayRender
// handle timed out after 28 s ("font Inter 400"), while short still renders finished before the timeout.
function load(family: string, url: string, weight: string): string {
  if (typeof FontFace === "undefined") return family;
  const handle = delayRender(`font ${family}`);
  const face = new FontFace(family, `url(${url}) format('woff2')`, { weight, style: "normal", unicodeRange: LATIN });
  document.fonts.add(face);
  face.load().then(() => continueRender(handle), (e) => cancelRender(e));
  return family;
}

export const SANS = load("Inter", interUrl, "100 900");
export const MONO = load("JetBrains Mono", monoUrl, "100 800");
