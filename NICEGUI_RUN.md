# NiceGUI Run Notes

From the project root:

```powershell
uv run python -m nice_gui_app.main
```

That starts the NiceGUI app on:

```text
http://127.0.0.1:8080
```

## Config Options

Real LLM conversation mode:

```powershell
$env:MANAGER_AI_CONFIG="C:\projects\en-red\manager-ai\config\dev-ui-llm.toml"
uv run python -m nice_gui_app.main
```

Local no-API mode:

```powershell
$env:MANAGER_AI_CONFIG="C:\projects\en-red\manager-ai\config\dev-no-api.toml"
uv run python -m nice_gui_app.main
```

If `MANAGER_AI_CONFIG` is not set, the app defaults to:

```text
config/dev-ui-llm.toml
```

## Stop

If the app is running in the current terminal, press `Ctrl+C`.

If you started it in another terminal/window:

```powershell
Get-CimInstance Win32_Process |
Where-Object { $_.CommandLine -like '*-m nice_gui_app.main*' } |
ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## Requirements

- Run from `C:\projects\en-red\manager-ai`
- `uv` must be available
- For real LLM mode, `ANTHROPIC_API_KEY` must be set in the environment
