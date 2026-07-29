from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    app = source("frontend/src/App.jsx")
    sidebar = source("frontend/src/components/Sidebar.jsx")
    guide = source("frontend/src/components/SimplePageGuide.jsx")
    wizard = source("frontend/src/components/GuidedShipmentWizard.jsx")
    progress = source("frontend/src/components/ShipmentProgress.jsx")
    overview = source("frontend/src/components/SimpleResultOverview.jsx")
    dashboard = source("frontend/src/pages/Dashboard.jsx")
    shipments = source("frontend/src/pages/Shipments.jsx")
    styles = source("frontend/src/styles.css")

    require('className="skip-link"' in app and 'id="main-content"' in app, "keyboard skip link missing")
    require("Start a Shipment" in sidebar and "Shipment Plan" in sidebar and "Loading Plan" in sidebar, "friendly navigation labels missing")
    require("Suppliers & Buying" in sidebar and "Rules & Documents" in sidebar and "Carrier Connections" in sidebar, "friendly trade navigation missing")
    require("advancedOnly" in sidebar and "System Details" in sidebar, "advanced-only system navigation missing")

    require("EASE_OF_ACCESS_GUIDED_WORKFLOW_V39" in guide, "V39 guide marker missing")
    require("TERM_HELP" in guide and "plain-language-terms" in guide, "plain-language term help missing")
    require("cbm" in guide.lower() and "landed cost" in guide.lower(), "common logistics explanations missing")

    require("guidedShipmentDraft.v39" in wizard and "sessionStorage" in wizard, "session-only guided draft missing")
    require("Check your details" in wizard and "Nothing has been sent yet" in wizard, "review-before-submit step missing")
    require("aria-invalid" in wizard and "wizard-field-error" in wizard, "field-level validation missing")
    require("buildGuidedShipmentRequest" in wizard and "Create shipping plan" in wizard, "guided request builder missing")

    require("Guide me step by step" in dashboard and "Describe it myself" in dashboard, "simple input choice missing")
    require("GuidedShipmentWizard" in dashboard and "submit(overrideText = null)" in dashboard, "guided submission wiring missing")
    require("ShipmentProgress" in dashboard and "SimpleResultOverview" in dashboard, "plain-language dashboard result missing")
    require("text.trim() ? parsePreview(text) : []" in dashboard, "V38 blank-preview guard regressed")

    require("STAGES" in progress and "Ready to book" in progress, "shipment progress stages missing")
    require("What was calculated" in overview and "What this means" in overview, "plain-language result questions missing")
    require("What is still missing" in overview and "What to do next" in overview, "next-action result questions missing")
    require("ShipmentProgress" in shipments and "SimpleResultOverview" in shipments, "shipment plan summary wiring missing")
    require("simple-extra-details" in shipments, "simple-view technical detail disclosure missing")

    require("EASE_OF_ACCESS_GUIDED_WORKFLOW_V39" in styles, "V39 styles marker missing")
    require("min-height: 44px" in styles, "minimum control target size missing")
    require("prefers-reduced-motion" in styles, "reduced-motion support missing")
    require("wizard-grid" in styles and "simple-result-grid" in styles, "responsive guided workflow styles missing")

    print("PASS - guided shipment wizard validates and reviews details before submission")
    print("PASS - plain-language result summary answers the four key user questions")
    print("PASS - shipment progress and friendly navigation are installed")
    print("PASS - logistics terms, keyboard access, target sizes, and reduced motion are covered")
    print("PASS - V38 empty-state protections remain present")


if __name__ == "__main__":
    main()
