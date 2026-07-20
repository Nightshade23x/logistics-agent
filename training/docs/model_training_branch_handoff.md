# Model Training Branch Handoff

Branch: model-training

## Purpose

This branch adds a trained router model to the multi-agent trade/logistics system.

The trained router is used by the User Agent to decide which specialist agents should be called.

## Current flow

User request
-> Trained Router predicts structured JSON
-> User Agent validates the route
-> Specialist agents run
-> Partner review service may review high-risk outputs separately

## Specialist agents

- shopping_agent
- document_ai_agent
- logistics_agent

## Review service

- partner_review_service

This is kept separate from agents_called to avoid confusing the actual agent chain.

## Trained model

Base model:

Qwen/Qwen2.5-0.5B-Instruct

Training method:

LoRA supervised fine-tuning

Adapter location:

G:\ai-models\checkpoints\router-qwen-0.5b-lora-expanded-400\final_adapter

The adapter is not committed to Git because it is a model artifact.

## Dataset

- train.jsonl: 340 records
- eval.jsonl: 85 records
- challenge_eval.jsonl: 8 records

## Evaluation results

Fine-tuned router:

- Eval set full routing accuracy: 85/85
- Challenge set full routing accuracy: 8/8

Base model without LoRA:

- Challenge set full routing accuracy: 0/8
- Eval sample full routing accuracy: 0/20

## Run trained router User Agent demo

Activate the training environment:

& "G:\venvs\logistics-training\Scripts\Activate.ps1"

Then go to the repo:

cd C:\Users\Samar\Desktop\logistics-agent

Run:

python scripts\run_user_agent_with_trained_router.py "I need 50 TVs from India and a shipping plan."

Expected output includes:

router_source: trained_router
detected_intent: shopping
agents_called: shopping_agent, logistics_agent
review_services_called: partner_review_service

## Normal fallback mode

The normal User Agent still works without the trained router.

If the trained router is disabled or unavailable, the rule-based router can still run.

## Important environment variable

To enable trained router manually:

$env:USE_TRAINED_ROUTER = "1"

To disable:

$env:USE_TRAINED_ROUTER = "0"

## What to send partner

Send the branch or a clean zip of the repo, but do not include:

- .venv
- G:\ai-models
- model weights
- cache files
- training outputs

The partner should receive the code, docs, dataset, and instructions.

The model adapter can be shared separately if needed.
