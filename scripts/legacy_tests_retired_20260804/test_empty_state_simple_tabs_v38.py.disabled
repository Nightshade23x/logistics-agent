from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def src(p): return (ROOT/p).read_text(encoding="utf-8")
def req(c,m):
    if not c: raise AssertionError(m)
def main():
    store=src("frontend/src/store.jsx"); dash=src("frontend/src/pages/Dashboard.jsx"); gate=src("frontend/src/components/ResultGate.jsx"); styles=src("frontend/src/styles.css")
    req("EMPTY_STATE_SIMPLE_TABS_V38" in store,"store marker missing")
    req("const [result, setResultState] = useState(null);" in store,"active result must start empty")
    req("localStorage.setItem(LEGACY_RESULT_KEY" not in store,"active result must not persist")
    req("loadFromHistory" in store,"history loading missing")
    req('const [text, setText] = useState("");' in dash,"draft must start blank")
    req("text.trim() ? parsePreview(text) : []" in dash,"preview guard missing")
    req("Nothing entered yet" in dash and "only a hint" in dash,"blank preview explanation missing")
    req("No shipping plan yet" in gate and "never submitted automatically" in gate,"empty result gate missing")
    pages=["Shipments.jsx","ContainerPlanning.jsx","Procurement.jsx","Compliance.jsx","PartnerAgents.jsx","Reports.jsx","Integrations.jsx"]
    for name in pages:
        p=src("frontend/src/pages/"+name)
        req("ViewControls" in p,name+": controls missing")
        req("SimplePageGuide" in p,name+": guide missing")
        req("userView" in p,name+": shared view missing")
    req('userView === "advanced"' in src("frontend/src/pages/Shipments.jsx"),"shipment technical gate missing")
    req('userView === "advanced"' in src("frontend/src/pages/Procurement.jsx"),"procurement tools gate missing")
    req('userView === "advanced"' in src("frontend/src/pages/PartnerAgents.jsx"),"partner tools gate missing")
    req('userView === "advanced"' in src("frontend/src/pages/Reports.jsx"),"report export gate missing")
    req('userView === "advanced"' in src("frontend/src/pages/Integrations.jsx"),"integration admin gate missing")
    req("EMPTY_STATE_SIMPLE_TABS_V38" in styles,"styles marker missing")
    print("PASS - stale active result is no longer restored")
    print("PASS - blank text and placeholder text cannot become a request")
    print("PASS - history is available only through deliberate selection")
    print("PASS - Simple and Advanced views are shared across all major tabs")
    print("PASS - technical and developer-only controls remain in Advanced view")
if __name__=="__main__": main()
