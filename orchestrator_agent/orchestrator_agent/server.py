"""Entry point for manually running the orchestrator against a query."""

import sys
from .container import build_container


def main() -> None:
    query = " ".join(sys.argv[1:]) or "ship 200 e-bike batteries from China to Brazil"
    container = build_container()
    result = container.orchestrator_service.run(query)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()