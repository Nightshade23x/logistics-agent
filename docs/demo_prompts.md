# Demo Prompts

These prompts cover the main application paths used during demonstration and consultant review.

## 1. Ordinary non-hazardous shipment

```text
Ship 10 pallets of cotton textiles from the United States to Israel using FOB. Each pallet measures 1.2 m x 1.0 m x 1.1 m and weighs 300 kg. The cargo is non-hazardous, stackable, and not fragile. No departure or arrival ports have been selected. Recommend suitable gateways and provide an indicative route. Check whether a trade agreement may apply and show the rules-of-origin and proof-of-origin document requirements.
```

Expected demonstration points:

- complete shipment extraction;
- total CBM and weight;
- load-type and container recommendation;
- gateway and route guidance;
- agreement and origin-document guidance;
- document checklist;
- compact serpentine process flow.

## 2. Landlocked origin

```text
Ship 20 crates of machine parts from Zambia to Finland using CIF. Each crate measures 1.0 m x 0.8 m x 0.7 m and weighs 250 kg. The cargo is non-hazardous, stackable, and not fragile. No ports or inland gateways have been selected. Recommend an indicative route including inland pre-carriage, export gateway, ocean corridor, destination gateway, and final delivery. Check for any relevant trade agreement and required origin documents.
```

Expected demonstration points:

- recognition that Zambia is landlocked;
- inland pre-carriage;
- reference export gateway;
- ocean corridor;
- destination gateway;
- final delivery;
- route assumptions and limitations.

## 3. Dangerous goods

```text
Ship 4 pallets of lithium-ion batteries from China to Germany using CIF. Each pallet measures 1.2 m x 1.0 m x 1.0 m and weighs 450 kg. The batteries are hazardous cargo and require dangerous-goods handling. Recommend the shipment plan, route, load type, required dangerous-goods documents, insurance review, packaging controls, and carrier approvals.
```

Expected demonstration points:

- hazardous-cargo classification;
- specialist review status;
- dangerous-goods documents;
- insurance and carrier-acceptance checks;
- additional process-flow steps.

## 4. 3D container visualizer

```text
Ship 5 boxes of glassware from India to Germany using CIF. Each box is 2 x 2 x 2 m and weighs 100 kg. The cargo is fragile, stackable, and does not contain hazardous materials. The working budget is 20000 USD.
```

Expected demonstration points:

- shared dimension-unit parsing;
- negated hazardous-language handling;
- container selection;
- utilization percentage;
- remaining CBM;
- visible cargo blocks;
- fragile-cargo guidance.

## 5. Non-fragile ordinary cargo

```text
Ship 40 cartons of plastic household goods from India to Germany. Each carton measures 0.6 m x 0.5 m x 0.4 m and weighs 25 kg. The cargo is non-fragile, stackable, and non-hazardous. Recommend a shipment and container plan.
```

Expected demonstration points:

- no contradictory fragile handling;
- no dangerous-goods documents;
- ordinary loading guidance;
- compact process flow.

## 6. Completed landed-cost calculation

```text
Calculate the landed cost for goods worth 15000 USD shipped from India to Germany using CIF. Freight is 2500 USD, insurance is 300 USD, customs brokerage is 200 USD, local delivery is 400 USD, duty rate is 5 percent, and import tax is 19 percent. The shipment is 12 CBM and weighs 4000 kg.
```

Expected demonstration points:

- complete commercial inputs;
- duty and tax calculation;
- landed-cost total;
- process flow showing cost completion.

## 7. Incomplete landed-cost request

```text
Estimate the landed cost for goods worth 15000 USD shipped from India to Germany.
```

Expected demonstration points:

- missing freight, insurance, brokerage, delivery, duty, or tax fields;
- no false claim that the calculation is complete;
- clear request for missing information.

## 8. Incomplete shipment request

```text
I need to ship furniture to Germany.
```

Expected demonstration points:

- missing origin;
- missing quantity;
- missing dimensions and weight;
- missing Incoterm and delivery scope;
- partial-plan or information-required status.

## 9. Explicit gateway preservation

```text
Ship 8 pallets of ceramic tiles from Mumbai, India to Hamburg, Germany using CIF. Use Nhava Sheva as the departure port and Hamburg as the arrival port. Each pallet measures 1.2 m x 1.0 m x 0.9 m and weighs 800 kg. The cargo is non-hazardous and stackable.
```

Expected demonstration points:

- explicit gateways are preserved;
- no replacement with invented ports;
- route plan uses the requested gateways.

## 10. Guided-input synchronization

Enter one of the complete prompts in free-text mode, then switch to guided mode.

Expected demonstration points:

- the request remains visible;
- the workflow does not silently reset;
- editing is explicit;
- switching back preserves the request until it is cleared.
