import { useStore } from "../store.jsx";
// EMPTY_STATE_SIMPLE_TABS_V38
export default function ViewControls({ compact = false }) {
  const { userView, setUserView, fontScale, setFontScale } = useStore();
  return <div className={`accessibility-controls${compact ? " compact" : ""}`} aria-label="Display preferences">
    <div className="view-toggle" role="group" aria-label="Information detail">
      <button type="button" className={userView === "simple" ? "active" : ""} aria-pressed={userView === "simple"} onClick={() => setUserView("simple")}>Simple view</button>
      <button type="button" className={userView === "advanced" ? "active" : ""} aria-pressed={userView === "advanced"} onClick={() => setUserView("advanced")}>Advanced view</button>
    </div>
    <div className="font-scale-controls" role="group" aria-label="Text size">
      <span>Text size</span>
      {["compact", "normal", "large"].map((value, index) => <button type="button" key={value} className={fontScale === value ? "active" : ""} aria-pressed={fontScale === value} aria-label={`${value} text`} onClick={() => setFontScale(value)}>{index === 0 ? "A−" : index === 1 ? "A" : "A+"}</button>)}
    </div>
  </div>;
}
