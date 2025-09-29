# setup-dev-environment.ps1 - PowerShell version for Windows

Write-Host "🚀 Setting up Mavik AI Development Environment..." -ForegroundColor Green

# Check if Poetry is installed
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Poetry..." -ForegroundColor Yellow
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
}

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js is required but not installed" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Check if pnpm is installed
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pnpm..." -ForegroundColor Yellow
    npm install -g pnpm
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is required but not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Red
    exit 1
}

# Setup Python environments for each MCP server
Write-Host "📦 Setting up MCP Server dependencies..." -ForegroundColor Blue

# RAG Server
Write-Host "Setting up RAG MCP Server..." -ForegroundColor Cyan
Set-Location services/mcp_servers/rag
poetry install
Set-Location ../../..

# Parser Server  
Write-Host "Setting up Parser MCP Server..." -ForegroundColor Cyan
Set-Location services/mcp_servers/parser
poetry install
Set-Location ../../..

# FinDB Server
Write-Host "Setting up FinDB MCP Server..." -ForegroundColor Cyan
Set-Location services/mcp_servers/findb
poetry install
Set-Location ../../..

# Web Server (if we complete it)
if (Test-Path "services/mcp_servers/web") {
    Write-Host "Setting up Web MCP Server..." -ForegroundColor Cyan
    Set-Location services/mcp_servers/web
    poetry install
    Set-Location ../../..
}

# Install common packages
Write-Host "Setting up shared packages..." -ForegroundColor Cyan
Set-Location packages/common
poetry install
Set-Location ../..

Set-Location packages/aws_clients
poetry install
Set-Location ../..

Set-Location packages/config
poetry install
Set-Location ../..

# Setup Lambda Authorizer
Write-Host "Setting up Lambda Authorizer..." -ForegroundColor Cyan
Set-Location services/authorizer
poetry install
Set-Location ../..

# Setup Infrastructure
Write-Host "Setting up CDK Infrastructure..." -ForegroundColor Cyan
Set-Location infra/cdk
npm install
Set-Location ../..

# Setup Web App
Write-Host "Setting up Next.js Web App..." -ForegroundColor Cyan
Set-Location apps/web
pnpm install
Set-Location ../..

Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Copy .env.example to .env and configure your settings" -ForegroundColor White
Write-Host "2. Run 'docker-compose up -d' to start local services" -ForegroundColor White
Write-Host "3. Use the test scripts in ./scripts/ to verify components" -ForegroundColor White