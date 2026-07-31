# Security Policy

## Project status

This repository is a demonstration and consultant-handover candidate.

It is not yet a production-hardened service.

## Reporting a vulnerability

Do not open a public issue containing:

- credentials;
- private documents;
- customer data;
- exploit details;
- sensitive infrastructure information.

Report sensitive findings privately to the repository owner.

Include:

- the affected component;
- reproduction steps;
- potential impact;
- suggested mitigation, when known.

## Credential handling

- Never commit `.env`.
- Never place real values in `.env.example`.
- Rotate credentials exposed in screenshots, terminal output, logs, generated reports, or Git history.
- Treat public Git history as permanently accessible.
- Use repository or deployment secret stores for CI/CD and hosted environments.
- Remove local credentials before sharing demo bundles.

## Data handling

Do not use confidential or real customer data in the public repository.

Use demonstration data instead of:

- private invoices;
- customer contact information;
- bills of lading;
- commercial contracts;
- insurance records;
- regulated shipment records;
- confidential supplier pricing.

## File-upload safety

Before production use, document processing should include:

- file-size limits;
- accepted file-type validation;
- malware scanning;
- safe temporary-file handling;
- access control;
- retention and deletion policies.

## Production hardening still required

- authentication and authorization;
- role-based access control;
- rate limiting;
- dependency and vulnerability scanning;
- centralized secret management;
- audit logging;
- secure CORS configuration;
- request-size limits;
- file-upload protections;
- threat modelling;
- secure deployment configuration;
- monitoring and alerting.

## Third-party and live data

External APIs and partner services should be reviewed for:

- credential scope;
- data retention;
- privacy terms;
- uptime expectations;
- error handling;
- versioning;
- licensing;
- jurisdictional restrictions.

## Supported versions

No formal production support policy has been established yet.

The mentor-approved handover tag should be treated as the review baseline.
