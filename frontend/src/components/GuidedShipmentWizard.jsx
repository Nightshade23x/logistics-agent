import { useEffect, useMemo, useState } from "react";

const SESSION_KEY = "meridian.guidedShipmentDraft.v39";

const STEP_SESSION_KEY = "meridian.guidedShipmentStep.v61"; // GUIDED_STEP_PERSISTENCE_V61

const EMPTY_DRAFT = {
  origin: "",
  destination: "",
  cargoName: "",
  quantity: "",
  packageType: "crates",
  length: "",
  width: "",
  height: "",
  dimensionUnit: "m",
  weightPerPackage: "",
  weightUnit: "kg",
  fragile: "unknown",
  stackability: "unknown",
  hazardous: "unknown",
  incoterm: "",
  goal: "shipping_plan",
  budget: "",
  currency: "USD",
};

const STEPS = [
  { title: "Route", help: "Where is the shipment starting and where is it going?" },
  { title: "Cargo", help: "What are you shipping and how many packages are there?" },
  { title: "Measurements", help: "Add the packed size and weight of one package." },
  { title: "Handling and goal", help: "Tell us how the cargo should be handled and what help you need." },
  { title: "Check your details", help: "Review the generated request before anything is sent." },
];

function loadDraft() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? { ...EMPTY_DRAFT, ...JSON.parse(raw) } : EMPTY_DRAFT;
  } catch {
    return EMPTY_DRAFT;
  }
}

function loadStep() {
  try {
    const parsed = Number(sessionStorage.getItem(STEP_SESSION_KEY));
    return Number.isInteger(parsed) && parsed >= 0 && parsed < STEPS.length ? parsed : 0;
  } catch {
    return 0;
  }
}

function singularPackage(value) {
  const text = String(value || "package");
  if (text.endsWith("ies")) return `${text.slice(0, -3)}y`;
  if (text.endsWith("s")) return text.slice(0, -1);
  return text;
}

function goalLead(goal) {
  if (goal === "landed_cost") return "Calculate landed cost and create a shipping plan for";
  if (goal === "documents") return "List the required shipping and compliance documents for";
  if (goal === "suppliers") return "Find suppliers and create a shipping plan for";
  return "Ship";
}

export function buildGuidedShipmentRequest(draft) {
  const quantity = String(draft.quantity || "").trim();
  const packageType = String(draft.packageType || "packages").trim();
  const cargoName = String(draft.cargoName || "").trim();
  const origin = String(draft.origin || "").trim();
  const destination = String(draft.destination || "").trim();

  if (!quantity || !cargoName || !origin || !destination) return "";

  const incoterm = draft.incoterm ? ` using ${draft.incoterm}` : "";
  const sentences = [
    `${goalLead(draft.goal)} ${quantity} ${packageType} of ${cargoName} from ${origin} to ${destination}${incoterm}.`,
  ];

  const dimensions = [draft.length, draft.width, draft.height].map((value) => String(value || "").trim());
  const hasDimensions = dimensions.every(Boolean);
  const weight = String(draft.weightPerPackage || "").trim();
  const packageLabel = singularPackage(packageType);

  if (hasDimensions && weight) {
    sentences.push(`Each ${packageLabel} is ${dimensions.join(" x ")} ${draft.dimensionUnit} and weighs ${weight} ${draft.weightUnit}.`);
  } else if (hasDimensions) {
    sentences.push(`Each ${packageLabel} is ${dimensions.join(" x ")} ${draft.dimensionUnit}.`);
  } else if (weight) {
    sentences.push(`Each ${packageLabel} weighs ${weight} ${draft.weightUnit}.`);
  }

  const handling = [];
  if (draft.fragile === "yes") handling.push("fragile");
  if (draft.fragile === "no") handling.push("not fragile");
  if (draft.stackability === "stackable") handling.push("stackable");
  if (draft.stackability === "non_stackable") handling.push("non-stackable");
  if (draft.hazardous === "yes") handling.push("contains hazardous materials");
  if (draft.hazardous === "no") handling.push("does not contain hazardous materials");
  if (handling.length) sentences.push(`The cargo is ${handling.join(", ")}.`);

  const budget = String(draft.budget || "").trim();
  if (budget) sentences.push(`The working budget is ${budget} ${draft.currency}.`);

  return sentences.join(" ");
}

function FieldError({ id, children }) {
  if (!children) return null;
  return <div className="wizard-field-error" id={id} role="alert">{children}</div>;
}

function ReviewRow({ label, value }) {
  return <div className="wizard-review-row"><dt>{label}</dt><dd>{value || "Not provided"}</dd></div>;
}

export default function GuidedShipmentWizard({ loading = false, onDraftChange, onSubmit }) {
  const [draft, setDraft] = useState(loadDraft);
  const [step, setStep] = useState(loadStep);
  const [errors, setErrors] = useState({});
  const requestText = useMemo(() => buildGuidedShipmentRequest(draft), [draft]);

  useEffect(() => {
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(draft)); } catch { /* Session storage is optional. */ }
    onDraftChange?.(requestText);
  }, [draft, requestText, onDraftChange]);

  useEffect(() => {
    try { sessionStorage.setItem(STEP_SESSION_KEY, String(step)); } catch { /* Session storage is optional. */ }
  }, [step]);

  function update(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function focusFirstError(nextErrors) {
    const firstField = Object.keys(nextErrors)[0];
    if (!firstField) return;
    window.requestAnimationFrame(() => document.getElementById(`wizard-${firstField}`)?.focus());
  }

  function validateCurrentStep() {
    const nextErrors = {};

    if (step === 0) {
      if (!draft.origin.trim()) nextErrors.origin = "Enter the country or city where the shipment starts.";
      if (!draft.destination.trim()) nextErrors.destination = "Enter the country or city where the shipment is going.";
      if (draft.origin.trim() && draft.destination.trim() && draft.origin.trim().toLowerCase() === draft.destination.trim().toLowerCase()) {
        nextErrors.destination = "Origin and destination must be different.";
      }
    }

    if (step === 1) {
      if (!draft.cargoName.trim()) nextErrors.cargoName = "Enter the cargo name, for example ceramic tiles.";
      if (!draft.quantity || Number(draft.quantity) <= 0) nextErrors.quantity = "Enter a quantity greater than zero.";
    }

    if (step === 2) {
      const dimensions = [draft.length, draft.width, draft.height];
      const anyDimension = dimensions.some((value) => String(value || "").trim());
      const allDimensions = dimensions.every((value) => Number(value) > 0);
      if (anyDimension && !allDimensions) nextErrors.length = "Enter all three packed dimensions, or leave all three blank.";
      if (!draft.weightPerPackage || Number(draft.weightPerPackage) <= 0) nextErrors.weightPerPackage = "Enter the packed weight of one package.";
    }

    setErrors(nextErrors);
    focusFirstError(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function next() {
    if (!validateCurrentStep()) return;
    setStep((value) => Math.min(value + 1, STEPS.length - 1));
  }

  function back() {
    setErrors({});
    setStep((value) => Math.max(value - 1, 0));
  }

  function startOver() {
    setDraft(EMPTY_DRAFT);
    setErrors({});
    setStep(0);
    try {
      sessionStorage.removeItem(SESSION_KEY);
      sessionStorage.removeItem(STEP_SESSION_KEY);
    } catch { /* Session storage is optional. */ }
  }

  function submit() {
    if (!requestText) {
      setStep(0);
      setErrors({ origin: "Complete the required shipment details before creating a plan." });
      return;
    }
    onSubmit?.(requestText);
  }

  const progress = Math.round(((step + 1) / STEPS.length) * 100);

  return (
    <section className="guided-wizard" aria-labelledby="guided-wizard-title">
      <div className="guided-wizard-head">
        <div>
          <div className="guided-wizard-kicker">Guided shipment form</div>
          <h3 id="guided-wizard-title">{STEPS[step].title}</h3>
          <p>{STEPS[step].help}</p>
        </div>
        <button type="button" className="btn btn-quiet" onClick={startOver}>Start over</button>
      </div>

      <div className="wizard-progress" aria-label={`Step ${step + 1} of ${STEPS.length}`}>
        <div className="wizard-progress-label"><span>Step {step + 1} of {STEPS.length}</span><span>{progress}%</span></div>
        <div className="wizard-progress-track"><span style={{ width: `${progress}%` }} /></div>
      </div>

      <ol className="wizard-step-list" aria-label="Shipment form steps">
        {STEPS.map((item, index) => (
          <li className={index === step ? "current" : index < step ? "complete" : ""} aria-current={index === step ? "step" : undefined} key={item.title}>
            <span>{index < step ? "✓" : index + 1}</span><b>{item.title}</b>
          </li>
        ))}
      </ol>

      <div className="wizard-panel" aria-live="polite">
        {step === 0 && (
          <fieldset>
            <legend>Shipment route</legend>
            <div className="wizard-grid two">
              <div className="form-group">
                <label className="form-label" htmlFor="wizard-origin">Starting country or city</label>
                <input id="wizard-origin" className="form-input" value={draft.origin} onChange={(event) => update("origin", event.target.value)} placeholder="India" aria-invalid={Boolean(errors.origin)} aria-describedby={errors.origin ? "wizard-origin-error" : undefined} />
                <FieldError id="wizard-origin-error">{errors.origin}</FieldError>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="wizard-destination">Destination country or city</label>
                <input id="wizard-destination" className="form-input" value={draft.destination} onChange={(event) => update("destination", event.target.value)} placeholder="Germany" aria-invalid={Boolean(errors.destination)} aria-describedby={errors.destination ? "wizard-destination-error" : undefined} />
                <FieldError id="wizard-destination-error">{errors.destination}</FieldError>
              </div>
            </div>
          </fieldset>
        )}

        {step === 1 && (
          <fieldset>
            <legend>Cargo and quantity</legend>
            <div className="wizard-grid three">
              <div className="form-group wizard-span-two">
                <label className="form-label" htmlFor="wizard-cargoName">What are you shipping?</label>
                <input id="wizard-cargoName" className="form-input" value={draft.cargoName} onChange={(event) => update("cargoName", event.target.value)} placeholder="Ceramic tiles" aria-invalid={Boolean(errors.cargoName)} aria-describedby={errors.cargoName ? "wizard-cargoName-error" : undefined} />
                <FieldError id="wizard-cargoName-error">{errors.cargoName}</FieldError>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="wizard-quantity">How many?</label>
                <input id="wizard-quantity" type="number" min="1" inputMode="numeric" className="form-input" value={draft.quantity} onChange={(event) => update("quantity", event.target.value)} placeholder="10" aria-invalid={Boolean(errors.quantity)} aria-describedby={errors.quantity ? "wizard-quantity-error" : undefined} />
                <FieldError id="wizard-quantity-error">{errors.quantity}</FieldError>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="wizard-packageType">Package type</label>
                <select id="wizard-packageType" className="form-select" value={draft.packageType} onChange={(event) => update("packageType", event.target.value)}>
                  <option value="packages">Packages</option><option value="boxes">Boxes</option><option value="crates">Crates</option><option value="pallets">Pallets</option><option value="units">Individual units</option>
                </select>
              </div>
            </div>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset>
            <legend>Packed measurements for one package</legend>
            <p className="wizard-field-hint">Dimensions are optional, but all three are needed for an accurate volume calculation. Weight is required.</p>
            <div className="wizard-grid measurement">
              <div className="form-group"><label className="form-label" htmlFor="wizard-length">Length</label><input id="wizard-length" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.length} onChange={(event) => update("length", event.target.value)} placeholder="1.2" aria-invalid={Boolean(errors.length)} aria-describedby={errors.length ? "wizard-length-error" : undefined} /><FieldError id="wizard-length-error">{errors.length}</FieldError></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-width">Width</label><input id="wizard-width" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.width} onChange={(event) => update("width", event.target.value)} placeholder="1.0" /></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-height">Height</label><input id="wizard-height" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.height} onChange={(event) => update("height", event.target.value)} placeholder="0.8" /></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-dimensionUnit">Dimension unit</label><select id="wizard-dimensionUnit" className="form-select" value={draft.dimensionUnit} onChange={(event) => update("dimensionUnit", event.target.value)}><option value="m">Metres</option><option value="cm">Centimetres</option><option value="inches">Inches</option></select></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-weightPerPackage">Weight of one package</label><input id="wizard-weightPerPackage" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.weightPerPackage} onChange={(event) => update("weightPerPackage", event.target.value)} placeholder="250" aria-invalid={Boolean(errors.weightPerPackage)} aria-describedby={errors.weightPerPackage ? "wizard-weightPerPackage-error" : undefined} /><FieldError id="wizard-weightPerPackage-error">{errors.weightPerPackage}</FieldError></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-weightUnit">Weight unit</label><select id="wizard-weightUnit" className="form-select" value={draft.weightUnit} onChange={(event) => update("weightUnit", event.target.value)}><option value="kg">Kilograms</option><option value="lb">Pounds</option></select></div>
            </div>
          </fieldset>
        )}

        {step === 3 && (
          <fieldset>
            <legend>Handling and type of help</legend>
            <div className="wizard-grid two">
              <div className="form-group"><label className="form-label" htmlFor="wizard-fragile">Is it fragile?</label><select id="wizard-fragile" className="form-select" value={draft.fragile} onChange={(event) => update("fragile", event.target.value)}><option value="unknown">Not sure</option><option value="yes">Yes</option><option value="no">No</option></select></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-stackability">Can packages be stacked?</label><select id="wizard-stackability" className="form-select" value={draft.stackability} onChange={(event) => update("stackability", event.target.value)}><option value="unknown">Not sure</option><option value="stackable">Yes, stackable</option><option value="non_stackable">No, non-stackable</option></select></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-hazardous">Hazardous or dangerous goods?</label><select id="wizard-hazardous" className="form-select" value={draft.hazardous} onChange={(event) => update("hazardous", event.target.value)}><option value="unknown">Not sure</option><option value="yes">Yes</option><option value="no">No</option></select></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-incoterm">Trade term (optional)</label><select id="wizard-incoterm" className="form-select" value={draft.incoterm} onChange={(event) => update("incoterm", event.target.value)}><option value="">Not sure</option><option value="EXW">EXW</option><option value="FOB">FOB</option><option value="CIF">CIF</option><option value="DAP">DAP</option><option value="DDP">DDP</option><option value="FCA">FCA</option><option value="CFR">CFR</option></select></div>
              <div className="form-group wizard-span-two"><label className="form-label" htmlFor="wizard-goal">What do you need?</label><select id="wizard-goal" className="form-select" value={draft.goal} onChange={(event) => update("goal", event.target.value)}><option value="shipping_plan">Create a shipping plan</option><option value="landed_cost">Estimate landed cost</option><option value="documents">List required documents</option><option value="suppliers">Find suppliers and plan shipping</option></select></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-budget">Working budget (optional)</label><input id="wizard-budget" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.budget} onChange={(event) => update("budget", event.target.value)} placeholder="12000" /></div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-currency">Currency</label><select id="wizard-currency" className="form-select" value={draft.currency} onChange={(event) => update("currency", event.target.value)}><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="ZMW">ZMW</option><option value="INR">INR</option></select></div>
            </div>
          </fieldset>
        )}

        {step === 4 && (
          <div className="wizard-review">
            <div className="wizard-review-notice"><strong>Nothing has been sent yet.</strong><span>Check the details below, then press Create shipping plan.</span></div>
            <dl>
              <ReviewRow label="Route" value={`${draft.origin} → ${draft.destination}`} />
              <ReviewRow label="Cargo" value={`${draft.quantity} ${draft.packageType} of ${draft.cargoName}`} />
              <ReviewRow label="Package size" value={draft.length && draft.width && draft.height ? `${draft.length} × ${draft.width} × ${draft.height} ${draft.dimensionUnit}` : "Not provided"} />
              <ReviewRow label="Package weight" value={draft.weightPerPackage ? `${draft.weightPerPackage} ${draft.weightUnit}` : "Not provided"} />
              <ReviewRow label="Trade term" value={draft.incoterm || "Not sure"} />
            </dl>
            <div className="wizard-generated-request"><span>Request that will be sent</span><p>{requestText}</p></div>
          </div>
        )}
      </div>

      <div className="wizard-actions">
        <button type="button" className="btn" onClick={back} disabled={step === 0 || loading}>Back</button>
        <div className="wizard-actions-right">
          {step < STEPS.length - 1 ? (
            <button type="button" className="btn btn-primary" onClick={next}>Continue</button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={submit} disabled={loading || !requestText}>
              {loading ? "Creating your plan..." : "Create shipping plan"}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
