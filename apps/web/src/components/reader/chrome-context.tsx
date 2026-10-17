"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { DEFAULT_VIEW, VIEW_MODES, type ViewMode } from "./model";

const VIEW_KEY = "nh:view";

/** The edition on screen, as far as the toolbar needs to know (for the PDF button). */
export type ActiveEdition = { date: string; ready: boolean } | null;

type Chrome = {
  view: ViewMode;
  setView: (view: ViewMode) => void;
  query: string;
  setQuery: (query: string) => void;
  /** null = the responsive default: open on wide screens, closed below. */
  panelOpen: boolean | null;
  setPanelOpen: (open: boolean | null) => void;
  /** After picking something in the panel: on phones the panel is a drawer, so put it away. */
  closeDrawer: () => void;
  edition: ActiveEdition;
  setEdition: (edition: ActiveEdition) => void;
};

const ChromeContext = createContext<Chrome | null>(null);

function readStoredView(): ViewMode {
  try {
    const stored = window.localStorage.getItem(VIEW_KEY);
    return VIEW_MODES.find((mode) => mode === stored) ?? DEFAULT_VIEW;
  } catch {
    return DEFAULT_VIEW;
  }
}

/** State shared by the toolbar, the panel and the article pane: view mode, search, panel, PDF. */
export function ChromeProvider({ children }: { children: ReactNode }) {
  const [view, setViewState] = useState<ViewMode>(DEFAULT_VIEW);
  const [query, setQuery] = useState("");
  const [panelOpen, setPanelOpen] = useState<boolean | null>(null);
  const [edition, setEdition] = useState<ActiveEdition>(null);

  // The saved view is only known in the browser, so it is applied after hydration.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading browser storage
    setViewState(readStoredView());
  }, []);

  const setView = useCallback((next: ViewMode) => {
    setViewState(next);
    try {
      window.localStorage.setItem(VIEW_KEY, next);
    } catch {
      // private mode: the choice just lasts for this visit
    }
  }, []);

  const closeDrawer = useCallback(() => {
    if (window.matchMedia("(max-width: 767px)").matches) setPanelOpen(null);
  }, []);

  const value = useMemo(
    () => ({ view, setView, query, setQuery, panelOpen, setPanelOpen, closeDrawer, edition, setEdition }),
    [view, setView, query, panelOpen, closeDrawer, edition],
  );
  return <ChromeContext.Provider value={value}>{children}</ChromeContext.Provider>;
}

export function useChrome(): Chrome {
  const chrome = useContext(ChromeContext);
  if (!chrome) throw new Error("useChrome must be used inside <ChromeProvider>");
  return chrome;
}

/** Tell the toolbar which edition is on screen; clears it when the page goes away. */
export function useActiveEdition(edition: ActiveEdition): void {
  const { setEdition } = useChrome();
  const date = edition?.date;
  const ready = edition?.ready;
  useEffect(() => {
    setEdition(date ? { date, ready: Boolean(ready) } : null);
    return () => setEdition(null);
  }, [date, ready, setEdition]);
}
