"""REST entry point for the Orchestrator Agent.

Run with:
    python -m uvicorn orchestrator_agent.api:app --port 8010
from inside the outer orchestrator_agent/ directory.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from .container import build_container
from .schemas.orchestrated_response import OrchestratedResponse

app = FastAPI(title="Orchestrator Agent")
container = build_container()


class QueryRequest(BaseModel):
    query: str


@app.post("/orchestrate", response_model=OrchestratedResponse)
def orchestrate(request: QueryRequest) -> OrchestratedResponse:
    """Run the full pipeline: parse free text, call all four agents, synthesize.

    Args:
        request: Contains the free-text shipment query, e.g.
            "ship 200 e-bike batteries from China to Brazil".

    Returns:
        An OrchestratedResponse with each agent's raw report plus a final
        synthesized, prioritized human-readable answer.
    """
    return container.orchestrator_service.run(request.query)

@app.get("/health")
def health():
    """Simple liveness check for this orchestrator."""
    return {"status": "ok", "agent": "orchestrator_agent"}