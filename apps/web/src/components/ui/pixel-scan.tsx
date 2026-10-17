"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type PixelScanProps = {
  /** 0..1. Shows a band at that height, with everything below it veiled. Omit to loop forever. */
  progress?: number;
  /** When this value changes, play one short sweep and then clear. Ignores `progress`. */
  trigger?: number;
  /** Text revealed in pixels where the band passes over it. */
  label?: string;
  /** Pixel size in CSS px. */
  cell?: number;
  /** Draws nothing at all. */
  idle?: boolean;
  className?: string;
};

const LOOP_MS = 2600;
const SWEEP_MS = 800;

/** A cheap deterministic per-cell flicker in 0..1. */
function noise(col: number, row: number, tick: number): number {
  let h = (Math.imul(col, 73856093) ^ Math.imul(row, 19349663) ^ Math.imul(tick, 83492791)) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 2246822519) >>> 0;
  return h / 4294967296;
}

/**
 * A canvas that scans a band of animated pixels down whatever sits under it, lighting up a text
 * mask as it passes. Decorative only: it is aria-hidden and ignores pointer events, so the real
 * progress text must live in the DOM. Colour comes from the CSS `color` of the element and the
 * veil from the `--paper` custom property (dark fallback). Pauses off screen; with reduced motion it
 * draws one still frame and never animates.
 */
export function PixelScan({ progress, trigger, label = "", cell = 6, idle = false, className }: PixelScanProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const live = useRef({ progress, trigger, label, cell, idle });
  const redraw = useRef<() => void>(() => {});

  // Props are read inside the frame loop, so changing them never tears the loop down.
  useEffect(() => {
    live.current = { progress, trigger, label, cell, idle };
    redraw.current();
  }, [progress, trigger, label, cell, idle]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

    let width = 0;
    let height = 0;
    let cols = 0;
    let rows = 0;
    let mask = new Uint8Array(0);
    let maskKey = "";
    let frame = 0;
    let visible = true;
    let shown = 0; // eased progress actually drawn
    let sweepStart = -1;
    let lastTrigger = live.current.trigger;

    const buildMask = () => {
      const { label: text, cell: size } = live.current;
      const key = `${text}|${size}|${cols}|${rows}`;
      if (key === maskKey) return;
      maskKey = key;
      mask = new Uint8Array(cols * rows);
      if (!text || cols < 4 || rows < 4) return;
      const off = document.createElement("canvas");
      off.width = cols;
      off.height = rows;
      const octx = off.getContext("2d");
      if (!octx) return;
      octx.fillStyle = "#fff";
      octx.textAlign = "center";
      octx.textBaseline = "middle";
      let font = Math.min(rows * 0.3, cols * 0.2);
      octx.font = `700 ${font}px ui-sans-serif, system-ui, sans-serif`;
      const measured = octx.measureText(text).width;
      if (measured > cols * 0.86) {
        font *= (cols * 0.86) / measured;
        octx.font = `700 ${font}px ui-sans-serif, system-ui, sans-serif`;
      }
      octx.fillText(text, cols / 2, rows / 2);
      const data = octx.getImageData(0, 0, cols, rows).data;
      for (let i = 0; i < cols * rows; i += 1) mask[i] = data[i * 4 + 3] > 110 ? 1 : 0;
    };

    const resize = () => {
      const box = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, Math.round(box.width));
      height = Math.max(1, Math.round(box.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const size = live.current.cell;
      cols = Math.ceil(width / size);
      rows = Math.ceil(height / size);
      maskKey = "";
    };

    const draw = (now: number) => {
      const { progress: target, cell: size, idle: off } = live.current;
      ctx.clearRect(0, 0, width, height);
      if (off) return;
      buildMask();
      const once = sweepStart >= 0;
      let position: number;
      const band = Math.max(40, height * 0.3);
      if (once) {
        const t = Math.min(1, (now - sweepStart) / SWEEP_MS);
        position = t * (height + band);
        if (t >= 1) sweepStart = -1;
      } else if (target === undefined) {
        position = (((now % LOOP_MS) / LOOP_MS) * (height + band)) | 0;
      } else {
        shown += (target - shown) * (reduce.matches ? 1 : 0.08);
        position = shown * (height + band);
      }
      if (!once && target !== undefined) {
        const style = getComputedStyle(canvas);
        const paper = style.getPropertyValue("--paper").trim() || "#101010";
        ctx.globalAlpha = 0.72;
        ctx.fillStyle = paper;
        ctx.fillRect(0, Math.min(height, position), width, height);
        ctx.globalAlpha = 1;
      }
      const color = getComputedStyle(canvas).color;
      ctx.fillStyle = color;
      const tick = Math.floor(now / 90);
      const top = position - band;
      const firstRow = Math.max(0, Math.floor(top / size));
      const lastRow = Math.min(rows - 1, Math.floor(position / size));
      for (let r = firstRow; r <= lastRow; r += 1) {
        const depth = Math.min(1, Math.max(0, (r * size - top) / band)); // 0 at the tail, 1 at the leading edge
        for (let c = 0; c < cols; c += 1) {
          const lit = mask[r * cols + c] === 1;
          const flicker = noise(c, r, tick);
          const alpha = lit ? 0.55 + 0.45 * flicker : depth * depth * flicker * 0.75;
          if (alpha < 0.04) continue;
          ctx.globalAlpha = alpha;
          ctx.fillRect(c * size, r * size, size - 1, size - 1);
        }
      }
      ctx.globalAlpha = 0.9;
      if (position > 0 && position < height + band) ctx.fillRect(0, Math.min(height - 1, position), width, 1);
      ctx.globalAlpha = 1;
    };

    const animating = () =>
      !reduce.matches && visible && !live.current.idle && (sweepStart >= 0 || live.current.progress === undefined || Math.abs((live.current.progress ?? 0) - shown) > 0.002);

    const loop = (now: number) => {
      frame = 0;
      const { trigger: current } = live.current;
      if (current !== lastTrigger) {
        lastTrigger = current;
        if (!reduce.matches) sweepStart = now;
      }
      draw(now);
      if (animating()) frame = requestAnimationFrame(loop);
    };
    const start = () => {
      if (!frame) frame = requestAnimationFrame(loop);
    };
    redraw.current = start;

    const resizeObserver = new ResizeObserver(() => {
      resize();
      start();
    });
    resizeObserver.observe(canvas);
    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
    });
    intersection.observe(canvas);
    const onMotion = () => start();
    reduce.addEventListener("change", onMotion);
    resize();
    start();
    return () => {
      if (frame) cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      intersection.disconnect();
      reduce.removeEventListener("change", onMotion);
      redraw.current = () => {};
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className={cn("pointer-events-none block", className)} />;
}
