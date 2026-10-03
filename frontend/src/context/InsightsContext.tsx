import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { BillAnalysis, BillReadingInput } from "../api/client";

/**
 * Shares the resident's bill readings + analysis across pages, so the
 * What-If simulator can start from their own forecast and Volt (the chat
 * assistant) can answer questions about "my bill". Kept in sessionStorage
 * only — nothing about a household's bills is persisted server-side.
 */
interface InsightsState {
  readings: BillReadingInput[];
  setReadings: (r: BillReadingInput[]) => void;
  analysis: BillAnalysis | null;
  setAnalysis: (a: BillAnalysis | null) => void;
}

const InsightsContext = createContext<InsightsState | null>(null);
const STORAGE_KEY = "wattwise.insights.v1";

function load(): { readings: BillReadingInput[]; analysis: BillAnalysis | null } {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* storage blocked — start empty */
  }
  return { readings: [], analysis: null };
}

export function InsightsProvider({ children }: { children: ReactNode }) {
  const [initial] = useState(load);
  const [readings, setReadings] = useState<BillReadingInput[]>(initial.readings);
  const [analysis, setAnalysis] = useState<BillAnalysis | null>(initial.analysis);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ readings, analysis }));
    } catch {
      /* ignore */
    }
  }, [readings, analysis]);

  return (
    <InsightsContext.Provider value={{ readings, setReadings, analysis, setAnalysis }}>
      {children}
    </InsightsContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useInsights(): InsightsState {
  const ctx = useContext(InsightsContext);
  if (!ctx) throw new Error("useInsights must be used inside InsightsProvider");
  return ctx;
}
