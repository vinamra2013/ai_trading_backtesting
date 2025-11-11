#!/bin/bash
# QuantConnect Automation Setup Script
# Sets up LEAN CLI and configures environment for cloud backtesting

set -e

echo "============================================================"
echo "QuantConnect Cloud Automation Setup"
echo "============================================================"
echo ""

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: Not in virtual environment"
    echo "Activating venv..."
    source venv/bin/activate || {
        echo "Error: Could not activate venv"
        echo "Please run: source venv/bin/activate"
        exit 1
    }
fi

# Install LEAN CLI
echo "Installing LEAN CLI..."
pip install --upgrade lean
echo "✓ LEAN CLI installed"
echo ""

# Check LEAN version
LEAN_VERSION=$(lean --version 2>&1 || echo "unknown")
echo "LEAN CLI version: $LEAN_VERSION"
echo ""

# Setup .env file
echo "Configuring .env file..."
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Check if QC variables exist
if ! grep -q "QC_PROJECT_NAME" "$ENV_FILE"; then
    echo "" >> "$ENV_FILE"
    echo "# QuantConnect Cloud Configuration" >> "$ENV_FILE"
    echo 'QC_PROJECT_NAME="RSI Mean Reversion Basic"' >> "$ENV_FILE"
    echo "✓ Added QC_PROJECT_NAME to .env"
else
    echo "✓ QC_PROJECT_NAME already exists in .env"
fi

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x scripts/qc_cloud_backtest.py
chmod +x scripts/setup_qc_automation.sh
echo "✓ Scripts are now executable"

# Login to QuantConnect
echo ""
echo "============================================================"
echo "QuantConnect Login"
echo "============================================================"
echo ""
echo "You need to login to QuantConnect to use the cloud API."
echo "Get your credentials from: https://www.quantconnect.com/account"
echo ""
read -p "Do you want to login now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    lean login
    echo ""
    echo "✓ Logged in to QuantConnect"
else
    echo "Skipping login. You can login later with: lean login"
fi

# Test LEAN CLI
echo ""
echo "============================================================"
echo "Testing LEAN CLI"
echo "============================================================"
echo ""

# Create results directory
mkdir -p results/qc
echo "✓ Created results/qc directory"

# Check if project name is set
QC_PROJECT_NAME=$(grep QC_PROJECT_NAME .env | cut -d '=' -f 2 | tr -d '"')

if [ -z "$QC_PROJECT_NAME" ]; then
    echo "⚠ Warning: QC_PROJECT_NAME not set in .env"
    echo ""
    echo "Please edit .env and set:"
    echo 'QC_PROJECT_NAME="Your QuantConnect Project Name"'
    echo ""
else
    echo "✓ Project name configured: $QC_PROJECT_NAME"
fi

# Setup complete
echo ""
echo "============================================================"
echo "✓ SETUP COMPLETE"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify .env configuration:"
echo "   nano .env"
echo "   # Set QC_PROJECT_NAME to match your QuantConnect project"
echo ""
echo "2. Test the automation:"
echo "   python scripts/qc_cloud_backtest.py --help"
echo ""
echo "3. Run your first cloud backtest:"
echo "   python scripts/qc_cloud_backtest.py --open"
echo ""
echo "4. Full workflow with results:"
echo "   python scripts/qc_cloud_backtest.py --commit --wait --save"
echo ""
echo "============================================================"
echo ""
echo "GitHub Repo: git@github.com:vinamra2013/QuantConnectAlgoTradingStratigies.git"
echo "Claude Skill: .claude/skills/qc-backtest-runner.md"
echo ""
echo "For help:"
echo "  python scripts/qc_cloud_backtest.py --help"
echo "  lean --help"
echo ""
