#!/usr/bin/env powershell
# Start all Mavik AI services in local mock mode

Write-Host "🚀 Starting Mavik AI Services (Local Mock Mode)" -ForegroundColor Green
Write-Host "=" * 50

# Set environment variables
$env:PYTHONPATH = Get-Location
$env:APP_ENV = "local"
$env:MOCK_AWS = "true"
$env:LOG_LEVEL = "DEBUG"

# Start services in background
Write-Host "Starting Orchestrator..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8080'; poetry run python apps/orchestrator/main.py"

Write-Host "Starting MCP-RAG..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8081'; poetry run python services/mcp-rag/main.py"

Write-Host "Starting MCP-Parser..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8082'; poetry run python services/mcp-parser/main.py"

Write-Host "Starting MCP-FinDB..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8083'; poetry run python services/mcp-findb/main.py"

Write-Host "Starting MCP-Web..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8084'; poetry run python services/mcp-web/main.py"

Write-Host "Starting MCP-Calc..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD'; `$env:PYTHONPATH='$PWD'; `$env:APP_ENV='local'; `$env:MOCK_AWS='true'; `$env:PORT='8085'; poetry run python services/mcp-calc/main.py"

Write-Host "Starting Web App..." -ForegroundColor Yellow
Start-Process -NoNewWindow powershell -ArgumentList "-Command", "cd '$PWD/apps/web'; pnpm dev"

Write-Host ""
Write-Host "✅ All services starting..." -ForegroundColor Green
Write-Host "🌐 Web UI: http://localhost:3000" -ForegroundColor Cyan
Write-Host "🔧 Orchestrator API: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services"

# Keep script running
try {
    while ($true) {
        Start-Sleep 1
    }
} catch {
    Write-Host "Stopping all services..." -ForegroundColor Red
}
