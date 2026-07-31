# Carrier and Company API Integration Guide

## Purpose

The Integration Hub keeps carrier-specific code out of the main logistics pipeline. Every provider is converted into one internal quote request and one normalized quote response.

## Available endpoints

- `GET /api/integrations`
- `GET /api/integrations/health`
- `GET /api/integrations/contract`
- `POST /api/integrations/quotes`

Interactive OpenAPI documentation is available at `/docs` while the FastAPI service is running.

## Add a company REST API

1. Copy `config/carrier_integrations.example.json` to `config/carrier_integrations.json`.
2. Change the endpoint paths and request/response mappings to match the provider API.
3. Put credential values in environment variables. Do not put them in JSON or source code.
4. Set `CARRIER_INTEGRATIONS_CONFIG` when using a different config path.
5. Restart the backend and inspect the Integrations page.

Supported authentication modes are `none`, `api_key`, `bearer`, and `basic`.

## Live versus demo data

The built-in Demo Carrier is deterministic and clearly marked `live: false` and `source: mock_estimate`. A configured production provider is marked live only when its configuration environment is `production`.

## Website-data future phase

A provider-approved browser connector can implement the same provider interface later. It should be read-only for quote collection, respect the provider's terms and robots restrictions, avoid CAPTCHA bypass, never store website passwords in source code, and require human confirmation before booking, payment, or shipment creation. Official APIs remain the preferred source.
