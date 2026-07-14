# Model Training Plan

## Goal

Fine-tune an instruct model to act as the User Agent router.

The trained model decides:

- user intent
- input type
- agents to call
- missing information
- confidence
- routing reason

The trained model does not replace the Python agents.

## Recommended base models

Start with:

- Llama 3.2 3B Instruct
- Qwen2.5 3B Instruct

Scale later to:

- Llama 3.1 8B Instruct
- Qwen2.5 7B Instruct

## Training method

Use supervised fine-tuning with LoRA or QLoRA.

## Target output

The model should return strict JSON.

Example:

{
  "intent": "shopping",
  "agents_to_call": ["shopping_agent", "logistics_agent"],
  "input_type": "text",
  "missing_information": [],
  "confidence": "high",
  "reason": "The user is asking to source products and plan shipping."
}

## Valid agents

- shopping_agent
- document_ai_agent
- logistics_agent

## Evaluation metrics

- JSON validity
- correct intent
- correct agent chain
- no hallucinated agents
- correct missing information
