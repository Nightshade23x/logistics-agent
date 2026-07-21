import { createContext, useContext, useEffect, useState, useCallback } from "react";

const StoreContext = createContext(null);

const RESULT_KEY = "meridian.lastResult";
const HISTORY_KEY = "meridian.history";

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function StoreProvider({ children }) {
  const [result, setResultState] = useState(() => loadJson(RESULT_KEY, null));
  const [history, setHistoryState] = useState(() => loadJson(HISTORY_KEY, []));

  useEffect(() => {
    if (result) localStorage.setItem(RESULT_KEY, JSON.stringify(result));
  }, [result]);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }, [history]);

  const setResult = useCallback((payload, meta) => {
    setResultState(payload);
    setHistoryState((prev) => {
      const entry = {
        id: `${Date.now()}`,
        timestamp: new Date().toISOString(),
        requestType: payload?.request_metadata?.request_type || "unknown",
        label: meta?.label || payload?.request_metadata?.input_source || "request",
        decision: payload?.decision,
        detectedIntent: payload?.detected_intent,
        payload,
      };
      return [entry, ...prev].slice(0, 25);
    });
  }, []);

  const loadFromHistory = useCallback(
    (id) => {
      const entry = history.find((h) => h.id === id);
      if (entry) setResultState(entry.payload);
    },
    [history]
  );

  const clearAll = useCallback(() => {
    setResultState(null);
    setHistoryState([]);
    localStorage.removeItem(RESULT_KEY);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  return (
    <StoreContext.Provider value={{ result, history, setResult, loadFromHistory, clearAll }}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}
