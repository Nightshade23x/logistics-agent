// Thin client around the FastAPI wrapper in ../api_server.py
// Every function returns the parsed JSON body or throws an Error with a
// readable message (surfaced by the UI as a toast / inline error).

async function handle(res) {
  let body;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const detail = body?.detail || res.statusText || "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const api = {
  health: () => fetch("/api/health").then(handle),

  // Full pipeline (recommended) ------------------------------------------
  requestText: (userText, includeRaw = false) =>
    fetch("/api/request/text", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ user_text: userText, include_raw_response: includeRaw }),
    }).then(handle),

  requestJson: (payload, includeRaw = false) =>
    fetch("/api/request/json", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ payload, include_raw_response: includeRaw }),
    }).then(handle),

  requestDocuments: (fileList) => {
    const form = new FormData();
    Array.from(fileList).forEach((f) => form.append("files", f));
    return fetch("/api/request/documents", { method: "POST", body: form }).then(handle);
  },

  // Individual specialist agents (playground) ------------------------------
  agentLogistics: (items, shipmentContext = null) =>
    fetch("/api/agents/logistics", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ items, shipment_context: shipmentContext }),
    }).then(handle),

  agentShopping: (requestData) =>
    fetch("/api/agents/shopping", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ request_data: requestData }),
    }).then(handle),

  agentDocument: (text) =>
    fetch("/api/agents/document", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ text }),
    }).then(handle),

  agentPartnerReview: (payload, requestId = null) =>
    fetch("/api/agents/partner-review", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ payload, request_id: requestId }),
    }).then(handle),

  agentIntent: (text) =>
    fetch("/api/agents/intent", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ text }),
    }).then(handle),
};
