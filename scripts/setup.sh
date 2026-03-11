#!/bin/bash
# AgenticP1 One-Command Setup Script
# ===================================
set -e

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   AgenticP1 — AI Calling Agent Platform   ║"
echo "║          One-Command Setup                ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Check dependencies
check_dep() {
    if ! command -v "$1" &>/dev/null; then
        echo "❌ $1 not found. Please install it first."
        exit 1
    fi
}

echo "Checking dependencies..."
check_dep docker
check_dep docker-compose || check_dep "docker compose"
echo "✅ Docker found"

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from .env.example..."
    cp .env.example .env

    # Generate a random JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/change-this-to-a-random-64-char-string-in-production!!/$JWT_SECRET/" .env
    else
        sed -i "s/change-this-to-a-random-64-char-string-in-production!!/$JWT_SECRET/" .env
    fi

    echo "✅ .env created with random JWT secret"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - GROQ_API_KEY (free at https://console.groq.com)"
    echo "   - TELNYX_API_KEY (for telephony, $0.005/min at telnyx.com)"
    echo ""
    read -p "Press ENTER to continue with default settings, or Ctrl+C to edit .env first..."
fi

# Create data directories
echo "Creating data directories..."
mkdir -p data/recordings data/chromadb data/models/piper data/models/vosk
echo "✅ Directories created"

# Build and start
echo ""
echo "Building and starting services..."
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend may still be starting. Check: docker-compose logs backend"
fi

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║             🚀 Setup Complete!            ║"
echo "╠═══════════════════════════════════════════╣"
echo "║                                           ║"
echo "║  Dashboard:  http://localhost:3000        ║"
echo "║  API Docs:   http://localhost:8000/docs   ║"
echo "║  API Base:   http://localhost:8000/api/v1 ║"
echo "║                                           ║"
echo "║  Commands:                                ║"
echo "║    make dev      - Start in dev mode      ║"
echo "║    make test     - Run tests              ║"
echo "║    make logs     - View logs              ║"
echo "║    make seed     - Add demo data          ║"
echo "║                                           ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
