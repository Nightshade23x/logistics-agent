# Router Baseline Comparison

## Purpose

This comparison tests whether fine-tuning improved the router model's ability to produce valid structured agent-routing JSON.

The router task is to predict:

- intent
- agents_to_call
- input_type
- missing_information
- confidence
- reason

## Base model

Qwen/Qwen2.5-0.5B-Instruct without LoRA adapter.

## Fine-tuned model

Qwen/Qwen2.5-0.5B-Instruct with LoRA adapter:

G:\ai-models\checkpoints\router-qwen-0.5b-lora-expanded-400\final_adapter

## Base model results

### Challenge evaluation set

Records: 8

- JSON valid: 0/8
- Schema valid: 0/8
- Intent accuracy: 0/8
- Agent-chain accuracy: 0/8
- Input-type accuracy: 0/8
- Missing-info accuracy: 0/8
- Full routing accuracy: 0/8

### Eval sample

Records: 20

- JSON valid: 3/20
- Schema valid: 0/20
- Intent accuracy: 0/20
- Agent-chain accuracy: 0/20
- Input-type accuracy: 0/20
- Missing-info accuracy: 0/20
- Full routing accuracy: 0/20

## Fine-tuned LoRA model results

### Full eval set

Records: 85

- JSON valid: 85/85
- Schema valid: 85/85
- Intent accuracy: 85/85
- Agent-chain accuracy: 85/85
- Input-type accuracy: 85/85
- Missing-info accuracy: 85/85
- Full routing accuracy: 85/85

### Challenge eval set

Records: 8

- JSON valid: 8/8
- Schema valid: 8/8
- Intent accuracy: 8/8
- Agent-chain accuracy: 8/8
- Input-type accuracy: 8/8
- Missing-info accuracy: 8/8
- Full routing accuracy: 8/8

## Conclusion

The base model was not reliable for structured router decisions. It often failed to produce valid JSON or failed to follow the required schema.

After LoRA fine-tuning, the router produced valid JSON and selected the correct agent chain across the synthetic eval set and challenge set.

This supports using the fine-tuned router as an optional User Agent backend, with the rule-based router kept as a fallback.
