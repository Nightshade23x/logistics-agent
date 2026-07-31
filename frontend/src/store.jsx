import { createContext, useContext, useEffect, useState, useCallback } from "react";

const StoreContext = createContext(null);
const LEGACY_RESULT_KEY = "meridian.lastResult";
const HISTORY_KEY = "meridian.history";
const USER_VIEW_KEY = "meridian.user.view";
const FONT_SCALE_KEY = "meridian.user.fontScale";

// EMPTY_STATE_SIMPLE_TABS_V38
// The active result is session-only. History may persist, but an old result is
// never silently presented as a request from the current session.
function loadJson(key, fallback) {
  try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }
  catch { return fallback; }
}
function loadString(key, fallback) {
  try { const raw = localStorage.getItem(key); return raw === null ? fallback : raw; }
  catch { return fallback; }
}

export function StoreProvider({ children }) {
  const [result, setResultState] = useState(null);
  const [history, setHistoryState] = useState(() => loadJson(HISTORY_KEY, []));
  const [userView, setUserView] = useState(() => loadString(USER_VIEW_KEY, "simple"));
  const [fontScale, setFontScale] = useState(() => loadString(FONT_SCALE_KEY, "normal"));

  useEffect(() => { localStorage.removeItem(LEGACY_RESULT_KEY); }, []);
  useEffect(() => { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); }, [history]);
  useEffect(() => {
    localStorage.setItem(USER_VIEW_KEY, userView);
    localStorage.setItem(FONT_SCALE_KEY, fontScale);
    document.documentElement.dataset.fontScale = fontScale;
  }, [userView, fontScale]);

  useEffect(() => {
    function parse(value, fallback) { try { return value ? JSON.parse(value) : fallback; } catch { return fallback; } }
    function onStorage(event) {
      if (event.key === HISTORY_KEY) setHistoryState(parse(event.newValue, []));
      if (event.key === USER_VIEW_KEY && event.newValue) setUserView(event.newValue);
      if (event.key === FONT_SCALE_KEY && event.newValue) setFontScale(event.newValue);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setResult = useCallback((payload, meta) => {
    setResultState(payload);
    setHistoryState((prev) => [{
      id: `${Date.now()}`,
      timestamp: new Date().toISOString(),
      requestType: payload?.request_metadata?.request_type || "unknown",
      label: meta?.label || payload?.request_metadata?.input_source || "request",
      decision: payload?.decision,
      status: payload?.status,
      detectedIntent: payload?.detected_intent,
      payload,
    }, ...prev].slice(0, 25));
  }, []);

  const loadFromHistory = useCallback((id) => {
    const entry = history.find((item) => item.id === id);
    if (entry) setResultState(entry.payload);
  }, [history]);
  const clearCurrent = useCallback(() => { setResultState(null); localStorage.removeItem(LEGACY_RESULT_KEY); }, []);
  const clearAll = useCallback(() => {
    setResultState(null); setHistoryState([]);
    localStorage.removeItem(LEGACY_RESULT_KEY); localStorage.removeItem(HISTORY_KEY);
  }, []);

  return <StoreContext.Provider value={{ result, history, setResult, loadFromHistory, clearCurrent, clearAll, userView, setUserView, fontScale, setFontScale }}>{children}</StoreContext.Provider>;
}
export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}
