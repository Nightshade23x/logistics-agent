# Local Setup

## Supported environment

The current handover workflow is primarily tested on Windows with PowerShell.

Required software:

- Git
- Python 3.11 or newer
- Node.js and npm
- A modern Chromium-based browser

## 1. Clone the repository

```powershell
git clone <repository-url>
cd logistics-agent
```

Use the repository URL shown on GitHub.

## 2. Create the Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the repository uses another requirements file in the future, install from the file documented in the current README.

## 3. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

Always run frontend npm commands from the `frontend` directory because that is where `package.json` is located.

## 4. Configure optional environment variables

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Typical optional variables:

```text
GEMINI_API_KEY=
TRADE_ORCHESTRATOR_BASE_URL=
OPENAI_API_KEY=
VITE_API_BASE_URL=
```

Leave optional values blank for deterministic standalone mode.

Never commit real credentials.

## 5. Start backend and frontend

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Logistics-App.ps1
```

The launcher is the authoritative source for:

- backend startup;
- frontend startup;
- current local ports;
- browser launch behaviour.

## 6. Refresh after frontend changes

After modifying frontend files:

1. stop the current launcher;
2. start it again;
3. press `Ctrl+F5` in the browser.

This prevents cached frontend assets from hiding recent changes.

## 7. Verify the frontend production build

```powershell
cd frontend
npm run build
cd ..
```

The build must pass before opening a Pull Request.

## 8. Run focused regression tests

From the repository root:

```powershell
$env:PYTHONPATH = (Get-Location).Path

python scripts/test_dynamic_process_flow_v62.py
python scripts/test_compact_flow_board_v62.py
python scripts/test_serpentine_flow_board_v62.py
python scripts/test_compact_synced_input_flow_v62.py
python scripts/test_blank_entry_fullwidth_flow_v62.py
python scripts/test_frontend_persistence_docs_cbm_v61.py
```

Run additional scripts under `scripts/` when changing related backend or agent logic.

## Standalone mode

Standalone mode does not require the external partner orchestrator.

The application should still provide:

- logistics calculations;
- container recommendations;
- route guidance;
- document advice;
- visualizer payloads;
- safe fallback status.

To remove a previously configured partner URL for the current PowerShell session:

```powershell
Remove-Item Env:\TRADE_ORCHESTRATOR_BASE_URL -ErrorAction SilentlyContinue
```

## Partner-integrated mode

To use compatible external partner services:

```powershell
$env:TRADE_ORCHESTRATOR_BASE_URL = "http://127.0.0.1:8010"
```

Start the required external services separately.

Do not describe partner results as live unless the services were checked immediately before the demonstration.

## Common problems

### PowerShell blocks the launcher

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Logistics-App.ps1
```

### npm cannot find package.json

You are probably running npm from the repository root.

Use:

```powershell
cd frontend
npm run build
```

### Python cannot import repository modules

Run commands from the repository root and set:

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

### The browser shows old frontend code

Restart the application and press `Ctrl+F5`.

### A previous request appears unexpectedly

Open a new tab for a clean session or use the application's clear controls.

### Optional partner services are unavailable

Continue in standalone mode and state clearly that partner integrations are not active.

## Stopping the application

Use `Ctrl+C` in the launcher terminals.

Before manually ending Python or Node processes, confirm that they belong to this repository.
