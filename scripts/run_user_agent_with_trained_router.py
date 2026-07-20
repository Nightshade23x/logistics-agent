from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.trained_router_backend import predict_trained_route
from app.user_agent import run_user_agent_from_text


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print('python scripts\\run_user_agent_with_trained_router.py "I need 50 TVs from India and a shipping plan."')
        raise SystemExit(1)

    user_text = " ".join(sys.argv[1:])

    os.environ["USE_TRAINED_ROUTER"] = "1"

    print("TRAINED ROUTER DECISION")
    print("=" * 40)

    decision = predict_trained_route(user_text)
    print(json.dumps(decision, indent=2))
    print("")

    print("USER AGENT RESULT")
    print("=" * 40)

    response = run_user_agent_from_text(user_text)

    compact = {
        "status": response.get("status"),
        "router_source": response.get("router_source"),
        "detected_intent": response.get("detected_intent"),
        "agents_called": response.get("agents_called"),
        "review_services_called": response.get("review_services_called"),
        "summary": response.get("summary"),
        "missing_information": response.get("missing_information"),
        "trained_router_decision": response.get("trained_router_decision"),
    }

    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
