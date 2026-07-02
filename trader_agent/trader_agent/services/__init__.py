"""Service layer for the Trader Agent MCP server.

Each service encapsulates a single domain concern (Incoterms, HS codes,
duty calculation, FTA checks, export strategy). Services are plain,
stateless-by-default classes with no global state, instantiated once
in container.py and injected into the MCP tool functions in server.py.
"""