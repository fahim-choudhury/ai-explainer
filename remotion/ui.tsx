import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const { fontFamily: SANS } = loadInter("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
export const { fontFamily: MONO } = loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] });

export const C = {
  bg: "#090E1B",
  bg2: "#0F1629",
  panel: "#141D33",
  line: "#26324F",
  text: "#EAF0FB",
  muted: "#8C97B3",
  orange: "#F68330",
  blue: "#4C8DFF",
  green: "#36D399",
  red: "#FF5D6C",
  purple: "#A78BFA",
  yellow: "#FACC15",
};

/** Beats = frame offsets (relative to the scene) at which each narration line starts. */
export const BeatCtx = React.createContext<number[]>([]);
export const useBeats = () => React.useContext(BeatCtx);

export const useAppear = (at: number, damping = 18) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - at, fps, config: { damping, mass: 0.7 } });
};

export const lerp = (f: number, a: number, b: number, from = 0, to = 1) =>
  interpolate(f, [a, b], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });

export const Appear: React.FC<{ at: number; children: React.ReactNode; y?: number; style?: React.CSSProperties; scale?: boolean }> = ({ at, children, y = 24, style, scale }) => {
  const p = useAppear(at);
  return (
    <div style={{ opacity: p, transform: `translateY(${(1 - p) * y}px) ${scale ? `scale(${0.85 + 0.15 * p})` : ""}`, ...style }}>{children}</div>
  );
};

export const Title: React.FC<{ kicker: string; title: string; at?: number }> = ({ kicker, title, at = 0 }) => {
  const p = useAppear(at);
  return (
    <div style={{ position: "absolute", left: 120, top: 80, opacity: p, transform: `translateX(${(1 - p) * -30}px)` }}>
      <div style={{ color: C.orange, fontFamily: MONO, fontSize: 24, letterSpacing: 4, textTransform: "uppercase" }}>{kicker}</div>
      <div style={{ color: C.text, fontFamily: SANS, fontWeight: 800, fontSize: 64, marginTop: 8, letterSpacing: -1 }}>{title}</div>
    </div>
  );
};

/* ---------- icons ---------- */
export type IconKind = "laptop" | "server" | "db" | "phone" | "cloud" | "printer" | "nas" | "brain" | "signal" | "relay" | "client" | "shield" | "key" | "lock" | "user" | "router"
  | "mail" | "bug" | "app" | "globe" | "home" | "eye" | "eyeAlt" | "plane" | "coffee" | "chip" | "proxy" | "tower" | "battery" | "file";
export const Icon: React.FC<{ kind: IconKind; size?: number; color?: string }> = ({ kind, size = 64, color = C.text }) => {
  const s = { fill: "none", stroke: color, strokeWidth: 2.2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const p: Record<IconKind, React.ReactNode> = {
    laptop: (<><rect x="10" y="14" width="44" height="28" rx="3" {...s} /><path d="M4 48h56l-4 5H8z" {...s} /></>),
    server: (<><rect x="12" y="8" width="40" height="14" rx="3" {...s} /><rect x="12" y="25" width="40" height="14" rx="3" {...s} /><rect x="12" y="42" width="40" height="14" rx="3" {...s} /><circle cx="19" cy="15" r="1.8" fill={color} /><circle cx="19" cy="32" r="1.8" fill={color} /><circle cx="19" cy="49" r="1.8" fill={color} /></>),
    db: (<><ellipse cx="32" cy="14" rx="18" ry="6" {...s} /><path d="M14 14v36c0 3.3 8 6 18 6s18-2.7 18-6V14" {...s} /><path d="M14 26c0 3.3 8 6 18 6s18-2.7 18-6M14 38c0 3.3 8 6 18 6s18-2.7 18-6" {...s} /></>),
    phone: (<><rect x="18" y="5" width="28" height="54" rx="5" {...s} /><path d="M28 51h8" {...s} /></>),
    cloud: (<path d="M18 46h30a10 10 0 0 0 0-20 14 14 0 0 0-27-3 11 11 0 0 0-3 23z" {...s} />),
    printer: (<><rect x="16" y="8" width="32" height="14" {...s} /><rect x="8" y="22" width="48" height="20" rx="3" {...s} /><rect x="16" y="36" width="32" height="18" {...s} /></>),
    nas: (<><rect x="14" y="8" width="36" height="48" rx="4" {...s} /><path d="M20 18h24M20 28h24M20 38h24" {...s} /><circle cx="44" cy="48" r="2" fill={color} /></>),
    brain: (<><circle cx="32" cy="32" r="22" {...s} /><path d="M32 10v44M10 32h44M17 17l30 30M47 17L17 47" {...s} strokeWidth={1.4} /><circle cx="32" cy="32" r="7" {...s} fill={C.bg} /></>),
    signal: (<><circle cx="32" cy="36" r="4" fill={color} /><path d="M22 26a14 14 0 0 1 20 0M16 20a22 22 0 0 1 32 0M26 46l6-10 6 10" {...s} /></>),
    relay: (<><path d="M8 24h40l-8-8M56 40H16l8 8" {...s} /></>),
    client: (<><rect x="8" y="12" width="48" height="34" rx="4" {...s} /><path d="M22 54h20M32 46v8" {...s} /><path d="M24 30l6 6 12-12" {...s} /></>),
    shield: (<><path d="M32 6l22 8v16c0 14-10 24-22 28C20 54 10 44 10 30V14z" {...s} /><path d="M22 31l7 7 13-14" {...s} /></>),
    key: (<><circle cx="20" cy="32" r="10" {...s} /><path d="M30 32h26M48 32v8M54 32v6" {...s} /></>),
    lock: (<><rect x="14" y="28" width="36" height="28" rx="4" {...s} /><path d="M22 28v-8a10 10 0 0 1 20 0v8" {...s} /><circle cx="32" cy="42" r="3" fill={color} /></>),
    user: (<><circle cx="32" cy="22" r="10" {...s} /><path d="M12 56c2-11 10-17 20-17s18 6 20 17" {...s} /></>),
    router: (<><rect x="8" y="34" width="48" height="16" rx="4" {...s} /><path d="M20 34l-6-14M44 34l6-14" {...s} /><circle cx="18" cy="42" r="2" fill={color} /><circle cx="26" cy="42" r="2" fill={color} /></>),
    mail: (<><rect x="8" y="14" width="48" height="36" rx="4" {...s} /><path d="M8 18l24 18 24-18" {...s} /></>),
    bug: (<><ellipse cx="32" cy="36" rx="12" ry="16" {...s} /><path d="M32 22v30M20 30H8M20 42H8M44 30h12M44 42h12M24 22l-6-10M40 22l6-10" {...s} /></>),
    app: (<><rect x="8" y="10" width="48" height="44" rx="5" {...s} /><path d="M8 22h48" {...s} /><circle cx="15" cy="16" r="1.8" fill={color} /><circle cx="21" cy="16" r="1.8" fill={color} /><path d="M18 34h28M18 44h18" {...s} /></>),
    globe: (<><circle cx="32" cy="32" r="22" {...s} /><path d="M10 32h44M32 10c8 8 8 36 0 44M32 10c-8 8-8 36 0 44" {...s} /></>),
    home: (<><path d="M8 30L32 10l24 20" {...s} /><path d="M14 26v28h36V26" {...s} /><rect x="27" y="38" width="10" height="16" {...s} /></>),
    eye: (<><path d="M4 32c8-14 18-20 28-20s20 6 28 20c-8 14-18 20-28 20S12 46 4 32z" {...s} /><circle cx="32" cy="32" r="8" {...s} /></>),
    plane: (<path d="M6 34l50-22-14 42-10-16-26-4zM32 38l24-26" {...s} />),
    coffee: (<><path d="M10 22h36v18a14 14 0 0 1-14 14h-8a14 14 0 0 1-14-14z" {...s} /><path d="M46 26h4a6 6 0 0 1 0 12h-5M20 8v8M28 8v8M36 8v8" {...s} /></>),
    chip: (<><rect x="16" y="16" width="32" height="32" rx="4" {...s} /><rect x="25" y="25" width="14" height="14" {...s} /><path d="M24 8v8M32 8v8M40 8v8M24 48v8M32 48v8M40 48v8M8 24h8M8 32h8M8 40h8M48 24h8M48 32h8M48 40h8" {...s} /></>),
    proxy: (<><rect x="20" y="8" width="24" height="48" rx="4" {...s} /><path d="M4 32h16M44 32h16M26 26l6 6-6 6" {...s} /></>),
    tower: (<><path d="M32 22L20 58M32 22l12 36M24 46h16M27 34h10" {...s} /><circle cx="32" cy="18" r="4" {...s} /><path d="M20 10a16 16 0 0 0 0 16M44 10a16 16 0 0 1 0 16" {...s} /></>),
    battery: (<><rect x="8" y="20" width="44" height="24" rx="4" {...s} /><path d="M56 28v8" {...s} /><rect x="13" y="25" width="26" height="14" rx="2" fill={color} /></>),
    file: (<><path d="M16 6h22l12 12v40H16z" {...s} /><path d="M38 6v12h12M22 30h20M22 38h20M22 46h14" {...s} /></>),
    eyeAlt: (<><path d="M4 32s10-18 28-18 28 18 28 18-10 18-28 18S4 32 4 32z" {...s} /><circle cx="32" cy="32" r="8" {...s} /></>),
  };
  return <svg width={size} height={size} viewBox="0 0 64 64">{p[kind]}</svg>;
};

/* ---------- network nodes ---------- */
export const Node: React.FC<{
  x: number; y: number; kind: IconKind; label?: string; sub?: string; at?: number; color?: string; dim?: number; size?: number; glow?: number; badge?: React.ReactNode;
}> = ({ x, y, kind, label, sub, at = 0, color = C.text, dim = 0, size = 120, glow = 0, badge }) => {
  const p = useAppear(at);
  return (
    <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, opacity: p * (1 - dim * 0.7), transform: `scale(${0.6 + 0.4 * p})`, textAlign: "center" }}>
      <div style={{ width: size, height: size, borderRadius: 28, background: C.panel, border: `2px solid ${glow ? color : C.line}`, boxShadow: glow ? `0 0 ${40 * glow}px ${color}88` : "none", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
        <Icon kind={kind} size={size * 0.55} color={color} />
        {badge ? <div style={{ position: "absolute", right: -18, top: -18 }}>{badge}</div> : null}
      </div>
      {label ? <div style={{ marginTop: 12, whiteSpace: "nowrap", marginLeft: -100, marginRight: -100 }}><span style={{ color: C.text, fontFamily: SANS, fontWeight: 600, fontSize: 26, background: C.bg, padding: "0 8px", borderRadius: 6 }}>{label}</span></div> : null}
      {sub ? <div style={{ marginTop: 2, whiteSpace: "nowrap", marginLeft: -100, marginRight: -100 }}><span style={{ color: C.muted, fontFamily: MONO, fontSize: 20, background: C.bg, padding: "0 6px", borderRadius: 6 }}>{sub}</span></div> : null}
    </div>
  );
};

/** SVG overlay drawing links, with optional packets travelling along them. */
export type LinkSpec = { a: [number, number]; b: [number, number]; at: number; color?: string; dashed?: boolean; packets?: number; speed?: number; width?: number; out?: number; via?: [number, number]; reverse?: boolean };

const pointOn = (l: LinkSpec, t: number): [number, number] => {
  if (!l.via) return [l.a[0] + (l.b[0] - l.a[0]) * t, l.a[1] + (l.b[1] - l.a[1]) * t];
  const u = 1 - t;
  return [u * u * l.a[0] + 2 * u * t * l.via[0] + t * t * l.b[0], u * u * l.a[1] + 2 * u * t * l.via[1] + t * t * l.b[1]];
};

export const Links: React.FC<{ links: LinkSpec[] }> = ({ links }) => {
  const f = useCurrentFrame();
  return (
    <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
      {links.map((l, i) => {
        const grow = lerp(f, l.at, l.at + 20);
        const fade = l.out !== undefined ? 1 - lerp(f, l.out, l.out + 12) : 1;
        if (grow <= 0 || fade <= 0) return null;
        const col = l.color ?? C.blue;
        const pts = Array.from({ length: 41 }, (_, k) => pointOn(l, (k / 40) * grow));
        const d = pts.map((p, k) => `${k ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
        const n = l.packets ?? 0;
        return (
          <g key={i} opacity={fade}>
            <path d={d} stroke={col} strokeWidth={l.width ?? 4} fill="none" strokeDasharray={l.dashed ? "10 12" : undefined} strokeLinecap="round" opacity={0.75} />
            {grow >= 1 && Array.from({ length: n }).map((_, k) => {
              const t0 = (((f - l.at) * (l.speed ?? 0.012) + k / n) % 1 + 1) % 1;
              const t = l.reverse ? 1 - t0 : t0;
              const [px, py] = pointOn(l, t);
              return <circle key={k} cx={px} cy={py} r={8} fill={col} style={{ filter: `drop-shadow(0 0 8px ${col})` }} />;
            })}
          </g>
        );
      })}
    </svg>
  );
};

export const Chip: React.FC<{ children: React.ReactNode; color?: string; at?: number; style?: React.CSSProperties }> = ({ children, color = C.orange, at = 0, style }) => {
  const p = useAppear(at);
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10, padding: "12px 24px", borderRadius: 999, border: `2px solid ${color}`, background: `${color}1A`, color: C.text, fontFamily: SANS, fontWeight: 600, fontSize: 28, opacity: p, transform: `scale(${0.7 + 0.3 * p})`, whiteSpace: "nowrap", ...style }}>
      {children}
    </div>
  );
};

export const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties; color?: string; active?: number }> = ({ children, style, color = C.line, active = 0 }) => (
  <div style={{ background: C.panel, borderRadius: 24, border: `2px solid ${active ? color : C.line}`, boxShadow: active ? `0 0 ${50 * active}px ${color}55` : "0 10px 30px #0006", padding: 32, fontFamily: SANS, color: C.text, ...style }}>{children}</div>
);
