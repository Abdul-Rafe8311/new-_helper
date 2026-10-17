"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useState,
  type Dispatch,
  type ReactNode,
} from "react";

import { applyPatches, type ItemStates, type StatePatch } from "./model";
import { FRONT_COLOR } from "./palette";

/** The edition on screen, as far as the masthead needs to know (for the PDF button). */
export type ActiveEdition = { date: string; ready: boolean } | null;

type Chrome = {
  /** The category colour that tints the glow and active pills. */
  accent: string;
  setAccent: (color: string) => void;
  menuOpen: boolean;
  setMenuOpen: (open: boolean) => void;
  edition: ActiveEdition;
  setEdition: (edition: ActiveEdition) => void;
  /** The reader's changes this visit; shared so a save on a story page shows on the feed. */
  states: ItemStates;
  patchStates: Dispatch<readonly StatePatch[]>;
};

const ChromeContext = createContext<Chrome | null>(null);

export function ChromeProvider({ children }: { children: ReactNode }) {
  const [accent, setAccent] = useState(FRONT_COLOR);
  const [menuOpen, setMenuOpen] = useState(false);
  const [edition, setEdition] = useState<ActiveEdition>(null);
  const [states, patchStates] = useReducer(applyPatches, {});

  const value = useMemo(
    () => ({ accent, setAccent, menuOpen, setMenuOpen, edition, setEdition, states, patchStates }),
    [accent, menuOpen, edition, states],
  );
  return <ChromeContext.Provider value={value}>{children}</ChromeContext.Provider>;
}

export function useChrome(): Chrome {
  const chrome = useContext(ChromeContext);
  if (!chrome) throw new Error("useChrome must be used inside <ChromeProvider>");
  return chrome;
}

/** Tell the masthead which edition is on screen; clears it when the page goes away. */
export function useActiveEdition(edition: ActiveEdition): void {
  const { setEdition } = useChrome();
  const date = edition?.date;
  const ready = edition?.ready;
  useEffect(() => {
    setEdition(date ? { date, ready: Boolean(ready) } : null);
    return () => setEdition(null);
  }, [date, ready, setEdition]);
}

/** Tint the page with a category colour while this view is on screen. */
export function useAccent(color: string): void {
  const { setAccent } = useChrome();
  useEffect(() => {
    setAccent(color);
  }, [color, setAccent]);
}

export function useCloseMenu(): () => void {
  const { setMenuOpen } = useChrome();
  return useCallback(() => setMenuOpen(false), [setMenuOpen]);
}
