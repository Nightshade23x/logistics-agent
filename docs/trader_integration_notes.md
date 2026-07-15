# Trader Agent Integration Notes

Branch: integration-test-trader-v5

## Purpose

This branch connects Avishi's Trader Agent into our V5 backend integration flow.

It proves that Trader Agent can run after Logistics Agent and return a shared contract response with Gemini reasoning.

## Supported flows

1. Shopping Agent -> Logistics Agent -> Trader Agent
2. Document AI Agent -> Logistics Agent -> Trader Agent

## Feature flags

Trader Agent is optional.

Enable Trader Agent:

    $env:ENABLE_TRADER_AGENT = "1"

Enable trained router:

    $env:USE_TRAINED_ROUTER = "1"

Trader is disabled by default, so the old User Agent tests still pass normally.

## Required local environment

Trader Agent uses Gemini reasoning.

Create a local .env file in the repo root with:

    GEMINI_API_KEY=your_key_here

Do not commit .env.

## Important files

- app/trader_adapter.py
  - Safe adapter between our backend and Avishi's Trader Agent package.

- app/user_agent.py
  - Optional Trader calls added after Logistics Agent handoff.

- scripts/test_full_trader_integration.py
  - Runs both full backend chains in one script.

- scripts/test_document_trader_integration.py
  - Tests Document AI -> Logistics -> Trader.

- trader_agent/requirements.txt
  - google-generativeai added for Gemini support.

## Full integration test

From repo root:

    cd C:\Users\Samar\Desktop\logistics-agent
    & "G:\venvs\logistics-training\Scripts\Activate.ps1"
    $env:PYTHONPATH = "$PWD\trader_agent;$PWD"
    $env:USE_TRAINED_ROUTER = "1"
    $env:ENABLE_TRADER_AGENT = "1"
    python scripts\test_full_trader_integration.py

Expected result:

- Shopping flow calls shopping_agent, logistics_agent, trader_agent
- Document flow calls document_ai_agent, logistics_agent, trader_agent
- Trader response includes llm_judgment from Gemini

## Safety test

With Trader disabled:

    Remove-Item Env:\ENABLE_TRADER_AGENT -ErrorAction SilentlyContinue
    python scripts\test_user_agent.py

Expected result:

    All user agent tests passed.

## Current known notes

- google.generativeai gives a deprecation warning.
- The warning is not blocking.
- Later Avishi can migrate Trader Agent from google.generativeai to google.genai.
- Trader may return partial_plan_needs_more_information if HS code or FTA data is missing.
- That is expected with the current placeholder trade reference data.
