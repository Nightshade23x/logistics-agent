import { useEffect, useMemo, useState } from "react";

const SESSION_KEY = "meridian.guidedShipmentDraft.v39";

const STEP_SESSION_KEY = "meridian.guidedShipmentStep.v61"; // GUIDED_STEP_PERSISTENCE_V61

// FLEXIBLE_UNITS_V67

const DIMENSION_TO_METRES = { m: 1, cm: 0.01, mm: 0.001, ft: 0.3048, inches: 0.0254 };
const VOLUME_TO_CBM = { cbm: 1, litres: 0.001, millilitres: 0.000001, cubic_feet: 0.028316846592, cubic_inches: 0.000016387064 };
const WEIGHT_TO_KG = { kg: 1, g: 0.001, tonnes: 1000, lb: 0.45359237, oz: 0.028349523125, st: 6.35029318 };
const VOLUME_LABELS = { cbm: "CBM", litres: "litres", millilitres: "millilitres", cubic_feet: "cubic feet", cubic_inches: "cubic inches" };

function cleanText(value) {
  return String(value || "").trim();
}

function positiveNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return Number(number.toFixed(6)).toString();
}

function resolvedPackageType(draft) {
  return draft.packageType === "custom" ? cleanText(draft.customPackageType) : cleanText(draft.packageType || "packages");
}

function resolvedCurrency(draft) {
  return draft.currency === "custom" ? cleanText(draft.customCurrency).toUpperCase() : cleanText(draft.currency || "USD").toUpperCase();
}

function resolvedDimensionUnit(draft) {
  return draft.dimensionUnit === "custom" ? cleanText(draft.customDimensionUnit) : cleanText(draft.dimensionUnit);
}

function resolvedVolumeUnit(draft) {
  return draft.volumeUnit === "custom" ? cleanText(draft.customVolumeUnit) : VOLUME_LABELS[draft.volumeUnit] || cleanText(draft.volumeUnit);
}

function resolvedWeightUnit(draft) {
  return draft.weightUnit === "custom" ? cleanText(draft.customWeightUnit) : cleanText(draft.weightUnit);
}

function dimensionFactor(draft) {
  return draft.dimensionUnit === "custom" ? positiveNumber(draft.metresPerCustomDimensionUnit) : DIMENSION_TO_METRES[draft.dimensionUnit] || null;
}

function volumeFactor(draft) {
  return draft.volumeUnit === "custom" ? positiveNumber(draft.cbmPerCustomVolumeUnit) : VOLUME_TO_CBM[draft.volumeUnit] || null;
}

function weightFactor(draft) {
  return draft.weightUnit === "custom" ? positiveNumber(draft.kgPerCustomWeightUnit) : WEIGHT_TO_KG[draft.weightUnit] || null;
}


const EMPTY_DRAFT = {
  origin: "",
  destination: "",
  cargoName: "",
  quantity: "",
  packageType: "crates",
  customPackageType: "",
  measurementMode: "dimensions",
  length: "",
  width: "",
  height: "",
  dimensionUnit: "m",
  customDimensionUnit: "",
  metresPerCustomDimensionUnit: "",
  volumePerPackage: "",
  volumeUnit: "litres",
  customVolumeUnit: "",
  cbmPerCustomVolumeUnit: "",
  weightPerPackage: "",
  weightUnit: "kg",
  customWeightUnit: "",
  kgPerCustomWeightUnit: "",
  fragile: "unknown",
  stackability: "unknown",
  hazardous: "unknown",
  incoterm: "",
  goal: "shipping_plan",
  budget: "",
  currency: "USD",
  customCurrency: "",
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
  const quantity = cleanText(draft.quantity);
  const packageType = resolvedPackageType(draft);
  const cargoName = cleanText(draft.cargoName);
  const origin = cleanText(draft.origin);
  const destination = cleanText(draft.destination);

  if (!quantity || !packageType || !cargoName || !origin || !destination) return "";

  const incoterm = draft.incoterm ? ` using ${draft.incoterm}` : "";
  const sentences = [
    `${goalLead(draft.goal)} ${quantity} ${packageType} of ${cargoName} from ${origin} to ${destination}${incoterm}.`,
  ];
  const packageLabel = singularPackage(packageType);

  if (draft.measurementMode === "volume") {
    const volume = positiveNumber(draft.volumePerPackage);
    const unit = resolvedVolumeUnit(draft);
    const factor = volumeFactor(draft);
    if (volume && unit && factor) {
      const totalCbm = volume * factor * Number(quantity);
      sentences.push(`Each ${packageLabel} has packed volume of ${formatNumber(volume)} ${unit}.`);
      sentences.push(`Original package volume: ${formatNumber(volume)} ${unit}.`);
      sentences.push(`The total shipment volume is ${formatNumber(totalCbm)} CBM for calculation.`);
    }
  } else {
    const dimensions = [draft.length, draft.width, draft.height].map(positiveNumber);
    const hasDimensions = dimensions.every((value) => value !== null);
    const unit = resolvedDimensionUnit(draft);
    const factor = dimensionFactor(draft);
    if (hasDimensions && unit && factor) {
      if (draft.dimensionUnit === "custom") {
        const converted = dimensions.map((value) => formatNumber(value * factor));
        sentences.push(
          `Each ${packageLabel} is ${converted.join(" x ")} m for calculation ` +
          `(entered as ${dimensions.map(formatNumber).join(" x ")} ${unit}; 1 ${unit} = ${formatNumber(factor)} m).`,
        );
      } else {
        sentences.push(`Each ${packageLabel} is ${dimensions.map(formatNumber).join(" x ")} ${unit}.`);
      }
    }
  }

  const weight = positiveNumber(draft.weightPerPackage);
  const weightUnit = resolvedWeightUnit(draft);
  const kgFactor = weightFactor(draft);
  if (weight && weightUnit && kgFactor) {
    if (draft.weightUnit === "custom") {
      sentences.push(`Each ${packageLabel} weighs ${formatNumber(weight * kgFactor)} kg for calculation.`);
      sentences.push(`Original package weight: ${formatNumber(weight)} ${weightUnit}.`);
      sentences.push(`The custom weight conversion is 1 ${weightUnit} = ${formatNumber(kgFactor)} kg.`);
    } else {
      sentences.push(`Each ${packageLabel} weighs ${formatNumber(weight)} ${weightUnit}.`);
    }
  }

  // DETERMINISTIC_DIRECT_VOLUME_V67
  // Give the deterministic backend one aggregate CBM + kg clause. The
  // original package volume and weight units remain in separate sentences
  // and are restored for display by FLEXIBLE_DISPLAY_UNITS_V67.
  if (draft.measurementMode === "volume") {
    const volume = positiveNumber(draft.volumePerPackage);
    const cbmFactor = volumeFactor(draft);
    const packageWeight = positiveNumber(draft.weightPerPackage);
    const kgFactor = weightFactor(draft);
    const packageCount = positiveNumber(quantity);

    if (volume && cbmFactor && packageWeight && kgFactor && packageCount) {
      const totalCbm = volume * cbmFactor * packageCount;
      const totalWeightKg = packageWeight * kgFactor * packageCount;
      sentences.push(
        `${formatNumber(totalCbm)} CBM of ${cargoName} weighing ` +
        `${formatNumber(totalWeightKg)} kg total.`,
      );
    }
  }

  const handling = [];
  if (draft.fragile === "yes") handling.push("fragile");
  if (draft.fragile === "no") handling.push("not fragile");
  if (draft.stackability === "stackable") handling.push("stackable");
  if (draft.stackability === "non_stackable") handling.push("non-stackable");
  if (draft.hazardous === "yes") handling.push("contains hazardous materials");
  if (draft.hazardous === "no") handling.push("does not contain hazardous materials");
  if (handling.length) sentences.push(`The cargo is ${handling.join(", ")}.`);

  const budget = cleanText(draft.budget);
  const currency = resolvedCurrency(draft);
  if (budget && currency) sentences.push(`The working budget is ${budget} ${currency}.`);

  return sentences.join(" ");
}

function FieldError({ id, children }) {
  if (!children) return null;
  return <div className="wizard-field-error" id={id} role="alert">{children}</div>;
}

function ReviewRow({ label, value }) {
  return <div className="wizard-review-row"><dt>{label}</dt><dd>{value || "Not provided"}</dd></div>;
}

// MENTOR WORKFLOW UX V89
// Reuse the completed guided-shipment draft for another user goal without
// forcing the user to walk backward through the five-step wizard.
export const GUIDED_GOAL_OPTIONS = Object.freeze([
  { value: "shipping_plan", label: "Create shipping plan" },
  { value: "landed_cost", label: "Estimate landed cost" },
  { value: "documents", label: "List required documents" },
  { value: "suppliers", label: "Find suppliers and plan shipping" },
]);

export function getGuidedShipmentGoal() {
  return loadDraft()?.goal || "shipping_plan";
}

export function buildGuidedShipmentRequestForGoal(goal) {
  const supportedGoal = GUIDED_GOAL_OPTIONS.some((option) => option.value === goal);
  if (!supportedGoal) return "";

  const draft = { ...loadDraft(), goal };

  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(draft));
  } catch {
    // Session storage is optional.
  }

  return buildGuidedShipmentRequest(draft);
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
      if (draft.packageType === "custom" && !draft.customPackageType.trim()) nextErrors.customPackageType = "Enter your package type.";
    }

    if (step === 2) {
      if (!positiveNumber(draft.weightPerPackage)) nextErrors.weightPerPackage = "Enter the packed weight of one package.";
      if (draft.weightUnit === "custom" && (!draft.customWeightUnit.trim() || !positiveNumber(draft.kgPerCustomWeightUnit))) {
        nextErrors.customWeightUnit = "Enter the unit name and how many kilograms one unit represents.";
      }

      if (draft.measurementMode === "volume") {
        if (!positiveNumber(draft.volumePerPackage)) nextErrors.volumePerPackage = "Enter the packed volume of one package.";
        if (draft.volumeUnit === "custom" && (!draft.customVolumeUnit.trim() || !positiveNumber(draft.cbmPerCustomVolumeUnit))) {
          nextErrors.customVolumeUnit = "Enter the unit name and how many CBM one unit represents.";
        }
      } else {
        const dimensions = [draft.length, draft.width, draft.height];
        const anyDimension = dimensions.some((value) => cleanText(value));
        const allDimensions = dimensions.every((value) => positiveNumber(value));
        if (anyDimension && !allDimensions) nextErrors.length = "Enter all three packed dimensions, or leave all three blank.";
        if (anyDimension && draft.dimensionUnit === "custom" && (!draft.customDimensionUnit.trim() || !positiveNumber(draft.metresPerCustomDimensionUnit))) {
          nextErrors.customDimensionUnit = "Enter the unit name and how many metres one unit represents.";
        }
      }
    }

    if (step === 3 && draft.budget && draft.currency === "custom" && !draft.customCurrency.trim()) {
      nextErrors.customCurrency = "Enter your currency code or name.";
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
                  <option value="packages">Packages</option><option value="boxes">Boxes</option><option value="crates">Crates</option><option value="pallets">Pallets</option><option value="drums">Drums</option><option value="bags">Bags</option><option value="cartons">Cartons</option><option value="units">Individual units</option><option value="custom">Other — enter your own</option>
                </select>
              </div>
              {draft.packageType === "custom" && (
                <div className="form-group">
                  <label className="form-label" htmlFor="wizard-customPackageType">Your package type</label>
                  <input id="wizard-customPackageType" className="form-input" value={draft.customPackageType} onChange={(event) => update("customPackageType", event.target.value)} placeholder="Bundles" aria-invalid={Boolean(errors.customPackageType)} />
                  <FieldError id="wizard-customPackageType-error">{errors.customPackageType}</FieldError>
                </div>
              )}
            </div>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset>
            <legend>Packed measurements for one package</legend>
            <p className="wizard-field-hint">Choose dimensions or enter direct volume. Weight is required. Custom units need a conversion factor so calculations remain accurate.</p>

            <div className="form-group wizard-measurement-choice">
              <label className="form-label" htmlFor="wizard-measurementMode">How do you know the cargo space?</label>
              <select id="wizard-measurementMode" className="form-select" value={draft.measurementMode} onChange={(event) => update("measurementMode", event.target.value)}>
                <option value="dimensions">Length × width × height</option>
                <option value="volume">Direct volume per package</option>
              </select>
            </div>

            {draft.measurementMode === "dimensions" ? (
              <>
                <div className="form-group wizard-measurement-choice">
                  <label className="form-label" htmlFor="wizard-dimensionUnit">Dimension unit</label>
                  <select id="wizard-dimensionUnit" className="form-select" value={draft.dimensionUnit} onChange={(event) => update("dimensionUnit", event.target.value)}>
                    <option value="m">Metres</option><option value="cm">Centimetres</option><option value="mm">Millimetres</option><option value="ft">Feet</option><option value="inches">Inches</option><option value="custom">Other — enter your own</option>
                  </select>
                </div>
                <div className="wizard-grid measurement">
                  <div className="form-group"><label className="form-label" htmlFor="wizard-length">Length</label><input id="wizard-length" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.length} onChange={(event) => update("length", event.target.value)} placeholder="1.2" aria-invalid={Boolean(errors.length)} /><FieldError id="wizard-length-error">{errors.length}</FieldError></div>
                  <div className="form-group"><label className="form-label" htmlFor="wizard-width">Width</label><input id="wizard-width" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.width} onChange={(event) => update("width", event.target.value)} placeholder="1.0" /></div>
                  <div className="form-group"><label className="form-label" htmlFor="wizard-height">Height</label><input id="wizard-height" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.height} onChange={(event) => update("height", event.target.value)} placeholder="0.8" /></div>
                </div>
                {draft.dimensionUnit === "custom" && (
                  <div className="wizard-custom-unit">
                    <div className="form-group"><label className="form-label" htmlFor="wizard-customDimensionUnit">Your dimension unit</label><input id="wizard-customDimensionUnit" className="form-input" value={draft.customDimensionUnit} onChange={(event) => update("customDimensionUnit", event.target.value)} placeholder="Yards" aria-invalid={Boolean(errors.customDimensionUnit)} /></div>
                    <div className="form-group"><label className="form-label" htmlFor="wizard-metresPerCustomDimensionUnit">Metres in one custom unit</label><input id="wizard-metresPerCustomDimensionUnit" type="number" min="0" step="any" className="form-input" value={draft.metresPerCustomDimensionUnit} onChange={(event) => update("metresPerCustomDimensionUnit", event.target.value)} placeholder="0.9144" aria-invalid={Boolean(errors.customDimensionUnit)} /></div>
                    <FieldError id="wizard-customDimensionUnit-error">{errors.customDimensionUnit}</FieldError>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="wizard-grid two">
                  <div className="form-group"><label className="form-label" htmlFor="wizard-volumePerPackage">Volume of one package</label><input id="wizard-volumePerPackage" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.volumePerPackage} onChange={(event) => update("volumePerPackage", event.target.value)} placeholder="100" aria-invalid={Boolean(errors.volumePerPackage)} /><FieldError id="wizard-volumePerPackage-error">{errors.volumePerPackage}</FieldError></div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="wizard-volumeUnit">Volume unit</label>
                    <select id="wizard-volumeUnit" className="form-select" value={draft.volumeUnit} onChange={(event) => update("volumeUnit", event.target.value)}>
                      <option value="cbm">CBM / cubic metres</option><option value="litres">Litres</option><option value="millilitres">Millilitres</option><option value="cubic_feet">Cubic feet</option><option value="cubic_inches">Cubic inches</option><option value="custom">Other — enter your own</option>
                    </select>
                  </div>
                </div>
                {draft.volumeUnit === "custom" && (
                  <div className="wizard-custom-unit">
                    <div className="form-group"><label className="form-label" htmlFor="wizard-customVolumeUnit">Your volume unit</label><input id="wizard-customVolumeUnit" className="form-input" value={draft.customVolumeUnit} onChange={(event) => update("customVolumeUnit", event.target.value)} placeholder="Barrels" aria-invalid={Boolean(errors.customVolumeUnit)} /></div>
                    <div className="form-group"><label className="form-label" htmlFor="wizard-cbmPerCustomVolumeUnit">CBM in one custom unit</label><input id="wizard-cbmPerCustomVolumeUnit" type="number" min="0" step="any" className="form-input" value={draft.cbmPerCustomVolumeUnit} onChange={(event) => update("cbmPerCustomVolumeUnit", event.target.value)} placeholder="0.158987" aria-invalid={Boolean(errors.customVolumeUnit)} /></div>
                    <FieldError id="wizard-customVolumeUnit-error">{errors.customVolumeUnit}</FieldError>
                  </div>
                )}
              </>
            )}

            <div className="wizard-grid two wizard-weight-row">
              <div className="form-group">
                <label className="form-label" htmlFor="wizard-weightUnit">Weight unit</label>
                <select id="wizard-weightUnit" className="form-select" value={draft.weightUnit} onChange={(event) => update("weightUnit", event.target.value)}>
                  <option value="kg">Kilograms</option><option value="g">Grams</option><option value="tonnes">Metric tonnes</option><option value="lb">Pounds</option><option value="oz">Ounces</option><option value="st">Stones</option><option value="custom">Other — enter your own</option>
                </select>
              </div>
              <div className="form-group"><label className="form-label" htmlFor="wizard-weightPerPackage">Weight of one package</label><input id="wizard-weightPerPackage" type="number" min="0" step="any" inputMode="decimal" className="form-input" value={draft.weightPerPackage} onChange={(event) => update("weightPerPackage", event.target.value)} placeholder="250" aria-invalid={Boolean(errors.weightPerPackage)} /><FieldError id="wizard-weightPerPackage-error">{errors.weightPerPackage}</FieldError></div>
            </div>
            {draft.weightUnit === "custom" && (
              <div className="wizard-custom-unit">
                <div className="form-group"><label className="form-label" htmlFor="wizard-customWeightUnit">Your weight unit</label><input id="wizard-customWeightUnit" className="form-input" value={draft.customWeightUnit} onChange={(event) => update("customWeightUnit", event.target.value)} placeholder="Sacks" aria-invalid={Boolean(errors.customWeightUnit)} /></div>
                <div className="form-group"><label className="form-label" htmlFor="wizard-kgPerCustomWeightUnit">Kilograms in one custom unit</label><input id="wizard-kgPerCustomWeightUnit" type="number" min="0" step="any" className="form-input" value={draft.kgPerCustomWeightUnit} onChange={(event) => update("kgPerCustomWeightUnit", event.target.value)} placeholder="25" aria-invalid={Boolean(errors.customWeightUnit)} /></div>
                <FieldError id="wizard-customWeightUnit-error">{errors.customWeightUnit}</FieldError>
              </div>
            )}
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
              <div className="form-group"><label className="form-label" htmlFor="wizard-currency">Currency</label><select id="wizard-currency" className="form-select" value={draft.currency} onChange={(event) => update("currency", event.target.value)}><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="ZMW">ZMW</option><option value="INR">INR</option><option value="AED">AED</option><option value="ILS">ILS</option><option value="CNY">CNY</option><option value="JPY">JPY</option><option value="CAD">CAD</option><option value="AUD">AUD</option><option value="CHF">CHF</option><option value="ZAR">ZAR</option><option value="SGD">SGD</option><option value="KES">KES</option><option value="NGN">NGN</option><option value="custom">Other — enter your own</option></select></div>
              {draft.currency === "custom" && (
                <div className="form-group">
                  <label className="form-label" htmlFor="wizard-customCurrency">Your currency code or name</label>
                  <input id="wizard-customCurrency" className="form-input" value={draft.customCurrency} onChange={(event) => update("customCurrency", event.target.value.toUpperCase())} placeholder="BWP" maxLength="12" aria-invalid={Boolean(errors.customCurrency)} />
                  <FieldError id="wizard-customCurrency-error">{errors.customCurrency}</FieldError>
                </div>
              )}
            </div>
          </fieldset>
        )}

        {step === 4 && (
          <div className="wizard-review">
            <div className="wizard-review-notice"><strong>Nothing has been sent yet.</strong><span>Check the details below, then press Create shipping plan.</span></div>
            <dl>
              <ReviewRow label="Route" value={`${draft.origin} → ${draft.destination}`} />
              <ReviewRow label="Cargo" value={`${draft.quantity} ${resolvedPackageType(draft)} of ${draft.cargoName}`} />
              <ReviewRow label={draft.measurementMode === "volume" ? "Package volume" : "Package size"} value={draft.measurementMode === "volume" ? (draft.volumePerPackage ? `${draft.volumePerPackage} ${resolvedVolumeUnit(draft)}` : "Not provided") : (draft.length && draft.width && draft.height ? `${draft.length} × ${draft.width} × ${draft.height} ${resolvedDimensionUnit(draft)}` : "Not provided")} />
              <ReviewRow label="Package weight" value={draft.weightPerPackage ? `${draft.weightPerPackage} ${resolvedWeightUnit(draft)}` : "Not provided"} />
              <ReviewRow label="Trade term" value={draft.incoterm || "Not sure"} />
              <ReviewRow label="Budget" value={draft.budget ? `${draft.budget} ${resolvedCurrency(draft)}` : "Not provided"} />
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
