"use client";

import { useEffect, useRef } from "react";

import { LAND_COLS, LAND_MASK, LAND_ROWS } from "./land-mask";
import { MASCOTS, Portrait } from "./mascots";

const POINTS = 5200;
const TILT = (-18 * Math.PI) / 180; // lean the north pole slightly toward the viewer
const SPEED = 0.07; // radians per second: one turn in about 90 seconds
const START_LON = (-15 * Math.PI) / 180;

/** Topic desks pinned to regions. Decorative: they mark topics, not people or reporters. */
const PINS = [
  { label: "World", lat: 47, lon: 10 },
  { label: "Climate & Environment", lat: -6, lon: -62 },
  { label: "Markets", lat: 31, lon: 112 },
  { label: "Travel", lat: -26, lon: 135 },
].map((pin) => {
  const index = MASCOTS.findIndex((m) => m.label === pin.label);
  return { ...pin, mascot: MASCOTS[index], index };
});

function landAt(lat: number, lon: number): boolean {
  const col = Math.min(LAND_COLS - 1, Math.floor(((lon + 180) / 360) * LAND_COLS));
  const row = Math.min(LAND_ROWS - 1, Math.floor(((90 - lat) / 180) * LAND_ROWS));
  const i = row * LAND_COLS + col;
  return (bytes()[i >> 3] & (1 << (i & 7))) !== 0;
}

let decoded: Uint8Array | null = null;
function bytes(): Uint8Array {
  if (!decoded) decoded = Uint8Array.from(atob(LAND_MASK), (ch) => ch.charCodeAt(0));
  return decoded;
}

/** Evenly spread points on a unit sphere that fall on land: [x, y, z] triples. */
function landPoints(): Float32Array {
  const out: number[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < POINTS; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / POINTS;
    const radius = Math.sqrt(1 - y * y);
    const lon = ((golden * i) % (2 * Math.PI)) - Math.PI;
    const lat = Math.asin(y);
    if (landAt((lat * 180) / Math.PI, (lon * 180) / Math.PI)) out.push(radius * Math.sin(lon), y, radius * Math.cos(lon));
  }
  return new Float32Array(out);
}

/**
 * A dot-matrix globe drawn on a 2D canvas (no 3D library). Land comes from a packed 2-degree mask,
 * the sphere turns slowly, and topic mascots sit on tethers. Purely decorative, so it is aria-hidden;
 * with reduced motion it draws one still frame, and it stops drawing while off screen.
 */
export function Globe() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pinRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!wrap || !canvas || !ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const points = landPoints();
    const probe = (name: string) => wrap.querySelector<HTMLElement>(`.lp-gc--${name}`);
    const palette = { disc: "#242424", dot: "#c9d6b8", rim: "#3b3833" };
    const readPalette = () => {
      for (const key of ["disc", "dot", "rim"] as const) {
        const el = probe(key);
        if (el) palette[key] = getComputedStyle(el).backgroundColor;
      }
    };
    readPalette();
    let size = 0;
    let frame = 0;
    let visible = true;
    let angle = START_LON;
    let last = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      size = Math.max(1, Math.round(wrap.getBoundingClientRect().width));
      canvas.width = Math.round(size * dpr);
      canvas.height = Math.round(size * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const project = (x: number, y: number, z: number, rot: number, r: number, c: number) => {
      const rx = x * Math.cos(rot) + z * Math.sin(rot);
      const rz = -x * Math.sin(rot) + z * Math.cos(rot);
      const ty = y * Math.cos(TILT) - rz * Math.sin(TILT);
      const tz = y * Math.sin(TILT) + rz * Math.cos(TILT);
      return { sx: c + rx * r, sy: c - ty * r, depth: tz };
    };

    const draw = () => {
      const c = size / 2;
      const r = size * 0.36;
      ctx.clearRect(0, 0, size, size);
      ctx.beginPath();
      ctx.arc(c, c, r, 0, Math.PI * 2);
      ctx.fillStyle = palette.disc;
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = palette.rim;
      ctx.stroke();
      const dot = Math.max(1.1, size / 330);
      ctx.fillStyle = palette.dot;
      for (let i = 0; i < points.length; i += 3) {
        const p = project(points[i], points[i + 1], points[i + 2], angle, r, c);
        if (p.depth <= 0.02) continue;
        ctx.globalAlpha = 0.18 + 0.72 * p.depth;
        ctx.fillRect(p.sx - dot / 2, p.sy - dot / 2, dot, dot);
      }
      ctx.globalAlpha = 1;
      PINS.forEach((pin, i) => {
        const el = pinRefs.current[i];
        if (!el) return;
        const lat = (pin.lat * Math.PI) / 180;
        const lon = (pin.lon * Math.PI) / 180;
        const p = project(Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon), angle, r, c);
        const front = p.depth > 0.2;
        const dx = p.sx - c;
        const dy = p.sy - c;
        const len = Math.hypot(dx, dy) || 1;
        const reach = size * 0.09;
        const px = p.sx + (dx / len) * reach;
        const py = p.sy + (dy / len) * reach;
        if (front) {
          ctx.globalAlpha = 0.55;
          ctx.strokeStyle = palette.dot;
          ctx.beginPath();
          ctx.moveTo(p.sx, p.sy);
          ctx.lineTo(px, py);
          ctx.stroke();
          ctx.globalAlpha = 1;
          ctx.fillStyle = palette.dot;
          ctx.fillRect(p.sx - 1.5, p.sy - 1.5, 3, 3);
        }
        el.style.transform = `translate(${px.toFixed(1)}px, ${py.toFixed(1)}px) translate(-50%, -50%)`;
        el.style.opacity = front ? "1" : "0";
      });
    };

    const loop = (now: number) => {
      frame = 0;
      if (last) angle += ((now - last) / 1000) * SPEED;
      last = now;
      draw();
      if (visible && !reduce.matches) frame = requestAnimationFrame(loop);
    };
    const start = () => {
      last = 0;
      if (!frame) frame = requestAnimationFrame(loop);
    };

    const resizeObserver = new ResizeObserver(() => {
      resize();
      start();
    });
    resizeObserver.observe(wrap);
    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
    });
    intersection.observe(wrap);
    reduce.addEventListener("change", start);
    // the theme flips a class on <html>: re-read the three colours and repaint
    const themeObserver = new MutationObserver(() => {
      readPalette();
      start();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    resize();
    start();
    return () => {
      themeObserver.disconnect();
      if (frame) cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      intersection.disconnect();
      reduce.removeEventListener("change", start);
    };
  }, []);

  return (
    <div ref={wrapRef} className="lp-globe" aria-hidden="true">
      <canvas ref={canvasRef} />
      <i className="lp-gc lp-gc--disc" />
      <i className="lp-gc lp-gc--dot" />
      <i className="lp-gc lp-gc--rim" />
      {PINS.map((pin, i) => (
        <div
          key={pin.label}
          className="lp-pin"
          ref={(el) => {
            pinRefs.current[i] = el;
          }}
        >
          <Portrait mascot={pin.mascot} index={pin.index} />
        </div>
      ))}
    </div>
  );
}
