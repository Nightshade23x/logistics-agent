# Router Model Training Results

## Branch

model-training

## Base model

Qwen/Qwen2.5-0.5B-Instruct

## Training method

LoRA supervised fine-tuning.

## Dataset size

- Training records: 340
- Evaluation records: 85
- Challenge evaluation records: 8

## Adapter

The trained adapter is stored locally at:

G:\ai-models\checkpoints\router-qwen-0.5b-lora-expanded-400\final_adapter

The adapter is not committed to Git because model weights are large artifacts.

## Evaluation results

### Eval set

- JSON valid: 85/85
- Schema valid: 85/85
- Intent accuracy: 85/85
- Agent-chain accuracy: 85/85
- Input-type accuracy: 85/85
- Missing-info accuracy: 85/85
- Full routing accuracy: 85/85

### Challenge eval set

- JSON valid: 8/8
- Schema valid: 8/8
- Intent accuracy: 8/8
- Agent-chain accuracy: 8/8
- Input-type accuracy: 8/8
- Missing-info accuracy: 8/8
- Full routing accuracy: 8/8

## Notes

These results show that the fine-tuned router can produce valid structured JSON and select the correct agent chain for the current synthetic and challenge evaluation sets.

Next step: integrate the trained router as an optional User Agent routing backend, while keeping the rule-based router as fallback.
