# Running the User Agent with the Trained Router

This script runs the User Agent using the fine-tuned LoRA router backend.

## Requirements

Use the training virtual environment:

G:\venvs\logistics-training

The trained adapter should exist locally at:

G:\ai-models\checkpoints\router-qwen-0.5b-lora-expanded-400\final_adapter

## Example

```powershell
& "G:\venvs\logistics-training\Scripts\Activate.ps1"
cd C:\Users\Samar\Desktop\logistics-agent

python scripts\run_user_agent_with_trained_router.py "I need 50 TVs from India and a shipping plan."
