import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver, which Radix popovers use to size themselves.
globalThis.ResizeObserver ??= class {
  constructor(readonly callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};
