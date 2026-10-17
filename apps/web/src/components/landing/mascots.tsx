/**
 * The cast: sixteen original, fictional topic mascots drawn as flat SVG "puppet" portraits.
 * They are illustrations of topics, not people and not reporters. No image model was used; the
 * clay look is approximated with flat shapes, a darker shade and a soft highlight.
 */
export type Mascot = {
  slug: string;
  /** Matches a real topic in the API taxonomy. */
  label: string;
  head: string;
  shade: string;
  hair: string;
  hairStyle: 0 | 1 | 2 | 3;
  glasses: 0 | 1 | 2;
  jacket: string;
  shirt: string;
  tie: string | null;
};

export const MASCOTS: readonly Mascot[] = [
  { slug: "tech", label: "Technology", head: "#3fb5a8", shade: "#2f8f85", hair: "#2b2b3a", hairStyle: 0, glasses: 0, jacket: "#3b4a6b", shirt: "#f3efe6", tie: "#f2b544" },
  { slug: "science", label: "Science", head: "#a7cc52", shade: "#85a63d", hair: "#e9e2d0", hairStyle: 2, glasses: 1, jacket: "#5b4b7a", shirt: "#f3efe6", tie: null },
  { slug: "business", label: "Business", head: "#f2b544", shade: "#cf9330", hair: "#6b3f2a", hairStyle: 1, glasses: 2, jacket: "#2f3a44", shirt: "#d9e6f2", tie: "#c8473a" },
  { slug: "music", label: "Music", head: "#b79ced", shade: "#9479cc", hair: "#e8633f", hairStyle: 2, glasses: 0, jacket: "#7a2f4b", shirt: "#f3efe6", tie: null },
  { slug: "football", label: "Football", head: "#e8715a", shade: "#c4543f", hair: "#3a2a22", hairStyle: 3, glasses: 1, jacket: "#2e5a43", shirt: "#f3efe6", tie: null },
  { slug: "world", label: "World", head: "#62a8e5", shade: "#4a89c4", hair: "#f0b93a", hairStyle: 0, glasses: 2, jacket: "#7a4a2e", shirt: "#f7f2e4", tie: "#2f5f8a" },
  { slug: "health", label: "Health", head: "#f08db5", shade: "#cc6f97", hair: "#4b2c55", hairStyle: 1, glasses: 0, jacket: "#3a6a6a", shirt: "#f3efe6", tie: null },
  { slug: "climate", label: "Climate & Environment", head: "#7fc47a", shade: "#5fa05b", hair: "#2f4a2a", hairStyle: 3, glasses: 2, jacket: "#8a6a2f", shirt: "#f3efe6", tie: null },
  { slug: "space", label: "Space", head: "#8e8bf0", shade: "#6d6acf", hair: "#f2f2f2", hairStyle: 2, glasses: 1, jacket: "#232a4a", shirt: "#e8e4f5", tie: "#f2b544" },
  { slug: "food", label: "Food", head: "#f28c3c", shade: "#cf6f26", hair: "#2a2a2a", hairStyle: 0, glasses: 0, jacket: "#a8473a", shirt: "#f7f2e4", tie: null },
  { slug: "travel", label: "Travel", head: "#4fc3d9", shade: "#38a0b5", hair: "#8a4a2a", hairStyle: 1, glasses: 1, jacket: "#c98a2f", shirt: "#f3efe6", tie: null },
  { slug: "books", label: "Books", head: "#d98acb", shade: "#b56ba8", hair: "#3b2a1f", hairStyle: 3, glasses: 2, jacket: "#4a5a3a", shirt: "#f3efe6", tie: "#7a2f4b" },
  { slug: "markets", label: "Markets", head: "#e6c24a", shade: "#c2a030", hair: "#1f1f1f", hairStyle: 0, glasses: 1, jacket: "#2e4a6b", shirt: "#d9e6f2", tie: "#2e5a43" },
  { slug: "cricket", label: "Cricket", head: "#e56a7a", shade: "#c24f60", hair: "#f2d36b", hairStyle: 2, glasses: 0, jacket: "#3a5a8a", shirt: "#f3efe6", tie: null },
  { slug: "design", label: "Design & Architecture", head: "#5bd0b0", shade: "#3fa88b", hair: "#7a3a6b", hairStyle: 1, glasses: 2, jacket: "#3a3a3a", shirt: "#f3efe6", tie: "#e8715a" },
  { slug: "gaming", label: "Gaming", head: "#a6d44f", shade: "#82ad37", hair: "#5a2a8a", hairStyle: 3, glasses: 1, jacket: "#a83a6b", shirt: "#f7f2e4", tie: null },
];

/** Fuzzy hair: a deterministic ring of overlapping circles whose count and spread depend on the style. */
function hairCircles(index: number, style: Mascot["hairStyle"]): { x: number; y: number; r: number }[] {
  const circles: { x: number; y: number; r: number }[] = [];
  const count = 11;
  for (let k = 0; k < count; k += 1) {
    const angle = Math.PI * (1.08 + (0.84 * k) / (count - 1));
    const r = 4 + ((k * 7 + index * 3) % 3) * 0.8;
    circles.push({ x: 28 + 16.2 * Math.cos(angle), y: 29 + 18.2 * Math.sin(angle), r });
  }
  if (style === 1) circles.push({ x: 15, y: 20, r: 5.5 }, { x: 12, y: 27, r: 4.2 }, { x: 22, y: 11, r: 5 });
  if (style === 2) circles.push({ x: 28, y: 7, r: 6 }, { x: 20, y: 9, r: 5 }, { x: 36, y: 9, r: 5 });
  if (style === 3) circles.push({ x: 13, y: 30, r: 4.6 }, { x: 43, y: 30, r: 4.6 });
  return circles;
}

/** One portrait on its own cream tile: 56 x 70, ready to be scaled by CSS. */
export function Portrait({ mascot, index }: { mascot: Mascot; index: number }) {
  const ink = "#1b1b1b";
  const eyes: [number, number][] = [
    [22, 31],
    [34, 31],
  ];
  return (
    <svg viewBox="0 0 56 70" width="56" height="70" aria-hidden="true" focusable="false" className="lp-portrait">
      <rect width="56" height="70" fill="#F0EEEB" />
      <path d="M3 70C3 55 13 49 28 49s25 6 25 21z" fill={mascot.jacket} />
      <rect x="23.5" y="43" width="9" height="9" rx="3" fill={mascot.shade} />
      <polygon points="19,49 28,63 37,49 33,47 28,53 23,47" fill={mascot.shirt} />
      {mascot.tie ? <path d="M26.2 55.5h3.6l1.4 9h-6.4z" fill={mascot.tie} /> : null}
      <circle cx="12.5" cy="32" r="3.6" fill={mascot.head} />
      <circle cx="43.5" cy="32" r="3.6" fill={mascot.head} />
      <ellipse cx="28" cy="30" rx="15" ry="17" fill={mascot.head} />
      <path d="M13.5 36c3 11 10 14.5 14.5 14.5s11.5-3.5 14.5-14.5c-3 6-9 9-14.5 9s-11.5-3-14.5-9z" fill={mascot.shade} opacity=".55" />
      {hairCircles(index, mascot.hairStyle).map((c, k) => (
        <circle key={k} cx={c.x.toFixed(2)} cy={c.y.toFixed(2)} r={c.r} fill={mascot.hair} />
      ))}
      <ellipse cx="21" cy="21.5" rx="5" ry="2.2" fill="#fff" opacity=".16" />
      <circle cx="18" cy="37" r="2.8" fill="#e8402f" opacity=".16" />
      <circle cx="38" cy="37" r="2.8" fill="#e8402f" opacity=".16" />
      {eyes.map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r="1.8" fill={ink} />
      ))}
      <ellipse cx="28" cy="35.5" rx="2.1" ry="1.6" fill={mascot.shade} />
      <path d="M23.5 40.5q4.5 3.8 9 0" fill="none" stroke={ink} strokeWidth="1.4" strokeLinecap="round" />
      {mascot.glasses === 0 ? (
        <g fill="none" stroke={ink} strokeWidth="1.3">
          <circle cx="22" cy="31" r="5.2" />
          <circle cx="34" cy="31" r="5.2" />
          <path d="M27.2 30.5h1.6" />
        </g>
      ) : mascot.glasses === 1 ? (
        <g fill="none" stroke={ink} strokeWidth="1.3">
          <rect x="16.5" y="26.5" width="10" height="8.5" rx="2.5" />
          <rect x="29.5" y="26.5" width="10" height="8.5" rx="2.5" />
          <path d="M26.5 30h3" />
        </g>
      ) : (
        <g fill="none" stroke={ink} strokeWidth="2">
          <circle cx="22" cy="31" r="4.8" />
          <circle cx="34" cy="31" r="4.8" />
          <path d="M26.8 30.5h2.4" />
        </g>
      )}
    </svg>
  );
}
