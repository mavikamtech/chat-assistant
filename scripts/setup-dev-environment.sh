#!/usr/bin/env bash
# setup-dev-environment.sh - Complete development environment setup

echo "🚀 Setting up Mavik AI Development Environment..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is required but not running"
    echo "Please start Docker Desktop"
    exit 1
fi

# Setup Python environments for each MCP server
echo "📦 Setting up MCP Server dependencies..."

# RAG Server
echo "Setting up RAG MCP Server..."
cd services/mcp_servers/rag
poetry install
cd ../../..

# Parser Server  
echo "Setting up Parser MCP Server..."
cd services/mcp_servers/parser
poetry install
cd ../../..

# FinDB Server
echo "Setting up FinDB MCP Server..."
cd services/mcp_servers/findb
poetry install
cd ../../..

# Web Server (if we complete it)
if [ -d "services/mcp_servers/web" ]; then
    echo "Setting up Web MCP Server..."
    cd services/mcp_servers/web
    poetry install
    cd ../../..
fi

# Install common packages
echo "Setting up shared packages..."
cd packages/common
poetry install
cd ../..

cd packages/aws_clients
poetry install
cd ../..

cd packages/config
poetry install
cd ../..

# Setup Lambda Authorizer
echo "Setting up Lambda Authorizer..."
cd services/authorizer
poetry install
cd ../..

# Setup Infrastructure
echo "Setting up CDK Infrastructure..."
cd infra/cdk
npm install
cd ../..

# Setup Web App
echo "Setting up Next.js Web App..."
cd apps/web
pnpm install
cd ../..

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Run 'docker-compose up -d' to start local services"
echo "3. Use the test scripts in ./scripts/ to verify components"