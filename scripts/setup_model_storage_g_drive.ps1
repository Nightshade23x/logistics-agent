$ErrorActionPreference = "Stop"

$ModelRoot = "G:\ai-models"
$VenvRoot = "G:\venvs"
$TrainingVenv = "$VenvRoot\logistics-training"

if (-not (Test-Path "G:\")) {
    throw "G: drive was not found. Check that the drive exists before running this script."
}

$dirs = @(
    "$ModelRoot",
    "$ModelRoot\huggingface",
    "$ModelRoot\huggingface\hub",
    "$ModelRoot\huggingface\datasets",
    "$ModelRoot\huggingface\transformers",
    "$ModelRoot\torch",
    "$ModelRoot\pip-cache",
    "$ModelRoot\ollama",
    "$ModelRoot\wandb",
    "$ModelRoot\checkpoints",
    "$ModelRoot\training-outputs",
    "$VenvRoot"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$envVars = @{
    "HF_HOME" = "$ModelRoot\huggingface"
    "HF_HUB_CACHE" = "$ModelRoot\huggingface\hub"
    "TRANSFORMERS_CACHE" = "$ModelRoot\huggingface\transformers"
    "HF_DATASETS_CACHE" = "$ModelRoot\huggingface\datasets"
    "TORCH_HOME" = "$ModelRoot\torch"
    "XDG_CACHE_HOME" = "$ModelRoot\xdg-cache"
    "PIP_CACHE_DIR" = "$ModelRoot\pip-cache"
    "OLLAMA_MODELS" = "$ModelRoot\ollama"
    "WANDB_DIR" = "$ModelRoot\wandb"
}

foreach ($item in $envVars.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($item.Key, $item.Value, "User")
    Set-Item -Path "Env:\$($item.Key)" -Value $item.Value
}

try {
    python -m pip config set global.cache-dir "$ModelRoot\pip-cache" | Out-Null
} catch {
    Write-Host "Could not set pip cache globally, but environment variable PIP_CACHE_DIR was set."
}

if (-not (Test-Path "$TrainingVenv\Scripts\python.exe")) {
    Write-Host "Creating training venv on G: ..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.12 -m venv "$TrainingVenv"
    } else {
        python -m venv "$TrainingVenv"
    }
}

Write-Host ""
Write-Host "Model storage configured on G:."
Write-Host "Training venv created at: $TrainingVenv"
Write-Host ""
Write-Host "Next time you train, activate it with:"
Write-Host "& `"$TrainingVenv\Scripts\Activate.ps1`""
Write-Host ""
Write-Host "You should restart PowerShell after this so all apps see the new environment variables."
